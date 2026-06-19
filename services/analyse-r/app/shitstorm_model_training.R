library(mlr3)
library(mlr3learners)
library(ranger)

#-----------------------------------------------------------------------------------
# Wählt nur die finalen Modellfeatures aus, erzeugt TF-IDF und entfernt dadurch
# indirekt alle nicht benötigten Rohspalten wie text, thread_id, login, parent usw.
#-----------------------------------------------------------------------------------
prepare_model_matrices <- function(train_data, test_data) {
  
  missing_structure_features <- setdiff(STRUCTURE_FEATURES, names(train_data))

  if (length(missing_structure_features) > 0) {
    stop(paste("Folgende Strukturfeatures fehlen:", paste(missing_structure_features, collapse = ", ")))
  }

  tfidf_result <- create_tfidf_features(train_data, test_data)

  train_model_data <- train_data[, c("synthetic_role", STRUCTURE_FEATURES), drop = FALSE]
  test_model_data <- test_data[, c("synthetic_role", STRUCTURE_FEATURES), drop = FALSE]

  train_model_data <- handle_missing_values(train_model_data)
  test_model_data <- handle_missing_values(test_model_data)
  test_model_data <- align_factor_levels(train_model_data, test_model_data)

  train_structure <- train_model_data[, STRUCTURE_FEATURES, drop = FALSE]
  test_structure <- test_model_data[, STRUCTURE_FEATURES, drop = FALSE]

  train_x <- combine_structure_and_tfidf(train_structure, tfidf_result$train_tfidf)
  test_x <- combine_structure_and_tfidf(test_structure, tfidf_result$test_tfidf)

  list(
    train_model_data = train_model_data,
    test_model_data = test_model_data,
    train_x = train_x,
    test_x = test_x,
    tfidf_result = tfidf_result,
    feature_cols = colnames(train_x)
  )
}


#-------------------------------------------------------------------------------
# Trainiert das vollständige Modell
# 80/20 Split, Strukturfeatures, TF-IDF, Ranger, Accuracy, Feature Importance,
# Results Row und Speichern der Analyseergebnisse in MongoDB über FastAPI.
#-------------------------------------------------------------------------------


