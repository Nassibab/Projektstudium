# ------------------------------------------------------------
# Analyse-Ergebnisse an FastAPI senden
# ------------------------------------------------------------
# Diese Datei trennt Ergebnisse sauber nach Ebene:
# Kommentar-Ergebnisse, Thread-Ergebnisse, User-Ergebnisse und Modell-Ergebnisse.
# FastAPI speichert diese anschließend in getrennte MongoDB-Collections.

library(httr)
library(jsonlite)
library(dplyr)


COMMON_COMMENT_RESULT_FIELDS <- c(
  "comment_id", "thread_id", "source_file",
  "login", "text", "created_at", "parent_id",

  "irony", "attack_score", "toxicity_score",
  "swearword_count", "negative_word_count", "insult_count",
  "direct_address_count", "imperative_count",
  "accusation_marker_count", "mockery_marker_count",
  "is_attacking",

  "reply_depth", "parent_is_root", "num_children",
  "thread_position_abs", "thread_position_rel",
  "num_previous_comments",
  "prev_attack_rate", "prev_toxicity_score_mean",
  "prev_attack_count", "prev_toxicity_score_max",
  "prev_attack_score_max",
  "recent_attack_rate_3", "recent_attack_rate_5",
  "attack_streak_current",
  "target_recently_attacked", "reply_after_attack",
  "target_response_context_score"
)
#-----------------------------------------------------------------------------------------------------
# Baut Dokumente für professor_dataset/training: pro Kommentar, pro Thread,pro User und pro Modelllauf
#-----------------------------------------------------------------------------------------------------
build_analysis_result_documents <- function(full_data, results_row = NULL) {
  
  comment_results <- full_data %>%
    select(
      comment_id, thread_id, login, synthetic_role,
      attack_score, toxicity_score, is_attacking,
      irony, swearword_count, insult_count, negative_word_count,
      direct_address_count, imperative_count, accusation_marker_count, mockery_marker_count,
      reply_depth, parent_is_root, num_children,
      thread_position_abs, thread_position_rel, num_previous_comments,
      prev_attack_rate, prev_toxicity_score_mean, prev_attack_count,
      prev_toxicity_score_max, prev_attack_score_max,
      recent_attack_rate_3, recent_attack_rate_5, attack_streak_current,
      is_target_login_numeric, target_recently_attacked, reply_after_attack,
      target_response_context_score, date_timestamp
    ) %>%
    mutate(across(where(is.factor), as.character))

  thread_results <- full_data %>%
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
      mean_toxicity_score = mean(as.numeric(toxicity_score), na.rm = TRUE),
      max_toxicity_score = max(as.numeric(toxicity_score), na.rm = TRUE),
      mean_attack_score = mean(as.numeric(attack_score), na.rm = TRUE),
      max_attack_score = max(as.numeric(attack_score), na.rm = TRUE),
      mean_prev_attack_rate = mean(prev_attack_rate, na.rm = TRUE),
      max_prev_attack_rate = max(prev_attack_rate, na.rm = TRUE),
      mean_prev_toxicity_score_mean = mean(prev_toxicity_score_mean, na.rm = TRUE),
      max_prev_toxicity_score_mean = max(prev_toxicity_score_mean, na.rm = TRUE),
      max_recent_attack_rate_3 = max(recent_attack_rate_3, na.rm = TRUE),
      max_recent_attack_rate_5 = max(recent_attack_rate_5, na.rm = TRUE),
      max_attack_streak_current = max(attack_streak_current, na.rm = TRUE),
      .groups = "drop"
    )

  user_results <- full_data %>%
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
      .groups = "drop"
    )

  model_results <- if (!is.null(results_row)) {
    results_row %>% mutate(created_at = as.character(Sys.time()))
  } else {
    data.frame()
  }

  list(
    comment_results = comment_results,
    thread_results = thread_results,
    user_results = user_results,
    model_results = model_results
  )
}
#-----------------------------------------------------------------------------------------------------
# Baut Dokumente für professor_dataset/test: pro Kommentar, pro Thread,pro User und pro Modelllauf
#-----------------------------------------------------------------------------------------------------

