library(mlr3)
library(mlr3learners)
library(ranger)

train_rpart_model <- function() {
  data <- load_analysis_data()
  model_data <- prepare_training_data(data)

  task <- TaskClassif$new(
    id = "shitstorm_model",
    backend = model_data,
    target = "scenario_type"
  )

  set.seed(RANDOM_SEED)
  splits <- partition(task, ratio = TRAIN_RATIO)

  learner <- lrn("classif.rpart")
  learner$train(task, row_ids = splits$train)

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
    status = "success",
    model = "classif.rpart",
    total_rows = nrow(model_data),
    train_rows = length(splits$train),
    test_rows = length(splits$test),
    accuracy = prediction$score(msr("classif.acc")),
    confusion = as.data.frame(prediction$confusion)
  )
}

train_ranger_model <- function() {
  data <- load_analysis_data()
  model_data <- prepare_training_data(data)

  task <- TaskClassif$new(
    id = "shitstorm_ranger_model",
    backend = model_data,
    target = "scenario_type"
  )

  set.seed(RANDOM_SEED)
  splits <- partition(task, ratio = TRAIN_RATIO)

  learner <- lrn("classif.ranger", predict_type = "prob")
  learner$train(task, row_ids = splits$train)

  prediction <- learner$predict(task, row_ids = splits$test)

  prediction_table <- data.frame(
    truth = prediction$truth,
    predicted = prediction$response
  )

  prediction_table$truth_label <- dplyr::recode(
    as.character(prediction_table$truth),
    !!!SCENARIO_LABELS
  )

  prediction_table$predicted_label <- dplyr::recode(
    as.character(prediction_table$predicted),
    !!!SCENARIO_LABELS
  )

  prediction_table <- head(prediction_table, 20)

  list(
    status = "success",
    model = "classif.ranger",
    total_rows = nrow(model_data),
    train_rows = length(splits$train),
    test_rows = length(splits$test),
    accuracy = prediction$score(msr("classif.acc")),
    classification_error = prediction$score(msr("classif.ce")),
    confusion = as.data.frame(prediction$confusion),
    prediction_table = prediction_table
  )
}
