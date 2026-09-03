# Módulo 1 — Fundamentos de PySpark

> Do zero a um primeiro pipeline: `SparkSession`, RDD vs. DataFrame, leitura de CSV/Parquet/JSON, transformações básicas e execução lazy.

## Objetivos

No final deste módulo conseguirás:

- criar e terminar uma `SparkSession`;
- explicar quando usar DataFrames e quando um RDD pode ser necessário;
- ler CSV, JSON e Parquet com schema explícito;
- usar `select`, `filter`, `withColumn`, `distinct` e `orderBy`;
- distinguir `col()` de `lit()`;
- distinguir Transformations (lazy) de Actions;
- construir e executar um pequeno pipeline completo.

## 1. O que são Spark e PySpark?

Apache Spark é um motor distribuído de processamento de dados. Divide o trabalho em partições, que podem ser processadas em paralelo por vários executores. PySpark é a API Python do Spark.

```text
Programa Python (Driver)
        |
        | cria um plano de execução
        v
SparkSession → Spark → partição 1 | partição 2 | partição 3
                         executor(es)
```

Mesmo em modo local, os conceitos são os mesmos de um cluster. `local[*]` significa usar todos os cores disponíveis na máquina.

### 1.1 Criar a SparkSession

`SparkSession` é o ponto de entrada para trabalhar com DataFrames e SQL.

```python
from pyspark.sql import SparkSession

spark = (
    SparkSession.builder
    .appName("Modulo01Fundamentos")
    .master("local[*]")  # Remove esta linha num cluster gerido, se necessário
    .config("spark.api.mode", "classic")  # Garante Spark clássico no laboratório local
    .getOrCreate()
)

spark.sparkContext.setLogLevel("WARN")

print(spark.version)
# Output esperado: a versão instalada, por exemplo: 4.2.0

# No final da aplicação, liberta os recursos.
spark.stop()
```

Em Databricks, a sessão `spark` já costuma existir. Num script local, deves criá-la e chamar `spark.stop()` no final.

### Desafio 1

1. Cria uma sessão chamada `EstudoVendas`.
2. Mostra a versão do Spark e o número de cores disponíveis com `spark.sparkContext.defaultParallelism`.
3. Termina a sessão corretamente.

## 2. RDD vs. DataFrame

Um RDD (*Resilient Distributed Dataset*) é uma coleção distribuída de objetos sem um schema tabular obrigatório. Um DataFrame é uma tabela distribuída, com colunas e tipos conhecidos.

| Aspeto | RDD | DataFrame |
|---|---|---|
| Estrutura | Objetos Python/Java | Linhas e colunas com schema |
| Otimização automática | Limitada | Catalyst + Tungsten |
| API | `map`, `flatMap`, `reduceByKey` | `select`, `filter`, `groupBy`, SQL |
| Validação de tipos | Menor | Schema explícito |
| Uso habitual | Lógica de baixo nível/não tabular | ETL, analytics e engenharia de dados |

**Regra prática:** começa com DataFrames. Usa RDDs apenas quando precisas de controlo de baixo nível ou tens dados genuinamente não tabulares que a API de DataFrames não expressa bem.

### 2.1 A mesma regra nas duas APIs

Dados iniciais:

| order_id | customer_id | total_eur | status |
|---:|---|---:|---|
| 1001 | C001 | 129.90 | entregue |
| 1002 | C002 | 49.50 | cancelada |
| 1003 | C001 | 215.00 | entregue |

