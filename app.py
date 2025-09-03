from pandas.tseries.offsets import BDay
from datetime import datetime
import streamlit as st
import pandas as pd
import altair as alt
import requests

def obter_feriados_manuais(ano: int = datetime.now().year):
    """
    Define feriados manuais customizados por categoria.
    Adicione ou remova datas conforme necessário.
    """
    feriados_manuais = {
        # Feriados municipais (São Paulo)
        "municipais": [
            f"{ano}-01-25",  # Aniversário de São Paulo
            f"{ano}-04-23",  # São Jorge
        ],
        
        # Feriados da empresa/opcionais
        "empresa": [
            f"{ano}-06-12",  # Dia dos Namorados (se for feriado na empresa)
            f"{ano}-12-24",  # Véspera de Natal
            f"{ano}-12-31",  # Véspera de Ano Novo
        ],
        
        # Feriados estaduais ou regionais
        "regionais": [
            f"{ano}-11-20",  # Consciência Negra (alguns estados)
            f"{ano}-07-09", # Revolução constitucionalíssima (MMDC)
        ],
        
        # Pontos facultativos ou datas específicas
        "pontos_facultativos": [
            # Adicione datas específicas aqui
            # f"{ano}-02-12",  # Carnaval (exemplo)
            # f"{ano}-02-13",  # Carnaval (exemplo)
        ]
    }
    
    # Combina todas as categorias
    todas_datas = []
    for categoria, datas in feriados_manuais.items():
        todas_datas.extend(datas)
    
    return todas_datas

def buscar_feriados_brasil(ano: int = datetime.now().year):
    # Obtém feriados manuais customizados
    feriados_manuais = obter_feriados_manuais(ano)
    
    # Converte feriados manuais para objetos date
    datas_feriados_manuais = [datetime.fromisoformat(data).date() for data in feriados_manuais]
    
    try:
        # Busca feriados da API
        url = "https://openholidaysapi.org/PublicHolidays"
        params = {
            "countryIsoCode": "BR",
            "languageIsoCode": "PT",
            "validFrom": f"{ano}-01-01",
            "validTo": f"{ano}-12-31"
        }
        headers = {
            "accept": "text/json"
        }

        response = requests.get(url, headers=headers, params=params)
        feriados_api = response.json()

        # Converte feriados da API para objetos date
        datas_feriados_api = [datetime.fromisoformat(f["startDate"]).date() for f in feriados_api]
        
    except Exception as e:
        print(f"Erro ao buscar feriados da API: {e}")
        datas_feriados_api = []
    
    # Combina feriados da API com feriados manuais (remove duplicatas)
    todas_datas_feriado = list(set(datas_feriados_api + datas_feriados_manuais))
    
    # print(f"Feriados encontrados: {len(todas_datas_feriado)}")
    # print(f"- Da API: {len(datas_feriados_api)}")
    # print(f"- Manuais: {len(datas_feriados_manuais)}")
    # print(f"Datas: {sorted(todas_datas_feriado)}")

    return sorted(todas_datas_feriado)


def detectar_sobreposicoes(df):
    df = df.copy()
    df["Sobreposição"] = False
    df["Start Rounded"] = df["Start Datetime"].dt.floor("min")
    df["End Rounded"] = df["End Datetime"].dt.floor("min")

    for (owner, data), grupo in df.groupby(["Owner", "Data"]):
        grupo_ordenado = grupo.sort_values("Start Rounded").reset_index()
        for i in range(1, len(grupo_ordenado)):
            atual = grupo_ordenado.loc[i]
            anterior = grupo_ordenado.loc[i - 1]
            if atual["Start Rounded"] < anterior["End Rounded"]:
                df.loc[grupo_ordenado.loc[i, "index"], "Sobreposição"] = True
    return df

