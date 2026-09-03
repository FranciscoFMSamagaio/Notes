from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, to_date


ROOT = Path(__file__).resolve().parents[1]


spark = (
    SparkSession.builder.appName("lesson-01-dataframe-basics")
    .master("local[*]")
    .getOrCreate()
)


orders = (
    spark.read.option("header", True)
    .option("inferSchema", True)
    .csv(str(ROOT / "data/raw/orders.csv"))
)

print("\nSchema original:")
orders.printSchema()

print("\nPrimeiras encomendas:")
orders.show(truncate=False)

clean_orders = (
    orders.withColumn("order_date", to_date(col("order_date")))
    .withColumn("quantity", col("quantity").cast("int"))
)

delivered_orders = clean_orders.filter(col("status") == "delivered")

print("\nApenas encomendas entregues:")
delivered_orders.select(
    "order_id", "customer_id", "product_id", "order_date", "quantity"
).show(truncate=False)

print("\nContagem por estado:")
clean_orders.groupBy("status").count().orderBy("status").show(truncate=False)

spark.stop()
