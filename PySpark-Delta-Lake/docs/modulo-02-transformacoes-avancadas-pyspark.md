# Módulo 2 — Transformações avançadas em PySpark

> Agregações, joins, janelas, strings, datas, condições e valores nulos.

## Objetivos

- resumir dados com `groupBy` e agregações;
- escolher entre `agg()` e a sintaxe curta;
- aplicar joins `inner`, `left`, `right`, `full` e `left_anti`;
- construir joins com múltiplas chaves;
- usar `rank`, `dense_rank`, `row_number`, `lag` e `lead`;
- limpar strings, trabalhar com datas e tratar valores nulos.

## 1. Dados do laboratório

Todos os exemplos partem destes DataFrames:

```python
from pyspark.sql import SparkSession, Window
from pyspark.sql import functions as F
from pyspark.sql.types import *

spark = (SparkSession.builder.appName("Modulo02")
         .master("local[*]").config("spark.api.mode", "classic").getOrCreate())
spark.sparkContext.setLogLevel("ERROR")

orders = spark.createDataFrame([
    (1001, "PT", "C001", "P10", "2026-08-01", 2, 60.0, "entregue"),
    (1002, "PT", "C002", "P20", "2026-08-01", 1, 90.0, "entregue"),
    (1003, "PT", "C001", "P30", "2026-08-05", 3, 40.0, "entregue"),
    (1004, "ES", "C001", "P10", "2026-08-06", 1, 120.0, "pendente"),
    (1005, "PT", "C003", "P20", "2026-08-08", 2, 45.0, "cancelada"),
    (1006, "PT", "C004", "P10", "2026-08-10", 2, 60.0, "entregue"),
], "order_id int, country string, customer_id string, product_id string, "
   "order_date string, quantity int, unit_price double, status string")

customers = spark.createDataFrame([
    ("PT", "C001", "  ana silva ", "ana@email.pt", "Porto"),
    ("PT", "C002", "BRUNO COSTA", None, "Lisboa"),
    ("PT", "C003", "Carla Sousa", "carla@email.pt", None),
    ("PT", "C999", "Diogo Lima", "diogo@email.pt", "Coimbra"),
    ("ES", "C001", "Elena García", "elena@email.es", "Vigo"),
], "country string, customer_id string, name string, email string, city string")

orders = (orders.withColumn("order_date", F.to_date("order_date"))
          .withColumn("total_eur", F.round(F.col("quantity") * F.col("unit_price"), 2)))
```

## 2. `groupBy` e agregações

`groupBy` define a granularidade do resultado. Se agrupares por `country` e `status`, obterás uma linha por combinação distinta dessas duas colunas.

```python
summary = (orders.groupBy("country", "status")
    .agg(
        F.sum("total_eur").alias("revenue_eur"),
        F.avg("total_eur").alias("avg_order_eur"),
        F.count("order_id").alias("order_count"),
        F.max("total_eur").alias("max_order_eur"),
        F.min("total_eur").alias("min_order_eur"),
    )
    .orderBy("country", "status"))
summary.show()
# Output esperado:
# ES, pendente: 120.0 | 120.0 | 1 | 120.0 | 120.0
# PT, cancelada: 90.0 | 90.0 | 1 | 90.0 | 90.0
# PT, entregue: 450.0 | 112.5 | 4 | 120.0 | 90.0
```

### `agg()` vs. sintaxe curta

```python
# Sintaxe curta: clara quando existe apenas uma métrica.
orders.groupBy("country").sum("total_eur")

# agg(): preferível para várias métricas, aliases e expressões diferentes.
orders.groupBy("country").agg(
    F.sum("total_eur").alias("revenue_eur"),
    F.countDistinct("customer_id").alias("unique_customers"),
)
```

Usa `.sum()`, `.avg()`, `.count()` quando a operação é simples e isolada. Usa `.agg()` em pipelines de produção: permite combinar funções e atribuir nomes de negócio explícitos. `count("email")` ignora nulos; `count("*")` conta linhas.

### Antes/depois

| Antes: várias encomendas | Depois: uma linha por país |
|---|---|
| PT: 5 linhas | PT: receita 540,00 € |
| ES: 1 linha | ES: receita 120,00 € |

