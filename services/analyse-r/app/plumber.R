library(plumber)
library(jsonlite)
library(dplyr)
library(mlr3)
library(mlr3learners)
library(ranger)

source("analysis_configuration.R")
source("analysis_data_loader.R")
source("professor_dataset_preprocessing.R")
source("bluesky_data_preprocessing.R")
source("shitstorm_model_training.R")
source("bluesky_scenario_prediction.R")
source("prediction_results_table.R")

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

#* Einfache Analyse
#* @get /analyse-summary
function() {
  data <- load_analysis_data()

  list(
    status = "success",
    total_comments = nrow(data),
    platforms = as.list(table(data$source_platform)),
    source_types = as.list(table(data$source_type))
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

#* Professor-Daten 80/20 aufteilen
#* @get /split-professor-data
function() {
  data <- load_analysis_data()
  professor_data <- data[data[["source_platform"]] == "professor_dataset", ]

  set.seed(RANDOM_SEED)

  n <- nrow(professor_data)
  train_indices <- sample(seq_len(n), size = floor(TRAIN_RATIO * n))

  train_data <- professor_data[train_indices, ]
  test_data <- professor_data[-train_indices, ]

  list(
    status = "success",
    total_professor_rows = n,
    train_rows = nrow(train_data),
    test_rows = nrow(test_data),
    train_preview = head(train_data, 3),
    test_preview = head(test_data, 3)
  )
}

#* Modelltraining mit rpart
#* @get /train-model
function() {
  train_rpart_model()
}

#* Random Forest Training mit Ranger
#* @get /train-ranger
function() {
  train_ranger_model()
}

#* Bluesky-Daten als JSON vorhersagen
#* @get /predict-bluesky
function() {
  result <- predict_bluesky_scenarios()

  list(
    status = "success",
    model = "classif.ranger",
    predicted_rows = nrow(result),
    predictions = result
  )
}

#* Bluesky-Daten als HTML-Tabelle anzeigen
#* @get /predict-bluesky-table
#* @html
function(res) {
  result <- predict_bluesky_scenarios()
  html <- create_prediction_html_table(result)

  res$setHeader("Content-Type", "text/html; charset=utf-8")

  html
}





source("LLM_Service.R")

#* Test LLM
#* @get /test-llm
function() {
  answer <- call_llm("Sag Hallo.")

  list(
    answer = answer
  )
}