```python
from pyspark.sql import SparkSession

spark = (
    SparkSession.builder
    .appName("RDDvsDataFrame")
    .master("local[*]")
    .config("spark.api.mode", "classic")
    .getOrCreate()
)

orders = [
    (1001, "C001", 129.90, "entregue"),
    (1002, "C002", 49.50, "cancelada"),
    (1003, "C001", 215.00, "entregue"),
]

# RDD: a posição [2] representa o valor, mas o Spark não conhece o seu significado.
rdd = spark.sparkContext.parallelize(orders)
rdd_resultado = rdd.filter(lambda linha: linha[2] >= 100).collect()
print(rdd_resultado)
# Output esperado:
# [(1001, 'C001', 129.9, 'entregue'), (1003, 'C001', 215.0, 'entregue')]

# DataFrame: as colunas e respetivos tipos fazem parte do plano.
df = spark.createDataFrame(
    orders,
    ["order_id", "customer_id", "total_eur", "status"],
)
df.filter(df.total_eur >= 100).show()
# Output esperado:
# +--------+-----------+---------+--------+
# |order_id|customer_id|total_eur|  status|
# +--------+-----------+---------+--------+
# |    1001|       C001|    129.9|entregue|
# |    1003|       C001|    215.0|entregue|
# +--------+-----------+---------+--------+

spark.stop()
```

### Desafio 2

Com os mesmos dados, devolve apenas encomendas entregues:

1. com `RDD.filter()`;
2. com `DataFrame.filter()`;
3. explica qual versão comunica melhor a intenção e porquê.

## 3. Leitura de CSV, JSON e Parquet

Em produção, evita depender de `inferSchema`: lê amostras adicionais, custa tempo e pode inferir tipos errados. Um schema explícito torna o contrato de dados previsível.

### 3.1 CSV

Ficheiro `orders.csv`:

```csv
order_id,customer_id,order_date,total_eur,status
1001,C001,2026-08-01,129.90,entregue
1002,C002,2026-08-01,49.50,cancelada
1003,C001,2026-08-03,215.00,entregue
```

```python
from pyspark.sql.types import (
    DateType, DoubleType, IntegerType, StringType, StructField, StructType
)

schema_orders = StructType([
    StructField("order_id", IntegerType(), False),
    StructField("customer_id", StringType(), False),
    StructField("order_date", DateType(), False),
    StructField("total_eur", DoubleType(), True),
    StructField("status", StringType(), True),
])

df_csv = (
    spark.read
    .option("header", True)
    .option("dateFormat", "yyyy-MM-dd")
    .schema(schema_orders)
    .csv("data/raw/orders.csv")
)

df_csv.printSchema()
# Output esperado:
# root
#  |-- order_id: integer (nullable = true)
#  |-- customer_id: string (nullable = true)
#  |-- order_date: date (nullable = true)
#  |-- total_eur: double (nullable = true)
#  |-- status: string (nullable = true)
```

Nota: fontes de ficheiros como CSV podem tornar os campos nullable no DataFrame lido, mesmo que o `StructField` indique `False`, porque dados externos podem estar incompletos ou malformados.

### 3.2 JSON

Por omissão, o Spark espera JSON delimitado por linha (*JSON Lines*): um objeto por linha.

```python
df_json = spark.read.schema(schema_orders).json("data/raw/orders.json")
df_json.show(truncate=False)
# Output esperado: as mesmas cinco colunas, com uma encomenda por linha.
```

Para um único array JSON formatado em várias linhas, acrescenta `.option("multiLine", True)`.

### 3.3 Parquet

Parquet é colunar, comprimido e preserva o schema. É normalmente preferível a CSV/JSON para armazenamento analítico intermédio.

```python
# Escrever em Parquet (Action: executa um job de escrita).
df_csv.write.mode("overwrite").parquet("data/processed/orders_parquet")

# O schema está guardado nos próprios ficheiros Parquet.
df_parquet = spark.read.parquet("data/processed/orders_parquet")
df_parquet.printSchema()
# Output esperado: order_id integer, customer_id string, order_date date,
# total_eur double e status string.
```

| Formato | Melhor para | Limitação principal |
|---|---|---|
| CSV | Troca simples com pessoas/sistemas legados | Sem tipos nativos; leitura menos eficiente |
| JSON | Dados semiestruturados e APIs | Verboso e mais caro de processar |
| Parquet | Data lakes e analytics | Não é legível diretamente por humanos |

### Desafio 3