build_professor_test_result_documents <- function(test_data, pred, test_truth, results_row = NULL) {
  probability_df <- as.data.frame(pred$prob)
  names(probability_df) <- paste0("prob_class_", names(probability_df))

  comment_results <- test_data %>%
    select(any_of(COMMON_COMMENT_RESULT_FIELDS)) %>%
        mutate(
            true_synthetic_role = as.character(test_truth),
            predicted_synthetic_role = as.character(pred$response),
            source_platform = "professor_dataset",
            analysis_saved_at = as.character(Sys.time())
            ) %>%
            bind_cols(probability_df) %>%
            mutate(across(where(is.factor), as.character))

  thread_results <- comment_results %>%
    group_by(thread_id) %>%
    summarise(
      test_comment_count = n(),
      accuracy = mean(true_synthetic_role == predicted_synthetic_role),

      mean_attack_score = mean(as.numeric(attack_score), na.rm = TRUE),
      max_attack_score = max(as.numeric(attack_score), na.rm = TRUE),

      mean_toxicity_score = mean(as.numeric(toxicity_score), na.rm = TRUE),
      max_toxicity_score = max(as.numeric(toxicity_score), na.rm = TRUE),

      predicted_attack_comments = sum(predicted_synthetic_role == "5", na.rm = TRUE),
      predicted_attack_share = mean(predicted_synthetic_role == "5", na.rm = TRUE),

      true_attack_comments = sum(true_synthetic_role == "5", na.rm = TRUE),
      true_attack_share = mean(true_synthetic_role == "5", na.rm = TRUE),

      mean_prev_attack_rate = mean(as.numeric(prev_attack_rate), na.rm = TRUE),
      max_recent_attack_rate_3 = max(as.numeric(recent_attack_rate_3), na.rm = TRUE),
      max_recent_attack_rate_5 = max(as.numeric(recent_attack_rate_5), na.rm = TRUE),
      max_attack_streak_current = max(as.numeric(attack_streak_current), na.rm = TRUE),

      analysis_saved_at = as.character(Sys.time()),
      .groups = "drop"
    )

  user_results <- test_data %>%
  mutate(
    true_synthetic_role = as.character(test_truth),
    predicted_synthetic_role = as.character(pred$response)
  ) %>%
  group_by(login) %>%
  summarise(
    test_comment_count = n(),
    test_thread_count = n_distinct(thread_id),
    accuracy = mean(true_synthetic_role == predicted_synthetic_role),

    login_count = first(login_count),
    login_percentage = first(login_percentage),
    frequency_group = first(frequency_group),

    mean_attack_score = mean(as.numeric(attack_score), na.rm = TRUE),
    max_attack_score = max(as.numeric(attack_score), na.rm = TRUE),

    mean_toxicity_score = mean(as.numeric(toxicity_score), na.rm = TRUE),
    max_toxicity_score = max(as.numeric(toxicity_score), na.rm = TRUE),

    mean_swearword_count = mean(as.numeric(swearword_count), na.rm = TRUE),
    mean_insult_count = mean(as.numeric(insult_count), na.rm = TRUE),
    mean_negative_word_count = mean(as.numeric(negative_word_count), na.rm = TRUE),

    predicted_attack_comments = sum(predicted_synthetic_role == "5", na.rm = TRUE),
    predicted_attack_share = mean(predicted_synthetic_role == "5", na.rm = TRUE),

    true_attack_comments = sum(true_synthetic_role == "5", na.rm = TRUE),
    true_attack_share = mean(true_synthetic_role == "5", na.rm = TRUE),

    source_platform = "professor_dataset",
    analysis_saved_at = as.character(Sys.time()),
    .groups = "drop"
  )

  model_results <- if (!is.null(results_row)) {
    results_row %>%
      mutate(
        result_type = "professor_test_prediction",
        analysis_saved_at = as.character(Sys.time())
      )
  } else {
    data.frame()
  }

  list(
    comment_results = comment_results,
    thread_results = thread_results,
    user_results = user_results,
    model_results = model_results
  )
}

#-------------------------------------------------------------------------------------------------------
# Speichert Test-Results aus der Analyse
#-------------------------------------------------------------------------------------------------------

save_professor_test_predictions_to_api <- function(comment_results, thread_results, user_results, model_results) {
  payload <- list(
    professor_test_comment_results = comment_results,
    professor_test_thread_results = thread_results,
    professor_test_user_results = user_results,
    professor_test_model_results = model_results
  )

  response <- httr::POST(
    url = ANALYSIS_SAVE_RESULTS_ENDPOINT,
    body = payload,
    encode = "json"
  )

  httr::content(response, as = "parsed")
}


#-------------------------------------------------------------------------------------------------------
# Speichert Trainings-/Testanalyse in die allgemeinen Analyse-Collections.
#-------------------------------------------------------------------------------------------------------

save_analysis_results_to_api <- function(comment_results, thread_results, user_results, model_results) {
  payload <- list(
    comment_results = comment_results,
    thread_results = thread_results,
    user_results = user_results,
    model_results = model_results
  )

  response <- httr::POST(
    url = ANALYSIS_SAVE_RESULTS_ENDPOINT,
    body = payload,
    encode = "json"
  )

  httr::content(response, as = "parsed")
}

# ----------------------------------------------------------------------------------
# Baut getrennte Bluesky Kommentar-, Thread- und User-Dokumente für MongoDB.
# ----------------------------------------------------------------------------------
build_bluesky_result_documents <- function(bluesky_data, pred, predicted_role) {
  probability_df <- as.data.frame(pred$prob)
  names(probability_df) <- paste0("prob_class_", names(probability_df))

  comment_results <- bluesky_data %>%
    select(any_of(COMMON_COMMENT_RESULT_FIELDS)) %>%
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
#---------------------------------------------------------------------------------------------------------
# Speichert Bluesky-Predictions getrennt von Trainingsdaten
#---------------------------------------------------------------------------------------------------------
save_bluesky_predictions_to_api <- function(comment_results, thread_results, user_results, model_results) {

  payload <- list(
    bluesky_prediction_comments_results = comment_results,
    bluesky_prediction_thread_results = thread_results,
    bluesky_prediction_user_results = user_results,
    bluesky_prediction_model_results = model_results
  )

  response <- httr::POST(
    url = ANALYSIS_SAVE_RESULTS_ENDPOINT,
    body = payload,
    encode = "json"
  )

  httr::content(response, as = "parsed")
}
