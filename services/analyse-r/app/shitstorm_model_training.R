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

  prediction <- learner$predict(task, row_ids = splits$test)

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
