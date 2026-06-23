# ----------------------------------------------------------------------------------
# Bluesky-Vorhersage mit dem vollständigen Modell
# ----------------------------------------------------------------------------------


# ----------------------------------------------------------------------------------
# Bereitet Bluesky-Daten mit denselben Struktur-/Kontextfeatures wie Training vor.
# ----------------------------------------------------------------------------------
prepare_full_bluesky_data <- function(data) {
  bluesky_data <- data[data[["source_platform"]] == "bluesky", ]

  if (nrow(bluesky_data) == 0) {
    stop("Keine Bluesky-Daten gefunden.")
  }

  bluesky_data <- bluesky_data %>%
    mutate(
      synthetic_role = factor(1, levels = c(1, 2, 3, 4, 5, 6, 7)),

      created_at = as.character(
        as.POSIXct(created_at, tz = "Europe/Berlin")
      ),

      created_timestamp = suppressWarnings(
        as.numeric(as.POSIXct(created_at, tz = "Europe/Berlin"))
      )
    )

  if (!"date_timestamp" %in% names(bluesky_data)) {
    bluesky_data$date_timestamp <- bluesky_data$created_timestamp
  }

  bluesky_data$comments_count <- suppressWarnings(as.integer(bluesky_data$comments_count))

  bluesky_data <- add_user_features(bluesky_data)
  bluesky_data <- add_thread_features(bluesky_data)
  bluesky_data <- add_lexicon_features(bluesky_data)
  bluesky_data <- add_toxicity_features(bluesky_data)
  bluesky_data <- add_context_features(bluesky_data)
  bluesky_data <- coerce_analysis_column_types(bluesky_data)
  bluesky_data <- handle_missing_values(bluesky_data)

  bluesky_data
}

# ----------------------------------------------------------------------------------
# Lädt gespeichertes Professor-Modell und predicted Bluesky.
# Trainiert NICHT neu.
# ----------------------------------------------------------------------------------
predict_bluesky_synthetic_roles <- function() {
  data <- load_analysis_bluesky ()

  if (!file.exists(MODEL_PATH)) {
    stop("Kein gespeichertes Modell gefunden. Bitte zuerst /train-full-model ausführen.")
  }

  # Gespeichertes Modell laden
  model_bundle <- readRDS(MODEL_PATH)

  learner <- model_bundle$learner
  train_data <- model_bundle$train_data_for_tfidf
  train_model_template <- model_bundle$train_model_template
  feature_cols <- model_bundle$feature_cols

  # Bluesky-Daten vorbereiten
  bluesky_data <- prepare_full_bluesky_data(data)

  # TF-IDF mit Professor-Trainingsdaten als Referenz bauen
  tfidf_result <- create_tfidf_features(train_data, bluesky_data)

  # Strukturfeatures + TF-IDF für Bluesky bauen
  bluesky_model_data <- bluesky_data[, STRUCTURE_FEATURES, drop = FALSE]
  bluesky_model_data <- cbind(bluesky_model_data, tfidf_result$test_tfidf)

  # Missing Values und Faktor-Level an Trainingsmodell anpassen
  bluesky_model_data <- handle_missing_values(bluesky_model_data)
  bluesky_model_data <- align_factor_levels(train_model_template, bluesky_model_data)

  # Gleiche Spalten-Reihenfolge wie beim Training
  bluesky_model_data <- bluesky_model_data[, feature_cols, drop = FALSE]

  # Prediction ohne Label
  pred <- learner$predict_newdata(bluesky_model_data)

  predicted_role <- as.character(pred$response)

  predicted_role[
    bluesky_data$is_thread_start != 1 &
      predicted_role == "1"
  ] <- "3"

  result <- data.frame(
    comment_id = bluesky_data$comment_id,
    thread_id = bluesky_data$thread_id,
    login = bluesky_data$login,
    text = bluesky_data$text,
    created_at = bluesky_data$created_at,
    predicted_synthetic_role = predicted_role,
    predicted_synthetic_role_label = dplyr::recode(
      predicted_role,
      !!!ROLE_LABELS
    ),
    as.data.frame(pred$prob)
  )

  probability_names <- paste0("prob_", unname(ROLE_LABELS))
  colnames(result)[8:(7 + length(probability_names))] <- probability_names

  documents <- build_bluesky_result_documents(
    bluesky_data = bluesky_data,
    pred = pred,
    predicted_role = predicted_role
  )

  save_status <- save_bluesky_predictions_to_api(
    comment_results = documents$comment_results,
    thread_results = documents$thread_results,
    user_results = documents$user_results,
    model_results = documents$model_results
  )

  list(
    status = "success",
    model_loaded_from = MODEL_PATH,
    target = "synthetic_role",
    predicted_rows = nrow(result),
    predictions = head(result, 100),
    save_status = save_status
  )
}