1. Lê `data/raw/customers.csv` com um schema explícito.
2. Guarda-o em Parquet.
3. Lê o Parquet novamente e confirma os tipos com `printSchema()`.
4. Responde: por que não é necessário passar o schema ao ler Parquet?

## 4. Transformações básicas

Vamos usar este DataFrame:

| order_id | customer_id | city | quantity | unit_price | status |
|---:|---|---|---:|---:|---|
| 1001 | C001 | Porto | 2 | 64.95 | entregue |
| 1002 | C002 | Lisboa | 1 | 49.50 | cancelada |
| 1003 | C001 | Porto | 4 | 53.75 | entregue |
| 1004 | C003 | Braga | 2 | 35.00 | pendente |
| 1005 | C004 | Lisboa | 3 | 25.00 | entregue |

### 4.1 `select`

Seleciona colunas e também aceita expressões:

```python
from pyspark.sql import functions as F

df_resumo = df.select("order_id", "customer_id", "status")
df_resumo.show()
# Output esperado: apenas as colunas order_id, customer_id e status.
```

### 4.2 `filter` / `where`

As duas formas são equivalentes:

```python
df_entregues = df.filter(
    (F.col("status") == "entregue") & (F.col("quantity") >= 2)
)
df_entregues.select("order_id", "status", "quantity").show()
# Output esperado:
# +--------+--------+--------+
# |order_id|  status|quantity|
# +--------+--------+--------+
# |    1001|entregue|       2|
# |    1003|entregue|       4|
# |    1005|entregue|       3|
# +--------+--------+--------+
```

Usa `&`, `|` e `~` para AND, OR e NOT, respetivamente, e coloca cada condição entre parênteses.

### 4.3 `withColumn` e a diferença entre `col()` e `lit()`

- `F.col("quantity")` referencia os valores de uma coluna existente, linha a linha.
- `F.lit(0.23)` cria o mesmo valor literal em todas as linhas.

```python
df_calculado = (
    df
    .withColumn("subtotal_eur", F.round(F.col("quantity") * F.col("unit_price"), 2))
    .withColumn("iva_rate", F.lit(0.23))
    .withColumn("iva_eur", F.round(F.col("subtotal_eur") * F.col("iva_rate"), 2))
)
```

Antes:

| order_id | quantity | unit_price |
|---:|---:|---:|
| 1001 | 2 | 64.95 |
| 1002 | 1 | 49.50 |

Depois:

| order_id | quantity | unit_price | subtotal_eur | iva_rate | iva_eur |
|---:|---:|---:|---:|---:|---:|
| 1001 | 2 | 64.95 | 129.90 | 0.23 | 29.88 |
| 1002 | 1 | 49.50 | 49.50 | 0.23 | 11.39 |

Não uses `F.lit("quantity")` para referir a coluna: isso criaria o texto constante `"quantity"` em todas as linhas.

### 4.4 `distinct`

```python
df.select("city").distinct().orderBy("city").show()
# Output esperado:
# +------+
# |  city|
# +------+
# | Braga|
# |Lisboa|
# | Porto|
# +------+
```

`distinct()` remove duplicados considerando todas as colunas selecionadas. Para controlar as colunas usadas na deduplicação, usa `dropDuplicates(["coluna_a", "coluna_b"])`.

### 4.5 `orderBy`

```python
df.orderBy(F.col("unit_price").desc(), F.col("order_id").asc()).show()
# Output esperado: 1001 (64.95), 1003 (53.75), 1002 (49.50),
# 1004 (35.00) e 1005 (25.00).
```

Ordenação global pode exigir um *shuffle* entre executores; é útil no resultado final, mas deve ser usada com intenção em grandes volumes.

### Desafio 4

A partir de `df`:

1. mantém apenas encomendas não canceladas com `quantity >= 2`;
2. cria `subtotal_eur`;
3. adiciona a coluna literal `currency` com o valor `"EUR"`;
4. seleciona `order_id`, `customer_id`, `subtotal_eur` e `currency`;
5. ordena do maior para o menor subtotal;
6. prevê o resultado antes de chamar `show()`.

