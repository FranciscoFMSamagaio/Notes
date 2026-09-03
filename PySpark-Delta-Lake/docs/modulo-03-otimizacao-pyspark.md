# Módulo 3 — Otimização, particionamento, cache e UDFs

> Um pipeline correto é o início; em escala, também precisa de ser observável e eficiente.

## Objetivos

- ler planos com `explain` e reconhecer *shuffle*;
- controlar partições sem criar o problema dos ficheiros pequenos;
- usar `cache`, `persist` e `unpersist` com intenção;
- preferir funções nativas e escolher UDFs apenas quando necessário;
- aplicar broadcast joins, AQE e boas práticas de escrita.

## 1. Modelo mental de execução

```text
Job (uma Action)
 ├─ Stage 1: leitura + filtro local
 ├─ shuffle: dados atravessam a rede
 └─ Stage 2: agregação + escrita
```

Operações estreitas, como `select` e muitos `filter`, podem ser executadas em cada partição. `groupBy`, `distinct`, `orderBy`, `repartition` e muitos joins provocam redistribuição (*shuffle*), normalmente cara em rede, disco e serialização.

```python
from pyspark.sql import SparkSession, functions as F

spark = (SparkSession.builder.appName("Modulo03")
         .master("local[*]").config("spark.api.mode", "classic").getOrCreate())
spark.sparkContext.setLogLevel("ERROR")

orders = spark.range(1, 1_000_001).select(
    F.col("id").alias("order_id"),
    (F.col("id") % 1000).cast("int").alias("customer_id"),
    (F.col("id") % 4).cast("int").alias("region_id"),
    F.round((F.col("id") % 500) * 1.25 + 10, 2).alias("total_eur"),
)

plan = orders.filter("total_eur >= 100").groupBy("region_id").sum("total_eur")
plan.explain(mode="formatted")
# Procura Exchange no plano: normalmente indica redistribuição/shuffle.
```

### Desafio 1

Compara os planos de `filter`, `orderBy` e `groupBy`. Identifica `Exchange`, `Sort` e `HashAggregate`.

## 2. Particionamento

Uma partição é uma unidade de paralelismo. Poucas partições criam tarefas enormes; demasiadas criam overhead e ficheiros pequenos.

```python
print(orders.rdd.getNumPartitions())
# Output: depende dos cores/configuração do ambiente.

by_region = orders.repartition(4, "region_id")
print(by_region.rdd.getNumPartitions())
# Output esperado: 4

fewer = by_region.coalesce(2)
print(fewer.rdd.getNumPartitions())
# Output esperado: 2
```

| Operação | Shuffle? | Uso típico |
|---|---|---|
| `repartition(n, cols...)` | Sim | aumentar/diminuir e redistribuir de forma equilibrada |
| `coalesce(n)` | Geralmente não | reduzir partições após um filtro |
| `repartitionByRange` | Sim | distribuir por intervalos para ordenação/faixas |

`coalesce` não deve ser usado para aumentar paralelismo. `repartition(1)` concentra tudo numa tarefa e é perigoso em produção.

### Particionar ficheiros por colunas

```python
(orders.withColumn("order_date", F.date_add(F.lit("2026-01-01").cast("date"),
                                             (F.col("order_id") % 365).cast("int")))
 .withColumn("year", F.year("order_date"))
 .withColumn("month", F.month("order_date"))
 .write.mode("overwrite").partitionBy("year", "month").parquet("data/output/orders"))
# Estrutura esperada: year=2026/month=1/..., year=2026/month=2/...
```

Escolhe colunas frequentemente filtradas e de cardinalidade moderada. Não particiones por `order_id`: milhões de valores podem criar milhões de diretórios.

### Desafio 2

Escreve por `region_id`, lê apenas `region_id = 2` e verifica `PartitionFilters` com `explain`. Compara com particionamento por `customer_id`.

## 3. Cache e persistência

Cache só compensa quando o mesmo resultado caro é reutilizado.

```python
clean = orders.filter("total_eur >= 100").cache()

clean.count()  # Materializa o cache. Output esperado: depende dos dados gerados.
clean.groupBy("region_id").sum("total_eur").show()  # Reutiliza-o.
clean.groupBy("customer_id").count().show(5)         # Reutiliza-o novamente.

print(clean.is_cached)
# Output esperado: True

clean.unpersist()
print(clean.is_cached)
# Output esperado: False
```

`cache()` usa o nível de armazenamento predefinido do DataFrame. Para controlar memória/disco:

```python
from pyspark import StorageLevel

reused = orders.persist(StorageLevel.MEMORY_AND_DISK)
reused.count()
# ... múltiplas utilizações ...
reused.unpersist()
```

Não faças cache de tudo: ocupa memória, pode aumentar garbage collection e compete com execução. Faz cache depois de filtros/seleção de colunas, materializa-o e remove-o assim que deixar de ser necessário.

