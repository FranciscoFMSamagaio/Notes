from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("intro-pyspark").master("local[*]").getOrCreate()

data = [
    ("Ana", "Data Engineer", 2),
    ("Bruno", "Analytics Engineer", 4),
    ("Carla", "Data Analyst", 3),
]

df = spark.createDataFrame(data, ["name", "role", "years_experience"])

df.show(truncate=False)

spark.stop()
