# Price Monitor — Pipeline de ETL com Python e Airflow

[![CI](https://github.com/verissimo-felipe/price-monitor/actions/workflows/ci.yml/badge.svg)](https://github.com/verissimo-felipe/price-monitor/actions/workflows/ci.yml)

Pipeline de **ETL orquestrado por Apache Airflow** que coleta cotações e
notícias de três tipos de fonte, transforma e valida os dados com **Pandas**
e carrega em **PostgreSQL**. Todo o desenvolvimento segue **Git Flow**.

---

## 🎯 O que este projeto faz

1. **Extrai** dados de três fontes diferentes:
   - **API REST** (cotações USD-BRL / EUR-BRL via AwesomeAPI) — `requests`
   - **Scraping estático** (títulos de notícias) — `BeautifulSoup`
   - **Scraping dinâmico** (páginas com JavaScript) — `Selenium`
2. **Transforma** e **valida a qualidade** dos dados com `pandas`
   (tipos, valores nulos, cotações inválidas).
3. **Carrega** o resultado consolidado em uma tabela **PostgreSQL**.
4. **Orquestra** todo o fluxo com uma **DAG do Airflow** agendada de hora em
   hora, com *retries* automáticos e monitoramento pela UI.

---
## 🏭 Arquitetura


![Arquitetura](./img/arquitetura-price-monitor.drawio.png)

Cada extrator implementa o mesmo contrato (`etl/base.py → Extractor`), então a
DAG é agnóstica à fonte: trocar/adicionar uma fonte não mexe no restante do
pipeline.

---

## 📁 Estrutura de pastas

```
price-monitor/
├── etl/
│   ├── base.py              # contrato comum (classe Extractor)
│   ├── api_extractor.py     # cotações via API REST (requests)
│   ├── scraper.py           # scraping estático (BeautifulSoup)
│   ├── selenium_scraper.py  # scraping dinâmico (Selenium)
│   ├── transform.py         # transformação + validações (pandas)
│   └── load.py              # carga no PostgreSQL (sqlalchemy)
├── dags/
│   └── pipeline_cotacoes.py # DAG do Airflow (extrair → transformar → carregar)
├── tests/
│   └── test_transform.py    # testes das regras de transformação
├── requirements.txt
├── .gitignore
└── README.md
```

---

## 🛠️ Tecnologias

| Categoria | Ferramenta |
|-----------|------------|
| Linguagem | Python 3.11+ |
| Extração | requests, BeautifulSoup4, Selenium |
| Transformação | pandas |
| Carga / SQL | SQLAlchemy + psycopg2 |
| Banco | PostgreSQL |
| Orquestração | Apache Airflow |
| Testes | pytest |
| Versionamento | Git Flow |

---

## ▶️ Como rodar

### 1. Pré-requisitos
- Python 3.11+
- PostgreSQL em execução
- Chrome/Chromium + chromedriver (para o extrator Selenium)

### 2. Setup

```bash
git clone <url-do-repo> && cd price-monitor
python -m venv .venv && . .venv/Scripts/activate   # Windows
# source .venv/bin/activate                        # Linux/Mac
pip install -r requirements.txt
```

### 3. Banco de dados

Ajuste a string de conexão em `etl/load.py` (ou via variável de ambiente) e
crie o banco `monitor`:

```sql
CREATE DATABASE monitor;
```

### 4. Rodar o pipeline manualmente (sem Airflow)

```python
from etl.api_extractor import CotacaoAPIExtractor
from etl.transform import transformar_cotacoes
from etl.load import carregar

df = CotacaoAPIExtractor().extract()
df = transformar_cotacoes(df)
carregar(df, "cotacoes")
```

### 5. Rodar com Airflow

```bash
# suba o Airflow (via Docker) e aponte a pasta dags/
# depois acesse a UI:
#   http://localhost:8080
# ative a DAG "pipeline_cotacoes" e dispare uma execução
```

---

## 🧪 Testes

```bash
pytest
```

---

## 🌱 Fluxo de trabalho (Git Flow)

- `main` — versões estáveis (tags de release)
- `develop` — integração contínua do desenvolvimento
- `feature/*` — cada funcionalidade (ex.: `feature/extractors-base`)
- `release/*` — preparação de versão

Exemplo de fechamento de release:

```bash
git checkout -b release/1.0.0 develop
git checkout main && git merge --no-ff release/1.0.0 && git tag v1.0.0
```

---

## 🚀 Próximos passos

- Alertas de falha (Slack/e-mail) na DAG
- Deploy do Airflow com `docker-compose` completo
- Extrator SOAP (via `zeep`) como fonte adicional
- Destino alternativo em NoSQL/Firebase
