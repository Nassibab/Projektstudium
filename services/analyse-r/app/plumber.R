# ---------------------------------------------------------------------------
# Plumber API für analyse-r
# ---------------------------------------------------------------------------
# Diese Datei stellt die R-Analyse über HTTP-Endpunkte bereit.

library(plumber)
library(jsonlite)
library(dplyr)
library(mlr3)
library(mlr3learners)
library(ranger)
library(httr)
library(quanteda)
library(Matrix)

source("analysis_configuration.R")
source("analysis_data_loader.R")
source("professor_dataset_preprocessing.R")
source("shitstorm_model_training.R")
source("bluesky_scenario_prediction.R")
source("prediction_results_table.R")
source("tfidf_feature_engineering.R")
source("thread_feature_engineering.R")
source("user_feature_engineering.R")
source("toxicity_feature_engineering.R")
source("lexicon_feature_engineering.R")
source("context_feature_engineering.R")
source("analysis_result_storage.R")
source("data_type_cleaning.R")


#* Health Check
#* @get /health
function() {
  list(status = "ok", service = "analyse-r")
}

#* Test: Daten aus API holen
#* @get /test-data
function() {
  data <- load_analysis_data()

  list(
    status = "success",
    rows = nrow(data),
    columns = colnames(data),
    preview = head(data, 5)
  )
}

#* ML-Daten vorbereiten
#* @get /prepare-ml-data
function() {
  data <- load_analysis_data()

  professor_data <- data[data[["source_platform"]] == "professor_dataset", ]
  bluesky_data <- data[data[["source_platform"]] == "bluesky", ]

  list(
    status = "success",
    total_rows = nrow(data),
    professor_rows = nrow(professor_data),
    bluesky_rows = nrow(bluesky_data),
    columns = names(data),
    professor_preview = head(professor_data, 3),
    bluesky_preview = head(bluesky_data, 3)
  )
}


#* Predict Bluesky synthetic roles as JSON
#* @get /predict-bluesky
function() {
  predict_bluesky_synthetic_roles()
}

#* Train full synthetic role model with TF-IDF
#* @get /train-full-model
function() {
  data <- load_analysis_data()
  result <- train_full_synthetic_role_model(data)

  list(
    status = "success",
    model = "classif.ranger",
    target = "synthetic_role",

    total_rows = result$total_rows,
    train_rows = result$train_rows,
    test_rows = result$test_rows,

    n_features_total = result$n_features_total,
    n_tfidf_features = result$n_tfidf_features,

    accuracy = result$accuracy,
    classification_error = result$classification_error,
    confusion = result$confusion,

    prediction_table = result$prediction_table,
    feature_importance = result$feature_importance,
    top_tfidf_features = result$top_tfidf_features,
    top_non_tfidf_features = result$top_non_tfidf_features,
    results_row = result$results_row,
    thread_feature_preview = result$thread_feature_preview,


    tfidf_time_seconds = result$tfidf_time,
    training_time_seconds = result$training_time,
    prediction_time_seconds = result$prediction_time,
    total_time_seconds = result$total_time
  )
}

#Test
#* Kommentar an Moderation senden
#* @post /send-to-moderation
function() {
  predict_bluesky_synthetic_roles()
}

#* Random Forest Training mit Ranger
#* @get /train-ranger
function() {
  data <- load_analysis_data()
  result <- train_full_synthetic_role_model(data)

  list(
    status = "sent",
    moderation_status = httr::status_code(response),
    moderation_response = httr::content(response, as = "parsed")
  )
}