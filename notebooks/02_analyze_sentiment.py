# Fabric PySpark notebook source. Run after the ingestion notebook.

# %% Read curated articles and configure sentiment analysis
from delta.tables import DeltaTable
from pyspark.sql.functions import col
from synapse.ml.services import AnalyzeText

SOURCE_TABLE = "News_Project_LakeHouse.tbl_latest_news"
TARGET_TABLE = "News_Project_LakeHouse.tbl_sentiment_analysis"

articles = spark.table(SOURCE_TABLE).where(col("snippet").isNotNull())

sentiment_model = (
    AnalyzeText()
    .setTextCol("snippet")
    .setKind("SentimentAnalysis")
    .setOutputCol("response")
    .setErrorCol("error")
)

scored_articles = (
    sentiment_model.transform(articles)
    .withColumn("sentiment", col("response.documents.sentiment"))
    .drop("response", "error")
)

display(scored_articles.select("title", "source", "sentiment").limit(10))

# %% Create the Delta table or upsert sentiment results by article link
if spark.catalog.tableExists(TARGET_TABLE):
    (
        DeltaTable.forName(spark, TARGET_TABLE)
        .alias("target")
        .merge(scored_articles.alias("source"), "target.link = source.link")
        .whenMatchedUpdateAll()
        .whenNotMatchedInsertAll()
        .execute()
    )
else:
    scored_articles.write.format("delta").saveAsTable(TARGET_TABLE)

print(f"Upserted sentiment results into {TARGET_TABLE}")