### Desafio 1

Calcula por cliente: receita, número de encomendas, ticket médio e última data. Exclui encomendas canceladas e ordena por receita descendente.

## 3. Joins

| Join | Mantém |
|---|---|
| `inner` | apenas correspondências dos dois lados |
| `left` | todas as linhas à esquerda |
| `right` | todas as linhas à direita |
| `full` | todas as linhas de ambos os lados |
| `left_anti` | linhas à esquerda sem correspondência à direita |

### 3.1 Join com múltiplas chaves

`customer_id = C001` existe em PT e ES. Juntar só por `customer_id` mistura duas pessoas. A chave correta é composta por `country` + `customer_id`.

```python
enriched = orders.join(customers, on=["country", "customer_id"], how="left")
enriched.select("order_id", "country", "customer_id", "name").orderBy("order_id").show()
# Output esperado:
# 1001 PT C001 "  ana silva "
# 1002 PT C002 "BRUNO COSTA"
# 1003 PT C001 "  ana silva "
# 1004 ES C001 "Elena García"  <- combinação correta
# 1005 PT C003 "Carla Sousa"
# 1006 PT C004 null             <- cliente não encontrado
```

Se as chaves tiverem nomes diferentes, usa aliases e uma condição explícita:

```python
o, c = orders.alias("o"), customers.alias("c")
condition = ((F.col("o.country") == F.col("c.country")) &
             (F.col("o.customer_id") == F.col("c.customer_id")))
joined = o.join(c, condition, "inner")
```

### 3.2 Comparação visual

Considera encomendas `C001, C002, C004` e clientes `C001, C002, C003`:

| Tipo | IDs resultantes |
|---|---|
| inner | C001, C002 |
| left | C001, C002, C004 |
| right | C001, C002, C003 |
| full | C001, C002, C003, C004 |
| left_anti | C004 |

```python
missing_customers = orders.join(
    customers, ["country", "customer_id"], "left_anti"
)
missing_customers.select("country", "customer_id").distinct().show()
# Output esperado: PT | C004
```

Evita selecionar `*` depois de uma condição explícita: podem ficar colunas duplicadas e ambíguas. Seleciona `o.*` e apenas os atributos necessários de `c`.

### Desafio 2

1. Produz encomendas enriquecidas com nome e cidade.
2. Deteta clientes sem encomendas com `left_anti`, invertendo os lados.
3. Repete o join apenas por `customer_id` e explica o erro de negócio criado em C001.

## 4. Window Functions

Uma janela calcula valores relacionados sem colapsar linhas, ao contrário de `groupBy`.

### 4.1 `rank()` vs. `dense_rank()` vs. `row_number()` com empates

```python
sales = spark.createDataFrame([
    ("Norte", "Ana", 120.0), ("Norte", "Bruno", 120.0),
    ("Norte", "Carla", 90.0), ("Norte", "Diogo", 70.0),
], "region string, seller string, revenue double")

w = Window.partitionBy("region").orderBy(F.col("revenue").desc())
ranking = (sales
    .withColumn("rank", F.rank().over(w))
    .withColumn("dense_rank", F.dense_rank().over(w))
    .withColumn("row_number", F.row_number().over(w)))
ranking.show()
# Output esperado (Ana/Bruno podem trocar no row_number):
# Ana   120 -> rank 1, dense_rank 1, row_number 1
# Bruno 120 -> rank 1, dense_rank 1, row_number 2
# Carla  90 -> rank 3, dense_rank 2, row_number 3
# Diogo  70 -> rank 4, dense_rank 3, row_number 4
```

- `rank`: empates recebem a mesma posição e deixam lacunas.
- `dense_rank`: empates recebem a mesma posição, sem lacunas.
- `row_number`: atribui sempre números únicos; num empate, o resultado não é determinístico sem um segundo critério.

Para tornar `row_number` determinístico: `orderBy(F.desc("revenue"), F.asc("seller"))`.

### 4.2 `lag` e `lead`

```python
w_customer = Window.partitionBy("country", "customer_id").orderBy("order_date")
timeline = (orders
    .withColumn("previous_total", F.lag("total_eur").over(w_customer))
    .withColumn("next_total", F.lead("total_eur").over(w_customer))
    .withColumn("change_eur", F.col("total_eur") - F.col("previous_total")))
# Para PT/C001: 2026-08-01 total 120 previous null next 120;
# 2026-08-05 total 120 previous 120 next null.
```

