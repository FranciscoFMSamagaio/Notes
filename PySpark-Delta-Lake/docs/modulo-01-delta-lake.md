# Delta Lake — Módulo 1: do zero ao Lakehouse

> ACID, Transaction Log, CRUD, MERGE, Time Travel, evolução de schema, otimização, VACUUM e arquitetura Medallion.

## Objetivos

- explicar o problema que Delta Lake resolve;
- compreender ACID e o diretório `_delta_log`;
- criar, ler, atualizar, apagar e fazer *upsert* numa tabela;
- recuperar versões anteriores com Time Travel;
- controlar Schema Enforcement e Schema Evolution;
- usar `OPTIMIZE`, `ZORDER` e `VACUUM` com segurança;
- desenhar um pipeline Bronze/Silver/Gold.

## 1. O que é Delta Lake?

Delta Lake é uma camada de tabelas sobre ficheiros Parquet. Acrescenta um log de transações e metadados que permitem operações confiáveis num data lake.

```text
Tabela Delta
├── _delta_log/               <- commits, metadados e checkpoints
├── part-00000-....parquet    <- ficheiros de dados
└── part-00001-....parquet
```

| Data lake só com Parquet | Delta Lake |
|---|---|
| ficheiros sem transação comum | commits atómicos no Transaction Log |
| updates manuais e frágeis | `UPDATE`, `DELETE`, `MERGE` |
| schema pode divergir silenciosamente | enforcement/evolution controlados |
| histórico artesanal | Time Travel por versão/timestamp |

Delta não substitui Parquet: usa Parquet para os dados e o Transaction Log para saber que ficheiros compõem cada versão lógica da tabela.

## 2. Preparar o ambiente

Em Databricks com Delta Lake, a sessão `spark` já está configurada. Localmente, instala uma versão de `delta-spark` compatível com a tua versão de Apache Spark, consultando a matriz oficial de compatibilidade; não escolhas versões ao acaso.

Exemplo de criação local (quando as versões instaladas são compatíveis):

```python
from delta import configure_spark_with_delta_pip
from pyspark.sql import SparkSession

builder = (SparkSession.builder
    .appName("DeltaLakeModulo01")
    .master("local[*]")
    .config("spark.api.mode", "classic")
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog"))

spark = configure_spark_with_delta_pip(builder).getOrCreate()
spark.sparkContext.setLogLevel("ERROR")
```

## 3. ACID e Transaction Log

- **Atomicity:** uma escrita fica totalmente visível ou não fica visível.
- **Consistency:** cada commit leva a tabela de um estado válido para outro.
- **Isolation:** leitores obtêm um snapshot consistente enquanto existem escritas.
- **Durability:** um commit confirmado permanece registado.

### O que acontece numa escrita?

```text
1. O job escreve novos ficheiros Parquet
2. Valida conflitos com commits concorrentes
3. Publica um novo commit em _delta_log
4. Leitores passam a ver o novo snapshot
```

Delta usa controlo de concorrência otimista. O log contém ações como ficheiros adicionados/removidos, schema, propriedades e informação da operação. Não edites `_delta_log` manualmente.

## 4. Criar e ler uma tabela

```python
from pathlib import Path
from pyspark.sql import functions as F

delta_path = "data/delta/orders"

orders = spark.createDataFrame([
    (1001, "PT", "C001", "2026-08-01", 129.90, "entregue"),
    (1002, "PT", "C002", "2026-08-01", 49.50, "pendente"),
    (1003, "ES", "C001", "2026-08-03", 215.00, "entregue"),
], "order_id int, country string, customer_id string, order_date string, "
   "total_eur double, status string").withColumn("order_date", F.to_date("order_date"))

orders.write.format("delta").mode("overwrite").save(delta_path)
# Output esperado: versão 0 da tabela com 3 linhas.

current = spark.read.format("delta").load(delta_path)
current.orderBy("order_id").show()
# Output esperado: encomendas 1001, 1002 e 1003.
```

Com catálogo:

```python
spark.sql(f"CREATE TABLE IF NOT EXISTS orders USING DELTA LOCATION '{delta_path}'")
spark.table("orders").show()
```

`save(path)` cria uma tabela por caminho; `saveAsTable`/`CREATE TABLE` regista um nome num catálogo. Em produção, prefere catálogo e governação centralizados.

## 5. CRUD

### Create/Append

```python
new_order = spark.createDataFrame([
    (1004, "PT", "C003", "2026-08-04", 75.00, "pendente")
], "order_id int, country string, customer_id string, order_date string, "
   "total_eur double, status string").withColumn("order_date", F.to_date("order_date"))

new_order.write.format("delta").mode("append").save(delta_path)
# Output esperado: nova versão; total atual = 4 linhas.
```

### Read

```python
spark.read.format("delta").load(delta_path).filter("country = 'PT'").show()
# Output esperado: encomendas 1001, 1002 e 1004.
```