def carregar_apontamentos(excel_path):
    df_raw = pd.read_excel(excel_path, sheet_name="log", header=None, engine="openpyxl")
    registros = []
    current_description = None
    processing_block = False

    for i, row in df_raw.iterrows():
        first_col = str(row[0]).strip()
        if first_col == "Started By":
            prev_row = df_raw.iloc[i - 1]
            next_row = df_raw.iloc[i + 1]
            current_description = str(prev_row[0]).strip()
            # current_owner = str(next_row[0]).strip()
            processing_block = True
            continue
        elif first_col == "Total":
            processing_block = False
            continue
        if processing_block:
            if pd.notna(row[2]) and pd.notna(row[3]) and pd.notna(row[4]) and pd.notna(row[5]):
                registros.append({
                    "Owner": str(row[0]).strip(),
                    "Descrição": current_description,
                    "Start Date": row[2],
                    "End Date": row[3],
                    "Start Time": row[4],
                    "End Time": row[5],
                    "Duration": row[6]
                })

    df = pd.DataFrame(registros)
    df["Start Datetime"] = pd.to_datetime(df["Start Date"].astype(str) + " " + df["Start Time"].astype(str), format='%Y-%m-%d %I:%M:%S %p')
    df["End Datetime"] = pd.to_datetime(df["End Date"].astype(str) + " " + df["End Time"].astype(str), format='%Y-%m-%d %I:%M:%S %p')
    df["Tempo Percorrido"] = df["End Datetime"] - df["Start Datetime"]
    df["Horas Decimais"] = round(df["Tempo Percorrido"].dt.total_seconds() / 3600, 2)
    df["Tempo Percorrido Formatado"] = df["Tempo Percorrido"].apply(lambda td: str(td).split(".")[0])
    df["Data"] = df["Start Datetime"].dt.date
    df["Início Formatado"] = df["Start Datetime"].dt.strftime("%d/%m/%Y %H:%M")
    df["Fim Formatado"] = df["End Datetime"].dt.strftime("%d/%m/%Y %H:%M")
    return df

def motivo_validacao(row):
    if pd.isna(row["Horas Decimais"]) or row["Horas Decimais"] == 0:
        return "Sem apontamento"
    motivos = []
    if row["Data"] in dias_com_sobreposicao:
        motivos.append("Conflito de horários")
    if row["Horas Decimais"] < 7:
        motivos.append("Tempo insuficiente")
    elif row["Horas Decimais"] > 9.5:
        motivos.append("Tempo excedente")
    return ", ".join(motivos) if motivos else "OK"

def validar_dia(row):
    if row["Horas Decimais"] == 0:
        return "❌ Inválido"
    if row["Data"] in dias_com_sobreposicao:
        return "❌ Inválido"
    elif 7 <= row["Horas Decimais"] <= 9.5:
        return "✅ Válido"
    else:
        return "❌ Inválido"

st.set_page_config(page_title="Timeline de Apontamentos", layout="wide")
st.title("🕒 Timeline Diária de Apontamentos")

uploaded_file = st.file_uploader("", type=["xlsx"])

