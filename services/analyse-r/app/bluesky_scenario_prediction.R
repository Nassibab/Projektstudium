library(mlr3)
library(mlr3learners)
library(ranger)

predict_bluesky_scenarios <- function() {
  data <- load_analysis_data()

  train_data <- prepare_training_data(data)
  prediction_data <- prepare_prediction_data(data)

  task <- TaskClassif$new(
    id = "shitstorm_prediction_model",
    backend = train_data,
    target = "scenario_type"
  )

  learner <- lrn("classif.ranger", predict_type = "prob")
  learner$train(task)

  pred <- learner$predict_newdata(prediction_data$model_data)

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

  head(result, 50)
}