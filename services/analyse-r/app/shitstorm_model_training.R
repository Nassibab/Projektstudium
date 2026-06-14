# ------------------------------------------------------------
# Modelltraining für synthetic_role
# ------------------------------------------------------------

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

  train_model_data <- cbind(train_model_data, tfidf_result$train_tfidf)
  test_model_data <- cbind(test_model_data, tfidf_result$test_tfidf)

  train_model_data <- handle_missing_values(train_model_data)
  test_model_data <- handle_missing_values(test_model_data)
  test_model_data <- align_factor_levels(train_model_data, test_model_data)

  list(
    train_model_data = train_model_data,
    test_model_data = test_model_data,
    tfidf_result = tfidf_result
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

  set.seed(SEED_VALUE)
  train_ids <- sample(seq_len(nrow(full_data)), size = floor(TRAIN_RATIO * nrow(full_data)))

  train_data <- full_data[train_ids, ]
  test_data <- full_data[-train_ids, ]

  matrices <- prepare_model_matrices(train_data, test_data)
  train_model_data <- matrices$train_model_data
  test_model_data <- matrices$test_model_data
  tfidf_result <- matrices$tfidf_result

  test_truth <- test_model_data$synthetic_role
  test_ids <- if ("id" %in% names(test_data)) test_data$id else seq_len(nrow(test_data))

  task <- TaskClassif$new(
    id = "full_synthetic_role_model",
    backend = train_model_data,
    target = "synthetic_role"
  )

  learner <- lrn(
    "classif.ranger",
    predict_type = "prob",
    importance = "impurity",
    num.threads = RANGER_NUM_THREADS
  )

  start_train <- Sys.time()
  learner$train(task)
  training_time <- Sys.time() - start_train

  feature_cols <- setdiff(names(train_model_data), "synthetic_role")
  test_x <- test_model_data[, feature_cols, drop = FALSE]
  test_x <- align_factor_levels(train_model_data, test_x)

  start_predict <- Sys.time()
  pred <- learner$predict_newdata(test_x)
  prediction_time <- Sys.time() - start_predict
  prediction_time_per_row <- as.numeric(prediction_time, units = "secs") / nrow(test_x)

  accuracy <- mean(pred$response == test_truth)
  classification_error <- mean(pred$response != test_truth)

  confusion <- as.data.frame(table(truth = test_truth, predicted = pred$response))

  test_confusion <- table(Truth = test_truth, Prediction = pred$response)
  class_accuracy <- diag(test_confusion) / rowSums(test_confusion)

  feature_importance <- learner$importance()
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
    n_features_total = ncol(train_model_data) - 1,
    n_tfidf_features = sum(grepl("^tfidf_", names(train_model_data))),
    oob_brier = learner$model$prediction.error,
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
    tfidf_time_min = as.numeric(tfidf_result$tfidf_time, units = "mins"),
    model_training_time_min = as.numeric(training_time, units = "mins"),
    prediction_time_min = as.numeric(prediction_time, units = "mins"),
    prediction_time_per_row_sec = prediction_time_per_row
  )

  documents <- build_analysis_result_documents(full_data = full_data, results_row = results_row)

  save_status <- save_analysis_results_to_api(
    documents$comment_results,
    documents$thread_results,
    documents$user_results,
    documents$model_results
  )

  list(
    learner = learner,
    accuracy = accuracy,
    classification_error = classification_error,
    confusion = confusion,
    prediction_table = head(prediction_table, 50),
    feature_importance = head(feature_importance_df, 50),
    top_tfidf_features = head(tfidf_importance_df, 30),
    top_non_tfidf_features = head(non_tfidf_importance_df, 30),
    results_row = results_row,
    thread_feature_preview = head(train_model_data[, intersect(STRUCTURE_FEATURES, names(train_model_data)), drop = FALSE], 20),
    total_rows = nrow(full_data),
    train_rows = nrow(train_model_data),
    test_rows = nrow(test_model_data),
    n_features_total = ncol(train_model_data) - 1,
    n_tfidf_features = tfidf_result$n_tfidf_features,
    tfidf_time = as.numeric(tfidf_result$tfidf_time, units = "secs"),
    training_time = as.numeric(training_time, units = "secs"),
    prediction_time = as.numeric(prediction_time, units = "secs"),
    prediction_time_per_row_sec = prediction_time_per_row,
    total_time = as.numeric(total_time, units = "secs"),
    save_status = save_status
  )
}
