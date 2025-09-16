# 🕒 Dashboard de Apontamentos

Um dashboard interativo desenvolvido em **Python + Streamlit** para monitoramento, análise e validação de apontamentos de horas da equipe.\
O sistema aplica regras de consistência diária e gera **insights visuais** para apoiar a gestão.

***

## 🚀 Funcionalidades

* 📂 Upload de planilha `.xlsx` com logs de apontamentos
* 📊 Dashboard visual com indicadores de:
  * Dias válidos ✅ e inválidos ❌
  * Horas totais registradas por colaborador
  * Dias sem apontamentos
  * Conflitos de sobreposição de horários
* 🗓️ Integração com **feriados nacionais, estaduais e municipais (Araçatuba - SP)**
* 🔍 Filtros por **colaborador** e **data**
* 📈 Visualização em **Timeline** e **tabelas detalhadas**

***

## 🛠️ Tecnologias

* [Python 3.11+](https://www.python.org/)
* [Streamlit](https://streamlit.io/)
* [Pandas](https://pandas.pydata.org/)
* [Altair](https://altair-viz.github.io/)
* [Requests](https://pypi.org/project/requests/)

***

## 📦 Instalação

Clone o repositório e instale as dependências:

```Shell
git clone https://github.com/denis-bonafe-solinftec/gestao-apontamentos.git
cd gestao-apontamentos
pip install -r requirements.txt
```

***

## ▶️ Execução Local

```Shell
streamlit run app.py
```

## Execução no macOS
É necessário instalar o podman para rodar via container.
```Shell
https://podman.io/docs/installation
```

É possível instalar via homebrew rodando:
```Shell
brew install podman
brew install podman-compose
```
Após instalar:
```Shell
podman machine init
```

Para executar a aplicação, acessar a pasta da mesma, e executar:
```Shell
podman machine start
```
E após a máquina executar:
```Shell
podman compose up -d
```

Após:

O app será iniciado em `http://localhost:8501`.