Resultado esperado:

| order_id | customer_id | subtotal_eur | currency |
|---:|---|---:|---|
| 1003 | C001 | 215.00 | EUR |
| 1001 | C001 | 129.90 | EUR |
| 1005 | C004 | 75.00 | EUR |
| 1004 | C003 | 70.00 | EUR |

## 5. Transformations (lazy) vs. Actions

Uma **Transformation** descreve um novo DataFrame/RDD, mas normalmente não processa os dados naquele momento. Spark regista as operações e constrói um plano lógico: isto é *lazy evaluation*.

Uma **Action** pede um resultado ou uma escrita e dispara a execução do plano. “Action” é mais preciso do que chamar-lhe “eager”: a Action executa imediatamente o plano lazy acumulado.

```text
read → filter → withColumn → select       count
       Transformations (plano lazy)  ───> Action (job executado)
```

| Transformations | Actions |
|---|---|
| `select`, `filter`, `withColumn` | `show`, `count`, `collect` |
| `distinct`, `orderBy` | `first`, `take`, `write...` |
| devolvem outro DataFrame | devolvem dados ao driver ou escrevem-nos |

```python
pipeline = (
    df
    .filter(F.col("status") == "entregue")  # Ainda não lê/processa tudo.
    .withColumn("subtotal_eur", F.col("quantity") * F.col("unit_price"))
    .select("order_id", "subtotal_eur")
)

pipeline.explain(mode="formatted")
# Mostra o plano; não devolve as linhas de negócio.

total_linhas = pipeline.count()  # Action: Spark executa o plano.
print(total_linhas)
# Output esperado: 3
```

Por que é útil? Antes de executar, o otimizador pode combinar filtros, eliminar colunas desnecessárias e escolher um plano físico mais eficiente.

Evita `collect()` em dados grandes: traz todas as linhas para a memória do Driver. Para inspeção, prefere `show(n)` ou `take(n)`.

### Desafio 5

No código seguinte, identifica as Transformations e Actions e prevê quantos jobs podem ser disparados:

```python
ativos = df.filter(F.col("status") != "cancelada")
totais = ativos.withColumn("subtotal_eur", F.col("quantity") * F.col("unit_price"))
totais.show()
print(totais.count())
```

Pergunta adicional: por que o Spark pode recalcular o mesmo plano para `show()` e `count()`? A otimização com `cache()` será estudada no Módulo 3.

## 6. Laboratório completo e funcional

Guarda o código como `modulo_01_lab.py` e executa-o a partir da raiz do projeto. O script cria os próprios dados temporários, por isso não depende de ficheiros prévios.