### Update e Delete

```python
from delta.tables import DeltaTable

table = DeltaTable.forPath(spark, delta_path)

table.update(
    condition="order_id = 1002",
    set={"status": F.lit("entregue")},
)
# Output esperado: order_id 1002 passa de pendente para entregue.

table.delete("status = 'cancelada'")
# Output esperado: todas as linhas canceladas deixam o snapshot atual.
```

Atualizar/apagar não significa editar Parquet no local. Delta grava novos ficheiros quando necessário e marca ficheiros antigos como removidos no log; por isso Time Travel continua possível antes de `VACUUM` eliminar ficheiros obsoletos.

### Desafio 1

Cria uma tabela `customers`, adiciona dois clientes, corrige uma cidade com `update` e remove registos de teste com `delete`. Consulta o histórico após cada operação.

## 6. MERGE / Upsert

*Upsert* significa atualizar correspondências e inserir novos registos. A condição deve representar a chave de negócio completa.

```python
updates = spark.createDataFrame([
    (1002, "PT", "C002", "2026-08-01", 49.50, "devolvida"), # atualização
    (1005, "PT", "C004", "2026-08-05", 310.00, "entregue"), # inserção
], "order_id int, country string, customer_id string, order_date string, "
   "total_eur double, status string").withColumn("order_date", F.to_date("order_date"))

(table.alias("target")
 .merge(updates.alias("source"),
        "target.country = source.country AND target.order_id = source.order_id")
 .whenMatchedUpdate(set={
     "customer_id": "source.customer_id",
     "order_date": "source.order_date",
     "total_eur": "source.total_eur",
     "status": "source.status",
 })
 .whenNotMatchedInsertAll()
 .execute())
# Output esperado: 1002 fica devolvida; 1005 é inserida.
```

Antes:

| country | order_id | status |
|---|---:|---|
| PT | 1002 | entregue |

Depois:

| country | order_id | status |
|---|---:|---|
| PT | 1002 | devolvida |
| PT | 1005 | entregue |

Garante que a fonte contém no máximo uma linha por chave; duplicados podem tornar o `MERGE` ambíguo. Deduplica com uma Window baseada num timestamp de atualização.

### Desafio 2

Implementa um upsert de clientes com chave composta `country` + `customer_id`. Conserva apenas o evento mais recente de cada chave antes do MERGE.

## 7. Time Travel e histórico

Cada commit cria uma versão. O histórico permite auditoria e investigação.

```python
table.history().select("version", "timestamp", "operation", "operationParameters").show(truncate=False)
# Output esperado: versões 0..N com WRITE, UPDATE, DELETE ou MERGE.

version_zero = (spark.read.format("delta")
    .option("versionAsOf", 0)
    .load(delta_path))
version_zero.show()
# Output esperado: as 3 linhas originais.

historical = (spark.read.format("delta")
    .option("timestampAsOf", "2026-09-03 10:00:00")
    .load(delta_path))
```

O timestamp tem de corresponder a um momento que exista no histórico real. Time Travel depende de ficheiros antigos ainda não removidos por políticas de retenção/VACUUM.

Em ambientes que suportem restore:

```python
table.restoreToVersion(0)
# Cria uma nova versão cujo estado lógico corresponde à versão 0;
# não apaga o histórico intermédio.
```

### Desafio 3

Compara a contagem e receita total entre duas versões. Restaura apenas se conseguires explicar o impacto nos consumidores da tabela.

## 8. Schema Enforcement e Evolution

Por defeito, Delta rejeita uma escrita incompatível: isso evita corrupção silenciosa do contrato.

```python
with_channel = current.withColumn("sales_channel", F.lit("online"))

(with_channel.write.format("delta").mode("append")
 .option("mergeSchema", "true")
 .save(delta_path))
# Output esperado: sales_channel é adicionada ao schema; linhas antigas têm null.
```

| Antes | Depois da evolução |
|---|---|
| `order_id, ..., status` | `order_id, ..., status, sales_channel` |
| linhas antigas | `sales_channel = null` |
| linhas novas | `sales_channel = online` |

Usa `mergeSchema` de forma explícita numa escrita controlada. A configuração global `spark.databricks.delta.schema.autoMerge.enabled=true` é mais abrangente e pode esconder alterações inesperadas. Schema Evolution adiciona/adapta colunas suportadas; não substitui validação de qualidade ou gestão de contratos.

## 9. OPTIMIZE e ZORDER

Muitas escritas pequenas geram muitos ficheiros pequenos, aumentando listagem e metadados. `OPTIMIZE` compacta ficheiros; `ZORDER` reorganiza dados para melhorar *data skipping* em colunas de filtro frequente.

```sql
OPTIMIZE orders;
OPTIMIZE orders ZORDER BY (country, customer_id);
```

Em APIs/ambientes Delta que disponibilizam o builder:

