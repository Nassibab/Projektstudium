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
# Trainiert auf professor_dataset und predicted anschließend nur Bluesky-Daten.
# ----------------------------------------------------------------------------------
predict_bluesky_synthetic_roles <- function() {
  data <- load_analysis_data()

  train_data <- prepare_full_training_data(data)
  bluesky_data <- prepare_full_bluesky_data(data)

  tfidf_result <- create_tfidf_features(train_data, bluesky_data)

  missing_structure_features <- setdiff(STRUCTURE_FEATURES, names(bluesky_data))

  if (length(missing_structure_features) > 0) {
    stop(paste(
      "Folgende Bluesky-Strukturfeatures fehlen:",
      paste(missing_structure_features, collapse = ", ")
    ))
  }

  train_model_data <- train_data[, c("synthetic_role", STRUCTURE_FEATURES), drop = FALSE]
  bluesky_model_data <- bluesky_data[, STRUCTURE_FEATURES, drop = FALSE]

  train_model_data <- cbind(train_model_data, tfidf_result$train_tfidf)
  bluesky_model_data <- cbind(bluesky_model_data, tfidf_result$test_tfidf)

  train_model_data <- handle_missing_values(train_model_data)
  bluesky_model_data <- handle_missing_values(bluesky_model_data)
  bluesky_model_data <- align_factor_levels(train_model_data, bluesky_model_data)

  task <- TaskClassif$new(
    id = "bluesky_prediction_model",
    backend = train_model_data,
    target = "synthetic_role"
  )

  learner <- lrn(
    "classif.ranger",
    predict_type = "prob",
    importance = "impurity",
    num.threads = RANGER_NUM_THREADS
  )

  learner$train(task)

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
    comment_created_at = bluesky_data$comment_created_at,
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
    model = "classif.ranger",
    target = "synthetic_role",
    predicted_rows = nrow(result),
    predictions = head(result, 100),
    save_status = save_status
  )
}