### Desafio 3

Encontra as duas encomendas de maior valor por país. Resolve uma vez com `dense_rank` e outra com `row_number`; explica por que o número de linhas pode diferir quando há empate.

## 5. Funções de string

```python
clean_customers = (customers
    .withColumn("name_clean", F.initcap(F.trim("name")))
    .withColumn("email_normalized", F.lower(F.trim("email")))
    .withColumn("email_domain", F.split("email_normalized", "@").getItem(1))
    .withColumn("city_code", F.upper(F.substring("city", 1, 3)))
    .withColumn("name_key", F.regexp_replace(F.lower(F.trim("name")), r"\s+", "_")))
```

| Antes | Depois |
|---|---|
| `"  ana silva "` | `"Ana Silva"` |
| `"BRUNO COSTA"` | `"Bruno Costa"` |
| `"ANA@EMAIL.PT"` | `"ana@email.pt"` |

Funções úteis: `trim`, `lower`, `upper`, `initcap`, `concat_ws`, `split`, `substring`, `regexp_replace`, `length`.

## 6. Funções de data

```python
dated = (orders
    .withColumn("year", F.year("order_date"))
    .withColumn("month", F.month("order_date"))
    .withColumn("month_start", F.trunc("order_date", "month"))
    .withColumn("payment_due", F.date_add("order_date", 30))
    .withColumn("days_until_today", F.datediff(F.current_date(), "order_date"))
    .withColumn("month_label", F.date_format("order_date", "yyyy-MM")))
# 2026-08-01 -> year 2026, month 8, month_start 2026-08-01,
# payment_due 2026-08-31, month_label 2026-08.
```

Converte texto com `to_date(coluna, formato)` e timestamps com `to_timestamp`. Mantém datas como `DateType`/`TimestampType`, não como strings: comparação e aritmética ficam corretas.

## 7. Condicionais e nulos

```python
classified = (enriched
    .withColumn("order_band",
        F.when(F.col("total_eur") >= 120, "alto")
         .when(F.col("total_eur") >= 75, "médio")
         .otherwise("baixo"))
    .withColumn("has_email", F.col("email").isNotNull())
    .fillna({"city": "Desconhecida", "email": "sem-email"}))
```

Antes/depois:

| customer_id | city antes | city depois |
|---|---|---|
| C003 | null | Desconhecida |
| C004 | null | Desconhecida |

Usa `isNull()`/`isNotNull()`; `col == None` não é a forma idiomática. `fillna` substitui; `dropna` remove; `coalesce(col1, col2, lit(...))` escolhe o primeiro valor não nulo.

### Desafio 4

Normaliza nomes/emails, preenche cidades, cria faixas de valor e calcula o prazo de pagamento. Mostra apenas linhas com email ausente antes de preencher.

## 8. Desafio final

Constrói uma tabela analítica com uma linha por encomenda entregue:

1. limpa os clientes;
2. junta encomendas e clientes por `country` + `customer_id`;
3. preenche dados ausentes;
4. calcula receita total e ticket médio por cliente com `agg()`;
5. acrescenta a encomenda anterior com `lag`;
6. classifica clientes por receita dentro de cada país com `dense_rank`;
7. conserva os três primeiros por país;
8. valida clientes desconhecidos através de `left_anti`.

## Resumo e checklist

- [ ] Sei quando usar `agg()` em vez da sintaxe curta.
- [ ] Sei que `count(coluna)` ignora nulos.
- [ ] Sei escolher entre inner, left, right, full e anti join.
- [ ] Sei fazer um join com múltiplas chaves.
- [ ] Explico `rank` vs. `dense_rank` vs. `row_number` com empates.
- [ ] Sei usar `lag` e `lead`.
- [ ] Sei limpar strings e converter datas.
- [ ] Sei usar `when`/`otherwise`, `isNull` e `fillna`.
- [ ] Completei o desafio final.

Referência: [Window Functions — Apache Spark](https://spark.apache.org/docs/latest/sql-ref-syntax-qry-select-window.html).
