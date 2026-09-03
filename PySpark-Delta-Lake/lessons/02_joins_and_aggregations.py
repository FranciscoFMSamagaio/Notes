from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, round as spark_round, sum as spark_sum


ROOT = Path(__file__).resolve().parents[1]


spark = (
    SparkSession.builder.appName("lesson-02-joins-and-aggregations")
    .master("local[*]")
    .getOrCreate()
)


def read_csv(name: str):
    return (
        spark.read.option("header", True)
        .option("inferSchema", True)
        .csv(str(ROOT / f"data/raw/{name}.csv"))
    )


orders = read_csv("orders")
customers = read_csv("customers")
products = read_csv("products")

sales = (
    orders.filter(col("status") == "delivered")
    .join(customers, on="customer_id", how="left")
    .join(products, on="product_id", how="left")
    .withColumn("revenue", spark_round(col("quantity") * col("unit_price"), 2))
)

print("\nTabela enriquecida:")
sales.select(
    "order_id",
    "name",
    "country",
    "product_name",
    "category",
    "quantity",
    "revenue",
).show(truncate=False)

print("\nReceita por pais:")
sales.groupBy("country").agg(
    spark_round(spark_sum("revenue"), 2).alias("total_revenue")
).orderBy(col("total_revenue").desc()).show(truncate=False)

print("\nReceita por categoria:")
sales.groupBy("category").agg(
    spark_round(spark_sum("revenue"), 2).alias("total_revenue")
).orderBy(col("total_revenue").desc()).show(truncate=False)

spark.stop()
