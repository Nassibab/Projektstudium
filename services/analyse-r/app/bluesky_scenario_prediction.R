library(mlr3)
library(mlr3learners)
library(ranger)


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

      comment_created_at = as.character(
        as.POSIXct(created, tz = "Europe/Berlin")
      ),

      created_timestamp = suppressWarnings(
        as.numeric(as.POSIXct(created, tz = "Europe/Berlin"))
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
# Baut getrennte Kommentar-, Thread- und User-Dokumente für MongoDB.
# ----------------------------------------------------------------------------------
build_bluesky_result_documents <- function(bluesky_data, pred, predicted_role) {
  probability_df <- as.data.frame(pred$prob)
  probability_names <- paste0("prob_", unname(ROLE_LABELS))
  names(probability_df) <- probability_names

  comment_results <- bluesky_data %>%
    select(any_of(c(
      "comment_id",
      "thread_id",
      "login",
      "text",

      "comment_created_at",

      "attack_score",
      "toxicity_score",
      "is_attacking",

      "irony",
      "swearword_count",
      "insult_count",
      "negative_word_count",
      "direct_address_count",
      "imperative_count",
      "accusation_marker_count",
      "mockery_marker_count",

      "reply_depth",
      "parent_is_root",
      "num_children",

      "thread_position_abs",
      "thread_position_rel",
      "num_previous_comments",
      "is_thread_start",
      "is_reply",

      "prev_attack_rate",
      "prev_toxicity_score_mean",
      "prev_attack_count",
      "prev_toxicity_score_max",
      "prev_attack_score_max",
      "recent_attack_rate_3",
      "recent_attack_rate_5",
      "attack_streak_current",

      "is_target_login_numeric",
      "target_recently_attacked",
      "reply_after_attack",
      "target_response_context_score"
    ))) %>%
    mutate(
      predicted_synthetic_role = predicted_role,
      predicted_synthetic_role_label = dplyr::recode(
        predicted_role,
        !!!ROLE_LABELS
      ),
      source_platform = "bluesky",
      analysis_saved_at = as.character(Sys.time())
    ) %>%
    bind_cols(probability_df) %>%
    mutate(across(where(is.factor), as.character))

  thread_results <- bluesky_data %>%
    group_by(thread_id) %>%
    summarise(
      thread_size = first(thread_size),
      thread_comment_count = first(thread_comment_count),
      thread_user_count = first(thread_user_count),
      thread_mean_comments_per_user = first(thread_mean_comments_per_user),
      thread_max_comments_by_one_user = first(thread_max_comments_by_one_user),
      thread_single_comment_user_count = first(thread_single_comment_user_count),
      thread_max_user_share = first(thread_max_user_share),
      thread_single_comment_user_share = first(thread_single_comment_user_share),

      first_comment_created_at = first(comment_created_at),
      last_comment_created_at = last(comment_created_at),

      mean_toxicity_score = mean(as.numeric(toxicity_score), na.rm = TRUE),
      max_toxicity_score = max(as.numeric(toxicity_score), na.rm = TRUE),
      mean_attack_score = mean(as.numeric(attack_score), na.rm = TRUE),
      max_attack_score = max(as.numeric(attack_score), na.rm = TRUE),

      mean_prev_attack_rate = mean(prev_attack_rate, na.rm = TRUE),
      max_prev_attack_rate = max(prev_attack_rate, na.rm = TRUE),
      max_recent_attack_rate_3 = max(recent_attack_rate_3, na.rm = TRUE),
      max_recent_attack_rate_5 = max(recent_attack_rate_5, na.rm = TRUE),
      max_attack_streak_current = max(attack_streak_current, na.rm = TRUE),

      source_platform = "bluesky",
      analysis_saved_at = as.character(Sys.time()),
      .groups = "drop"
    )

  user_results <- bluesky_data %>%
    group_by(login) %>%
    summarise(
      login_count = first(login_count),
      login_percentage = first(login_percentage),
      frequency_group = first(frequency_group),

      total_comments = n(),
      total_threads = n_distinct(thread_id),

      mean_toxicity_score = mean(as.numeric(toxicity_score), na.rm = TRUE),
      max_toxicity_score = max(as.numeric(toxicity_score), na.rm = TRUE),
      mean_attack_score = mean(as.numeric(attack_score), na.rm = TRUE),
      max_attack_score = max(as.numeric(attack_score), na.rm = TRUE),

      mean_swearword_count = mean(swearword_count, na.rm = TRUE),
      mean_insult_count = mean(insult_count, na.rm = TRUE),
      mean_negative_word_count = mean(negative_word_count, na.rm = TRUE),

      mean_prev_attack_rate = mean(prev_attack_rate, na.rm = TRUE),
      max_prev_attack_rate = max(prev_attack_rate, na.rm = TRUE),

      source_platform = "bluesky",
      analysis_saved_at = as.character(Sys.time()),
      .groups = "drop"
    )

  list(
    comment_results = comment_results,
    thread_results = thread_results,
    user_results = user_results,
    model_results = data.frame(
      model = "bluesky_full_prediction",
      target = "synthetic_role",
      predicted_rows = nrow(comment_results),
      predicted_threads = nrow(thread_results),
      predicted_users = nrow(user_results),
      analysis_saved_at = as.character(Sys.time())
    )
  )
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
    comment_id = prediction_data$original$comment_id,
    thread_id = prediction_data$original$thread_id,
    text = prediction_data$original$text,
    predicted_scenario_type = pred$response,
    as.data.frame(pred$prob)
  )

  if (ncol(result) >= 10) {
    colnames(result)[5:10] <- names(SCENARIO_LABELS)
  }

  result$predicted_scenario_type <- dplyr::recode(
    as.character(result$predicted_scenario_type),
    !!!SCENARIO_LABELS
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