### Desafio 3

Cria um pipeline reutilizado por três Actions. Observa a Spark UI ou os planos antes/depois de `cache()` e garante `unpersist()`.

## 4. Otimizações essenciais

### 4.1 Filtrar e projetar cedo

```python
small_orders = (spark.read.parquet("data/orders")
    .select("customer_id", "region_id", "total_eur")
    .filter(F.col("total_eur") >= 100))
```

Parquet permite *column pruning* e *predicate pushdown*: o Spark pode ler apenas as colunas e blocos relevantes.

### 4.2 Broadcast join

Se uma dimensão for realmente pequena, envia-a para cada executor e evita o shuffle do dataset grande.

```python
regions = spark.createDataFrame([(0, "Norte"), (1, "Centro"), (2, "Sul"), (3, "Ilhas")],
                                "region_id int, region_name string")
enriched = orders.join(F.broadcast(regions), "region_id", "left")
enriched.explain()
# Output esperado no plano: BroadcastHashJoin.
```

Não forces broadcast numa tabela grande: cada executor precisa de a guardar. O Spark também pode escolher broadcast automaticamente com base em estatísticas.

### 4.3 AQE e skew

Adaptive Query Execution (AQE) reotimiza o plano com estatísticas recolhidas durante a execução e está ativado por defeito nas versões atuais do Spark.

```python
print(spark.conf.get("spark.sql.adaptive.enabled"))
# Output esperado nas versões atuais: true
```

Um valor de chave desproporcional cria *data skew*: uma tarefa recebe muito mais dados que as restantes. Verifica distribuição, AQE, qualidade das chaves e, só quando necessário, técnicas como *salting*.

## 5. UDFs: último recurso, não primeira opção

Funções nativas são visíveis ao otimizador e executadas no motor Spark. Uma Python UDF pode introduzir serialização entre JVM e Python.

```python
# Melhor: função nativa.
native = orders.withColumn(
    "value_band",
    F.when(F.col("total_eur") >= 300, "premium")
     .when(F.col("total_eur") >= 100, "standard")
     .otherwise("small"),
)
```

Quando a lógica não existe na API nativa:

```python
from pyspark.sql.types import StringType

@F.udf(returnType=StringType(), useArrow=True)
def mask_customer(customer_id: int) -> str:
    """Cria um identificador mascarado para demonstração."""
    return f"CLIENTE-{customer_id:04d}" if customer_id is not None else None

masked = orders.withColumn("customer_mask", mask_customer("customer_id"))
masked.select("customer_id", "customer_mask").show(3)
# Output esperado: 1 -> CLIENTE-0001, 2 -> CLIENTE-0002, 3 -> CLIENTE-0003
```

Ordem de preferência: função nativa → expressão SQL → UDF vetorizada/Arrow → UDF Python escalar tradicional. Mede sempre: clareza não substitui benchmark.

### Desafio 4

Implementa uma limpeza de código primeiro com UDF e depois com `upper`, `trim` e `regexp_replace`. Compara planos e tempo sobre um milhão de linhas.

## 6. Checklist de diagnóstico

Quando um job está lento:

1. confirma volume, schema e número de partições;
2. abre `explain("formatted")` e Spark UI;
3. procura shuffles, sorts, skew e leituras excessivas;
4. reduz dados cedo e usa formatos colunares;
5. verifica estratégia de join e estatísticas;
6. reutiliza resultados caros com cache apenas quando justificado;
7. reduz UDFs Python;
8. mede novamente com dados representativos.

## 7. Desafio final

Otimiza um pipeline que lê encomendas, junta uma dimensão de regiões, agrega por mês/região e produz milhares de ficheiros pequenos. Entrega uma versão com:

- projeção e filtros antecipados;
- broadcast justificado por tamanho;
- número de partições de shuffle documentado;
- escrita particionada por mês (não por ID);
- cache apenas se o resultado for usado por pelo menos duas Actions;
- plano físico antes/depois e medições reproduzíveis.

## Resumo e checklist

- [ ] Distingo operações estreitas de shuffles.
- [ ] Sei interpretar `Exchange` e `BroadcastHashJoin`.
- [ ] Sei escolher `repartition` vs. `coalesce`.
- [ ] Evito partições de cardinalidade excessiva e ficheiros pequenos.
- [ ] Uso `cache`/`persist` apenas com reutilização e faço `unpersist`.
- [ ] Sei quando broadcast ajuda e quando prejudica.
- [ ] Prefiro funções nativas a UDFs Python.
- [ ] Sei que otimização exige medição, não receitas universais.

Referências: [Performance Tuning](https://spark.apache.org/docs/latest/sql-performance-tuning) e [UDFs/UDTFs em PySpark](https://spark.apache.org/docs/latest/api/python/user_guide/udfandudtf.html).
