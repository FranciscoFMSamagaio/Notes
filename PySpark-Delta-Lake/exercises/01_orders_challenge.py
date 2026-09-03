from pathlib import Path

from pyspark.sql import SparkSession


ROOT = Path(__file__).resolve().parents[1]


spark = (
    SparkSession.builder.appName("exercise-01-orders-challenge")
    .master("local[*]")
    .getOrCreate()
)


orders = (
    spark.read.option("header", True)
    .option("inferSchema", True)
    .csv(str(ROOT / "data/raw/orders.csv"))
)
customers = (
    spark.read.option("header", True)
    .option("inferSchema", True)
    .csv(str(ROOT / "data/raw/customers.csv"))
)
products = (
    spark.read.option("header", True)
    .option("inferSchema", True)
    .csv(str(ROOT / "data/raw/products.csv"))
)

# Desafio:
# 1. Filtra apenas encomendas com status "delivered".
# 2. Junta orders com customers e products.
# 3. Cria uma coluna revenue = quantity * unit_price.
# 4. Mostra a receita total por cliente, ordenada da maior para a menor.
# 5. Mostra a receita total por categoria.
#
# Dica: vais precisar de:
# - from pyspark.sql.functions import col, sum, round
# - .filter(...)
# - .join(...)
# - .withColumn(...)
# - .groupBy(...).agg(...)
# - .orderBy(...)

print("Completa o desafio neste ficheiro.")
print("Quando acabares, compara com lessons/02_joins_and_aggregations.py.")

spark.stop()