```python
DeltaTable.forPath(spark, delta_path).optimize().executeCompaction()
DeltaTable.forPath(spark, delta_path).optimize().executeZOrderBy("country", "customer_id")
```

Não uses ZORDER em todas as colunas. Escolhe poucas colunas seletivas e muito usadas em filtros. `OPTIMIZE` melhora layout físico, mas não altera os resultados lógicos. A disponibilidade e sintaxe podem variar entre Delta Lake open source e o runtime Databricks usado.

## 10. VACUUM: operação irreversível

`VACUUM` elimina ficheiros que já não pertencem ao snapshot atual e são mais antigos que a retenção.

```sql
VACUUM orders RETAIN 168 HOURS; -- 7 dias
```

```python
table.vacuum(168)
# Output esperado: lista/resultado dos ficheiros elegíveis, dependente do ambiente.
```

Depois da remoção física, versões antigas que dependem desses ficheiros podem deixar de ser legíveis. Nunca reduzas a retenção apenas para libertar espaço sem confirmar:

- jobs concorrentes e leitores de longa duração;
- requisitos de auditoria/recuperação;
- retenção do log e políticas da plataforma;
- existência de backups e testes de restauro.

### Desafio 4

Explica por que `DELETE` não liberta imediatamente todo o espaço e por que `VACUUM RETAIN 0 HOURS` é perigoso. Não executes retenção zero no laboratório.

## 11. Medallion Architecture

```text
Fontes → Bronze → Silver → Gold → BI / ML / APIs
          bruto     limpo     negócio
```

| Camada | Responsabilidade | Exemplo |
|---|---|---|
| Bronze | ingestão fiel, metadados técnicos | eventos de encomendas como recebidos |
| Silver | tipos, deduplicação, qualidade, conformidade | encomendas válidas e clientes normalizados |
| Gold | métricas e modelos orientados ao consumo | receita diária por país e canal |

### Pipeline completo

```python
bronze_path = "data/lake/bronze/orders"
silver_path = "data/lake/silver/orders"
gold_path = "data/lake/gold/daily_revenue"

# Bronze: preserva dados e acrescenta rastreabilidade.
bronze = (spark.read.option("header", True).csv("data/incoming/orders/*.csv")
    .withColumn("_ingested_at", F.current_timestamp())
    .withColumn("_source_file", F.input_file_name()))
bronze.write.format("delta").mode("append").save(bronze_path)

# Silver: tipa, valida e deduplica.
silver = (spark.read.format("delta").load(bronze_path)
    .withColumn("order_id", F.col("order_id").cast("int"))
    .withColumn("order_date", F.to_date("order_date", "yyyy-MM-dd"))
    .withColumn("total_eur", F.col("total_eur").cast("double"))
    .filter("order_id IS NOT NULL AND total_eur >= 0")
    .dropDuplicates(["country", "order_id"]))
silver.write.format("delta").mode("overwrite").save(silver_path)

# Gold: métrica pronta para consumo.
gold = (spark.read.format("delta").load(silver_path)
    .filter("status = 'entregue'")
    .groupBy("order_date", "country")
    .agg(F.round(F.sum("total_eur"), 2).alias("revenue_eur"),
         F.count("order_id").alias("orders")))
gold.write.format("delta").mode("overwrite").save(gold_path)
```

Em produção, tornar o Silver idempotente geralmente requer `MERGE`, chaves estáveis e uma estratégia clara para dados atrasados. Um simples `overwrite` serve para o laboratório, não é uma receita universal.

## 12. Desafio final

Constrói um mini-lakehouse de vendas:

1. ingere dois lotes na Bronze com metadados;
2. inclui no segundo lote uma correção e uma nova encomenda;
3. valida e deduplica na Silver;
4. aplica o segundo lote por `MERGE` com chave composta;
5. cria receita diária na Gold;
6. mostra o histórico da Silver;
7. lê a versão anterior e explica as diferenças;
8. adiciona `sales_channel` com evolução controlada;
9. propõe (sem executar cegamente) uma política de OPTIMIZE/VACUUM.

## Resumo e checklist

- [ ] Sei que Delta combina Parquet com um Transaction Log.
- [ ] Explico Atomicity, Consistency, Isolation e Durability.
- [ ] Sei criar, ler, atualizar e apagar dados Delta.
- [ ] Faço MERGE com a chave de negócio completa e fonte deduplicada.
- [ ] Consulto histórico e versões anteriores.
- [ ] Distingo Schema Enforcement de Schema Evolution.
- [ ] Sei quando OPTIMIZE/ZORDER podem ajudar.
- [ ] Compreendo o risco irreversível de VACUUM.
- [ ] Sei separar responsabilidades Bronze, Silver e Gold.
- [ ] Completei o desafio final.

Referências oficiais: [Delta Lake documentation](https://docs.delta.io/), [updates e MERGE](https://docs.delta.io/delta-update/) e [utility commands](https://docs.delta.io/delta-utility/).