if uploaded_file:

    feriados = buscar_feriados_brasil(2025)
    df = carregar_apontamentos(uploaded_file)
    df = detectar_sobreposicoes(df)

    # Filtros
    with st.sidebar:
        st.header("🔍 Filtros")
        
        owners = ["Todos Colaboradores"] + sorted(df["Owner"].unique())
        selected_owner = st.selectbox("👤 Colaborador", owners)

        # só filtra se não for visão geral
        if selected_owner != "Todos Colaboradores":
            df = df[df["Owner"] == selected_owner]

        # Datas disponíveis após filtro de owner
        datas_disponiveis = sorted(df["Data"].unique())
        data_selecionada = st.date_input(
            "📆 Data",
            value=datas_disponiveis[-1],
            min_value=datas_disponiveis[0],
            max_value=datas_disponiveis[-1]
        )

    # Gera todos os dias úteis entre o primeiro e o último dia
    datas_uteis = pd.date_range(start=df["Data"].min(), end=df["Data"].max(), freq=BDay()).date

    # Remove feriados
    dias_uteis_validos = [d for d in datas_uteis if d not in feriados]

    # Converte para dataframe
    df_datas_uteis = pd.DataFrame({"Data": dias_uteis_validos})

    # Mescla os dias úteis com os que possuem horas
    horas_por_dia = df.groupby("Data")["Horas Decimais"].sum().reset_index()
    horas_por_dia = pd.merge(df_datas_uteis, horas_por_dia, on="Data", how="left")
    horas_por_dia["Horas Decimais"] = horas_por_dia["Horas Decimais"].fillna(0)

    dias_com_sobreposicao = df[df["Sobreposição"]]["Data"].unique()

    horas_por_dia["Motivo"] = horas_por_dia.apply(motivo_validacao, axis=1)
    horas_por_dia["Status"] = horas_por_dia["Motivo"].apply(lambda m: "✅ Válido" if m == "OK" else "❌ Inválido")

    dias_invalidos = horas_por_dia[horas_por_dia["Status"] == "❌ Inválido"]

    # Métricas gerais
    st.markdown("---")
    col1, col2 = st.columns([1, 4])
    col1.subheader(f"📊 Métricas")
    col1.metric("📅 Dias registrados", len(horas_por_dia), border=True)
    col1.metric("⚠️ Dias com erro", len(dias_invalidos), border=True)

    # Validação em aba separada
    col2.subheader(f"📊 Apontamentos inválidos")
    if dias_invalidos.empty:
        col2.success("🎉 Todos os dias estão válidos!")
    else:
        col2.dataframe(dias_invalidos[["Data", "Horas Decimais", "Motivo"]], use_container_width=True)

    # Filtro por dia
    datas_disponiveis = sorted(df["Data"].unique())
    df_dia = df[df["Data"] == data_selecionada].sort_values("Start Datetime")

    st.markdown("---")    
    col1, col2 = st.columns([1, 4])
    col1.subheader(f"📊 Resumo de horas")

    if selected_owner == "Todos Colaboradores":
        # visão geral
        total_por_owner = df_dia.groupby("Owner")["Horas Decimais"].sum().reset_index()
        total_geral = total_por_owner["Horas Decimais"].sum().round(2)

        col1.metric(
            "⏱️ Total geral de horas",
            f"{total_geral}h",
            border=True
        )
        col2.subheader(f"📊 Apontamentos de todos em {data_selecionada.strftime('%d/%m/%Y')}")

        if df_dia.empty:
            st.warning("⚠️ Nenhum apontamento encontrado para essa data.")
        else:
            tab1, tab2 = col2.tabs(["📈 Timeline", "📄 Detalhes"])

            with tab1:
                chart = alt.Chart(df_dia).mark_bar(size=30).encode(
                    x=alt.X('Start Datetime:T', axis=alt.Axis(grid=True, title="Início")),
                    x2='End Datetime:T',
                    y=alt.Y('Descrição:N', sort=alt.EncodingSortField(field="Start Datetime")),
                    color=alt.Color("Owner:N", legend=alt.Legend(title="Colaborador")),
                    tooltip=[
                        alt.Tooltip("Owner:N", title="Colaborador"),
                        alt.Tooltip("Descrição:N", title="Tarefa"),
                        alt.Tooltip("Início Formatado:N", title="Início"),
                        alt.Tooltip("Fim Formatado:N", title="Fim"),
                        alt.Tooltip("Horas Decimais:Q", title="Horas")
                    ]
                ).properties(height=500)
                st.altair_chart(chart, use_container_width=True)

            with tab2:
                st.dataframe(df_dia[[
                    "Owner", "Descrição", "Início Formatado", "Fim Formatado",
                    "Tempo Percorrido Formatado", "Horas Decimais", "Sobreposição"
                ]], use_container_width=True)

            # Tabela resumo por colaborador
            st.markdown("### 📌 Total de horas por colaborador")
            st.dataframe(total_por_owner.rename(columns={"Owner": "Colaborador", "Horas Decimais": "Total de Horas"}), use_container_width=True)

    else:
        # visão individual (como já era antes)
        total_dia = round(df_dia["Horas Decimais"].sum(), 2)
        status_dia = "✅ Válido" if 7 <= total_dia <= 9.5 else "❌ Inválido"

        col1.metric("⏱️ Total de horas", f"{total_dia}h", status_dia, border=True)
        col2.subheader(f"📊 Apontamentos de {data_selecionada.strftime('%d/%m/%Y')}")

        if df_dia.empty:
            st.warning("⚠️ Nenhum apontamento encontrado para essa data.")
        else:
            tab1, tab2 = col2.tabs(["📈 Timeline", "📄 Detalhes"])

            with tab1:
                chart = alt.Chart(df_dia).mark_bar(size=30).encode(
                    x=alt.X('Start Datetime:T', axis=alt.Axis(grid=True, title="Início")),
                    x2='End Datetime:T',
                    y=alt.Y('Descrição:N', sort=alt.EncodingSortField(field="Start Datetime")),
                    color=alt.condition(alt.datum.Sobreposição, alt.value("crimson"), alt.value("#4B8BBE")),
                    tooltip=[
                        alt.Tooltip("Descrição:N", title="Tarefa"),
                        alt.Tooltip("Início Formatado:N", title="Início"),
                        alt.Tooltip("Fim Formatado:N", title="Fim"),
                        alt.Tooltip("Horas Decimais:Q", title="Horas")
                    ]
                ).properties(height=400)
                st.altair_chart(chart, use_container_width=True)

            with tab2:
                st.dataframe(df_dia[[
                    "Descrição", "Início Formatado", "Fim Formatado",
                    "Tempo Percorrido Formatado", "Horas Decimais", "Sobreposição"
                ]], use_container_width=True)

else:
    st.info("Por favor, carregue um arquivo `.xlsx` com os apontamentos para iniciar.")
