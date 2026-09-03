from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, round as spark_round, sum as spark_sum, to_date


ROOT = Path(__file__).resolve().parents[1]
LAKEHOUSE = ROOT / "data/lakehouse"


spark = (
    SparkSession.builder.appName("lesson-03-bronze-silver-gold")
    .master("local[*]")
    .getOrCreate()
)


def read_raw_csv(name: str):
    return (
        spark.read.option("header", True)
        .option("inferSchema", True)
        .csv(str(ROOT / f"data/raw/{name}.csv"))
    )


# Bronze: dados ingeridos quase crus.
bronze_orders = read_raw_csv("orders")
bronze_customers = read_raw_csv("customers")
bronze_products = read_raw_csv("products")

bronze_orders.write.mode("overwrite").parquet(str(LAKEHOUSE / "bronze/orders"))
bronze_customers.write.mode("overwrite").parquet(str(LAKEHOUSE / "bronze/customers"))
bronze_products.write.mode("overwrite").parquet(str(LAKEHOUSE / "bronze/products"))

# Silver: dados limpos, tipados e prontos para combinacao.
silver_orders = (
    bronze_orders.withColumn("order_date", to_date(col("order_date")))
    .withColumn("quantity", col("quantity").cast("int"))
    .filter(col("quantity") > 0)
)

silver_orders.write.mode("overwrite").parquet(str(LAKEHOUSE / "silver/orders"))

# Gold: metricas prontas para consumo.
gold_sales_by_customer = (
    silver_orders.filter(col("status") == "delivered")
    .join(bronze_customers, on="customer_id", how="left")
    .join(bronze_products, on="product_id", how="left")
    .withColumn("revenue", spark_round(col("quantity") * col("unit_price"), 2))
    .groupBy("customer_id", "name", "country", "segment")
    .agg(
        spark_sum("quantity").alias("items_sold"),
        spark_round(spark_sum("revenue"), 2).alias("total_revenue"),
    )
    .orderBy(col("total_revenue").desc())
)

gold_sales_by_customer.write.mode("overwrite").parquet(
    str(LAKEHOUSE / "gold/sales_by_customer")
)

print("\nGold table: sales_by_customer")
gold_sales_by_customer.show(truncate=False)

print(f"\nFicheiros escritos em: {LAKEHOUSE}")

spark.stop()