```python
from pathlib import Path
from tempfile import TemporaryDirectory

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    DoubleType,
    IntegerType,
    StringType,
    StructField,
    StructType,
)


def main() -> None:
    spark = (
        SparkSession.builder
        .appName("Modulo01Lab")
        .master("local[*]")
        .config("spark.api.mode", "classic")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("ERROR")

    schema = StructType([
        StructField("order_id", IntegerType(), False),
        StructField("customer_id", StringType(), False),
        StructField("city", StringType(), False),
        StructField("quantity", IntegerType(), False),
        StructField("unit_price", DoubleType(), False),
        StructField("status", StringType(), False),
    ])

    rows = [
        (1001, "C001", "Porto", 2, 64.95, "entregue"),
        (1002, "C002", "Lisboa", 1, 49.50, "cancelada"),
        (1003, "C001", "Porto", 4, 53.75, "entregue"),
        (1004, "C003", "Braga", 2, 35.00, "pendente"),
        (1005, "C004", "Lisboa", 3, 25.00, "entregue"),
    ]

    df = spark.createDataFrame(rows, schema)

    # Transformations: o Spark constrói o plano sem o executar já.
    resultado = (
        df
        .filter((F.col("status") != "cancelada") & (F.col("quantity") >= 2))
        .withColumn(
            "subtotal_eur",
            F.round(F.col("quantity") * F.col("unit_price"), 2),
        )
        .withColumn("currency", F.lit("EUR"))
        .select("order_id", "customer_id", "subtotal_eur", "currency")
        .orderBy(F.col("subtotal_eur").desc())
    )

    # Action: executa o plano e apresenta as linhas.
    resultado.show()
    # Output esperado:
    # +--------+-----------+------------+--------+
    # |order_id|customer_id|subtotal_eur|currency|
    # +--------+-----------+------------+--------+
    # |    1003|       C001|       215.0|     EUR|
    # |    1001|       C001|       129.9|     EUR|
    # |    1005|       C004|        75.0|     EUR|
    # |    1004|       C003|        70.0|     EUR|
    # +--------+-----------+------------+--------+

    # Demonstra leitura e escrita nos três formatos sem poluir o projeto.
    with TemporaryDirectory(prefix="pyspark_modulo01_") as temp_dir:
        base = Path(temp_dir)
        csv_path = str(base / "csv")
        json_path = str(base / "json")
        parquet_path = str(base / "parquet")

        # Cada escrita é uma Action.
        df.write.mode("overwrite").option("header", True).csv(csv_path)
        df.write.mode("overwrite").json(json_path)
        df.write.mode("overwrite").parquet(parquet_path)

        # O schema explícito protege os tipos em formatos de texto.
        lido_csv = spark.read.option("header", True).schema(schema).csv(csv_path)
        lido_json = spark.read.schema(schema).json(json_path)
        lido_parquet = spark.read.parquet(parquet_path)

        print("CSV:", lido_csv.count())
        print("JSON:", lido_json.count())
        print("Parquet:", lido_parquet.count())
        # Output esperado:
        # CSV: 5
        # JSON: 5
        # Parquet: 5

    spark.stop()


if __name__ == "__main__":
    main()
```

Execução:

```bash
scripts/run_spark.sh modulo_01_lab.py
```

## 7. Desafio final

Cria um pipeline de qualidade para encomendas:

1. define o schema explicitamente;
2. lê um CSV;
3. remove linhas duplicadas por `order_id`;
4. mantém apenas `quantity > 0` e `unit_price > 0`;
5. cria `subtotal_eur` e a coluna literal `country` com `"PT"`;
6. seleciona apenas as colunas finais;
7. ordena por `subtotal_eur` descendente;
8. guarda o resultado em Parquet;
9. conta quantas linhas válidas foram escritas;
10. assinala no código cada Transformation e cada Action.

**Extensão:** usa `explain(mode="formatted")` antes da primeira Action e procura `Filter`, `Project` e `Sort` no plano físico.

## Resumo e checklist

Neste módulo construíste a base de PySpark: a `SparkSession` cria o contexto de trabalho; DataFrames oferecem schema e otimização; schemas explícitos tornam a ingestão previsível; Transformations constroem um plano lazy; Actions executam-no.

- [ ] Consigo criar e terminar uma `SparkSession`.
- [ ] Sei explicar RDD vs. DataFrame e escolher DataFrame por defeito.
- [ ] Sei ler CSV e JSON com schema explícito.
- [ ] Sei explicar por que Parquet é adequado para analytics.
- [ ] Sei usar `select`, `filter`, `withColumn`, `distinct` e `orderBy`.
- [ ] Sei que `col()` referencia uma coluna e `lit()` cria um valor constante.
- [ ] Sei combinar condições com `&`, `|`, `~` e parênteses.
- [ ] Sei distinguir uma Transformation lazy de uma Action.
- [ ] Sei por que `collect()` é perigoso em datasets grandes.
- [ ] Completei o desafio final sem consultar a solução.

**Próximo módulo, quando solicitado:** GroupBy, agregações, joins (incluindo múltiplas chaves), Window Functions, strings, datas, condicionais e valores nulos.
