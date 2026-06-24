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

  # ------------------------------------------------------------
  # NEU: Recall-orientierte Prediction-Anpassung
  # ------------------------------------------------------------
  prob_df_raw <- as.data.frame(pred$prob)
  pred_adjusted <- as.character(pred$response)

  if ("5" %in% names(prob_df_raw)) {
    pred_adjusted[prob_df_raw[["5"]] >= 0.35] <- "5"
  }
  if ("6" %in% names(prob_df_raw)) {
    pred_adjusted[prob_df_raw[["6"]] >= 0.25] <- "6"
  }
  if ("7" %in% names(prob_df_raw)) {
    pred_adjusted[prob_df_raw[["7"]] >= 0.25] <- "7"
  }

  # Wir überschreiben die originalen Predictions mit den angepassten.
  # So berechnen alle folgenden Schritte (Accuracy, Confusion, FastAPI-Upload)
  # automatisch die neuen, recall-optimierten Werte!
  pred$response <- factor(pred_adjusted, levels = levels(test_truth))
  # ------------------------------------------------------------

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

  prob_df <- as.data.frame(pred$prob)
  names(prob_df) <- paste0("prob_class_", names(prob_df))
    
  test_identifiers <- data.frame(ID = test_ids)
  total_time <- Sys.time() - start_total # Wichtig für den return() ganz unten!

  evaluation_results <- evaluate_test_predictions(
    test_data_ranger = test_data,
    test_identifiers = test_identifiers,
    prob_df = prob_df,
    start.time_total = start_total,
    model_name = MODEL_NAME,
    seed_value = SEED_VALUE,
    test_accuracy = accuracy,
    test_classification_error = classification_error,
    pred_response = pred$response
  )

  results_row <- evaluation_results$model_comparison_metrics
  prediction_table <- evaluation_results$full_prediction_results

  # ------------------------------------------------------------
  
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

  model_bundle <- list(
    learner = learner,
    train_data_for_tfidf = train_data,
    train_model_template = train_model_data,
    feature_cols = feature_cols,
    created_at = as.character(Sys.time()),
    model_name = MODEL_NAME,
    accuracy = accuracy
  )

  saveRDS(model_bundle, MODEL_PATH)

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