train_full_synthetic_role_model <- function(data) {

  start_total <- Sys.time()

  full_data <- prepare_full_training_data(data)
  rm(data)
  gc(full = TRUE)

  set.seed(SEED_VALUE)
  train_ids <- sample(seq_len(nrow(full_data)), size = floor(TRAIN_RATIO * nrow(full_data)))

  train_data <- full_data[train_ids, ]
  test_data <- full_data[-train_ids, ]
  total_rows <- nrow(full_data)
  rm(full_data)
  gc(full = TRUE)

  matrices <- prepare_model_matrices(train_data, test_data)
  train_model_data <- matrices$train_model_data
  test_model_data <- matrices$test_model_data
  train_x <- matrices$train_x
  test_x <- matrices$test_x
  feature_cols <- matrices$feature_cols
  tfidf_result <- matrices$tfidf_result
  tfidf_time_secs <- as.numeric(tfidf_result$tfidf_time, units = "secs")
  n_tfidf_features <- tfidf_result$n_tfidf_features
  rm(matrices, tfidf_result)
  gc(full = TRUE)

  test_truth <- test_model_data$synthetic_role
  test_ids <- if ("id" %in% names(test_data)) test_data$id else seq_len(nrow(test_data))

  start_train <- Sys.time()
  rf_model <- ranger::ranger(
    x = train_x,
    y = train_model_data$synthetic_role,
    probability = TRUE,
    importance = "impurity",
    num.threads = RANGER_NUM_THREADS
  )
  training_time <- Sys.time() - start_train

  start_predict <- Sys.time()
  pred_prob <- predict(rf_model, data = test_x)$predictions
  pred_response <- predict(rf_model, data = test_x, type = "response")$predictions

  if (is.matrix(pred_response)) {
    pred_response <- colnames(pred_prob)[max.col(pred_response, ties.method = "first")]
  }

  pred_response <- factor(as.character(pred_response), levels = levels(test_truth))
  pred <- list(
    response = pred_response,
    prob = as.data.frame(pred_prob)
  )
  prediction_time <- Sys.time() - start_predict
  prediction_time_per_row <- as.numeric(prediction_time, units = "secs") / nrow(test_x)

  accuracy <- mean(pred$response == test_truth)
  classification_error <- mean(pred$response != test_truth)

  confusion <- as.data.frame(table(truth = test_truth, predicted = pred$response))

  test_confusion <- table(Truth = test_truth, Prediction = pred$response)
  class_accuracy <- diag(test_confusion) / rowSums(test_confusion)

  feature_importance <- rf_model$variable.importance
  feature_importance_sorted <- sort(feature_importance, decreasing = TRUE)
  feature_importance_df <- data.frame(
    feature = names(feature_importance_sorted),
    importance = as.numeric(feature_importance_sorted),
    row.names = NULL
  )

  tfidf_importance_df <- feature_importance_df %>% filter(grepl("^tfidf_", feature))
  non_tfidf_importance_df <- feature_importance_df %>% filter(!grepl("^tfidf_", feature))

  prediction_table <- data.frame(
    ID = test_ids,
    true_synthetic_role = test_truth,
    predicted_synthetic_role = pred$response,
    as.data.frame(pred$prob)
  )

  probability_names <- paste0("prob_class_", names(as.data.frame(pred$prob)))
  colnames(prediction_table)[4:ncol(prediction_table)] <- probability_names

  total_time <- Sys.time() - start_total

  results_row <- data.frame(
    model = MODEL_NAME,
    seed = SEED_VALUE,
    ngram_min = NGRAM_MIN,
    ngram_max = NGRAM_MAX,
    tfidf_top_n = TFIDF_TOP_N,
    tfidf_min_termfreq = TFIDF_MIN_TERMFREQ,
    class_weights_used = FALSE,
    lookback_features_used = FALSE,
    feature_importance_used = TRUE,
    ranger_num_threads = RANGER_NUM_THREADS,
    n_features_total = length(feature_cols),
    n_tfidf_features = n_tfidf_features,
    oob_brier = rf_model$prediction.error,
    test_accuracy = accuracy,
    test_classification_error = classification_error,
    class_1_root = as.numeric(class_accuracy["1"]),
    class_2_meta = as.numeric(class_accuracy["2"]),
    class_3_discussion = as.numeric(class_accuracy["3"]),
    class_4_counter_speech = as.numeric(class_accuracy["4"]),
    class_5_attack = as.numeric(class_accuracy["5"]),
    class_6_target_response = as.numeric(class_accuracy["6"]),
    class_7_deescalation = as.numeric(class_accuracy["7"]),
    total_time_min = as.numeric(total_time, units = "mins"),
    tfidf_time_min = tfidf_time_secs / 60,
    model_training_time_min = as.numeric(training_time, units = "mins"),
    prediction_time_min = as.numeric(prediction_time, units = "mins"),
    prediction_time_per_row_sec = prediction_time_per_row
  )

prob_df <- as.data.frame(pred$prob)
names(prob_df) <- paste0("prob_class_", names(prob_df))

test_labeled_output <- test_data %>%
  mutate(
    true_synthetic_role = as.character(test_truth),
    predicted_synthetic_role = as.character(pred$response),
    analysis_saved_at = as.character(Sys.time())
  ) %>%
  bind_cols(prob_df) %>%
  mutate(across(where(is.factor), as.character))

documents <- build_professor_test_result_documents(
  test_data = test_data,
  pred = pred,
  test_truth = test_truth,
  results_row = results_row
)

save_status <- save_professor_test_predictions_to_api(
  comment_results = documents$comment_results,
  thread_results = documents$thread_results,
  user_results = documents$user_results,
  model_results = documents$model_results
)

# ------------------------------------------------------------
# Modell speichern, damit es später nicht neu trainiert wird
# ------------------------------------------------------------
if (!dir.exists(MODEL_DIR)) {
  dir.create(MODEL_DIR, recursive = TRUE)
}

model_bundle <- slim_model_bundle(list(
  learner = rf_model,
  train_data_for_tfidf = train_data,
  train_model_template = train_model_data,
  feature_cols = feature_cols,
  created_at = as.character(Sys.time()),
  model_name = MODEL_NAME,
  accuracy = accuracy
))

saveRDS(model_bundle, MODEL_PATH)


  list(
    learner = rf_model,
    accuracy = accuracy,
    classification_error = classification_error,
    confusion = confusion,
    prediction_table = head(prediction_table, 50),
    feature_importance = head(feature_importance_df, 50),
    top_tfidf_features = head(tfidf_importance_df, 30),
    top_non_tfidf_features = head(non_tfidf_importance_df, 30),
    results_row = results_row,
    thread_feature_preview = head(train_model_data[, intersect(STRUCTURE_FEATURES, names(train_model_data)), drop = FALSE], 20),
    total_rows = total_rows,
    train_rows = nrow(train_model_data),
    test_rows = nrow(test_model_data),
    n_features_total = length(feature_cols),
    n_tfidf_features = n_tfidf_features,
    tfidf_time = tfidf_time_secs,
    training_time = as.numeric(training_time, units = "secs"),
    prediction_time = as.numeric(prediction_time, units = "secs"),
    prediction_time_per_row_sec = prediction_time_per_row,
    total_time = as.numeric(total_time, units = "secs"),
    save_status = save_status
  )
}
