library(plumber)
library(jsonlite)

#* Health Check
#* @get /health
function() {
  list(status = "ok", service = "analyse-r")
}

#* Test: Daten aus API holen
#* @get /test-data
function() {
  data <- jsonlite::fromJSON("http://api:8000/analysis/comments")

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
  data <- jsonlite::fromJSON("http://api:8000/analysis/comments")

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
  data <- jsonlite::fromJSON(
    "http://api:8000/analysis/comments",
    flatten = TRUE
  )

  data <- as.data.frame(data)

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
  data <- jsonlite::fromJSON(
    "http://api:8000/analysis/comments",
    flatten = TRUE
  )

  data <- as.data.frame(data)

  professor_data <- data[data[["source_platform"]] == "professor_dataset", ]

  set.seed(123)

  n <- nrow(professor_data)
  train_indices <- sample(seq_len(n), size = floor(0.8 * n))

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