# Databricks e PySpark para Data Engineering

Este workspace e um mini-lab pratico para aprender PySpark com mentalidade de Data Engineer. A ordem sugerida e:

## Documentação de estudo

| Percurso | Conteúdo | Estado |
|---|---|---|
| PySpark — Módulo 1 | [Fundamentos de PySpark](docs/modulo-01-fundamentos-pyspark.md) | Disponível |
| PySpark — Módulo 2 | [Transformações avançadas](docs/modulo-02-transformacoes-avancadas-pyspark.md) | Disponível |
| PySpark — Módulo 3 | [Otimização, particionamento, cache e UDFs](docs/modulo-03-otimizacao-pyspark.md) | Disponível |
| Delta Lake — Módulo 1 | [Do zero ao Lakehouse](docs/modulo-01-delta-lake.md) | Disponível |

Cada módulo inclui explicações, exemplos visuais, código Python, outputs esperados, exercícios e um checklist final.

## Laboratórios existentes

1. `notebooks/01_dataframe_basics.ipynb` - criar uma SparkSession, ler CSV, selecionar, filtrar e criar colunas.
2. `notebooks/02_joins_and_aggregations.ipynb` - joins, agregacoes e metricas de negocio.
3. `notebooks/03_bronze_silver_gold.ipynb` - pipeline estilo lakehouse com camadas Bronze, Silver e Gold.
4. `notebooks/04_orders_challenge.ipynb` - desafio para consolidares o essencial.

## Como correr localmente

Ativa o ambiente virtual:

```bash
source .venv/bin/activate
```

Verifica se Java e PySpark estao prontos:

```bash
python setup/check_environment.py
```

Corre uma aula:

```bash
scripts/run_spark.sh lessons/01_dataframe_basics.py
```

Se o Java/Spark estiver configurado, vais ver tabelas impressas no terminal.

Se aparecer `Unable to locate a Java Runtime`, segue [setup/macos.md](/Users/franciscosamagaio/Documents/Pyspark/setup/macos.md).

Nota: corre um script Spark de cada vez. Localmente, cada SparkSession abre portas internas para comunicar entre Python e JVM.

## Como usar Jupyter notebooks

Instala as dependencias de notebook:

```bash
.venv/bin/pip install -r requirements.txt
```

Abre o Jupyter Notebook:

```bash
scripts/run_spark.sh -m notebook
```

Depois abre `notebooks/01_dataframe_basics.ipynb` e corre as celulas uma a uma.

## Como pensar em Databricks

No Databricks, estes scripts normalmente viram notebooks. Os conceitos sao os mesmos:

- `SparkSession`: no Databricks ja existe como `spark`.
- `data/raw`: seria uma pasta num volume, DBFS, cloud storage ou Unity Catalog.
- Bronze: dados ingeridos quase crus.
- Silver: dados limpos, tipados e validados.
- Gold: tabelas prontas para analytics, reporting ou ML.

## Objetivo do primeiro ciclo

No fim destes ficheiros deves conseguir:

- Ler dados com PySpark.
- Aplicar transformacoes comuns em DataFrames.
- Fazer joins entre tabelas.
- Agregar dados por cliente, produto e data.
- Explicar a arquitetura Bronze/Silver/Gold.
- Adaptar o pipeline para um notebook Databricks.
