# Fabric PySpark notebook source. Run in a notebook with the Lakehouse attached.

# %% Read and flatten the source JSON
from delta.tables import DeltaTable
from pyspark.sql.functions import col, explode, to_date, to_timestamp

TABLE_NAME = "News_Project_LakeHouse.tbl_latest_news"

raw_news = (
    spark.read
    .option("multiLine", "true")
    .option("mode", "FAILFAST")
    .json("Files/Latest_News.json")
)

articles = (
    raw_news
    .select(explode(col("organic_results")).alias("article"))
    .select(
        col("article.title").alias("title"),
        col("article.snippet").alias("snippet"),
        col("article.favicon").alias("favicon"),
        col("article.link").alias("link"),
        col("article.thumbnail").alias("thumbnail"),
        col("article.source").alias("source"),
        col("article.date").alias("date"),
        to_date(to_timestamp(col("article.iso_date"))).alias("iso_date"),
    )
    .where(col("link").isNotNull() & col("snippet").isNotNull())
    .dropDuplicates(["link"])
)

display(articles.limit(10))

# %% Create the Delta table or merge new and changed articles
if spark.catalog.tableExists(TABLE_NAME):
    changed_columns = [
        "title", "snippet", "favicon", "link", "thumbnail", "source", "date", "iso_date"
    ]
    unchanged = " AND ".join(
        f"target.{name} <=> source.{name}" for name in changed_columns
    )

    (
        DeltaTable.forName(spark, TABLE_NAME)
        .alias("target")
        .merge(articles.alias("source"), "target.link = source.link")
        .whenMatchedUpdateAll(condition=f"NOT ({unchanged})")
        .whenNotMatchedInsertAll()
        .execute()
    )
else:
    articles.write.format("delta").saveAsTable(TABLE_NAME)

print(f"Upserted news articles into {TABLE_NAME}")