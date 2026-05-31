# Loading packages
library(mlr3)
library(mlr3learners)
library(mlr3pipelines)
library(haven)
library(ggplot2)
library(dplyr)
library(jsonlite)

# Description mlr3 learners for classification
# lrn("classif.rpart")
# lrn("classif.xgboost")
# lrn("classif.kknn")
# lrn("classif.cv_glmnet")
# lrn("classif.glmnet")
# lrn("classif.lda")
# lrn("classif.log_reg") - Can handle character values, but not missing values
# lrn("classif.multinom")
# lrn("classif.naive_bayes")
# lrn("classif.nnet")
# lrn("classif.qda")
# lrn("classif.ranger") - Can handle character values
# lrn("classif.svm")

# Computational time calculation
start.time <- Sys.time()


# Loading data
train_data <- read.csv("E:\\Hochschule München\\Master\\4.Semester\\Projektstudium\\Data sets\\synthetic_shitstorm_messages_attack_scaled.csv",sep=",")
train_data$thread_title <- NULL

test_data <- read.csv("E:\\Hochschule München\\Master\\4.Semester\\Projektstudium\\Data sets\\synthetic_shitstorm_messages_unlabeled.csv",sep=",")
test_data$thread_title <- NULL

# Encoding character variables

train_data <- train_data %>%
  mutate(
    scenario_type = as.character(scenario_type),
    scenario_type = case_when(
      scenario_type == "kein_shitstorm" ~ 1,
      scenario_type == "grenzfall_deeskalation" ~ 2,
      scenario_type == "polarisierung" ~ 3,
      scenario_type == "langsame_eskalation" ~ 4,
      scenario_type == "ereignisgetriebene_eskalation" ~ 5,
      scenario_type == "dogpiling_einzelperson" ~ 6,
      TRUE ~ NA_real_
    )
  )


train_data <- train_data %>%
  mutate(
    synthetic_role = as.character(synthetic_role),
    synthetic_role = case_when(
      synthetic_role == "meta" ~ 2,
      synthetic_role == "discussion" ~ 3,
      synthetic_role == "counter_speech" ~ 4,
      synthetic_role == "attack" ~ 5,
      synthetic_role == "target_response" ~ 6,
      TRUE ~ NA_real_
    )
  )

test_data <- test_data %>%
  mutate(
    synthetic_role = as.character(synthetic_role),
    synthetic_role = case_when(
      synthetic_role == "meta" ~ 2,
      synthetic_role == "discussion" ~ 3,
      synthetic_role == "counter_speech" ~ 4,
      synthetic_role == "attack" ~ 5,
      synthetic_role == "target_response" ~ 6,
      TRUE ~ NA_real_
    )
  )

test_clean = subset(
  test_data,
  !is.na(id) &
    !is.na(parent) &
    !is.na(synthetic) &
    !is.na(toxicity_level) &
    label_shitstorm %in% c("0", "1") &
    is_long_thread %in% c("0", "1")
)

test_clean = droplevels(test_clean)
test_data <- test_clean

# Column data types

factor_columns <- c(2,3,4,11,13)
train_data[, factor_columns] <- lapply(train_data[, factor_columns], factor)
test_data[, factor_columns] <- lapply(test_data[, factor_columns], factor)

integer_columns <- c(5,6,14)
train_data[, integer_columns] <- lapply(train_data[, integer_columns], as.integer)
test_data[, integer_columns] <- lapply(test_data[, integer_columns], as.integer)

date_columns <- c(10)

# Coverting date to POSIXct and valid timestamp
train_data[, date_columns] <- lapply(train_data[, date_columns],as.POSIXct, format = "%d.%m.%Y %H:%M",tz = "Europe/Berlin")
test_data[, date_columns] <- lapply(test_data[, date_columns],as.POSIXct, format = "%d.%m.%Y %H:%M",tz = "Europe/Berlin")

train_data$date_timestamp <- as.numeric(train_data[[10]])
train_data[[10]] <- NULL
test_data$date_timestamp <- as.numeric(test_data[[10]])
test_data[[10]] <- NULL

train_data$irony <- NULL
train_data$text <- NULL
train_data$thread_id <- NULL
train_data$login <- NULL
train_data$subject <- NULL
train_data$irony_binary_previous <- NULL
train_data$is_attacking_binary_previous <- NULL
train_data$synthetic <- NULL
train_data$toxicity_level <- NULL

test_data$irony <- NULL
test_data$text <- NULL
test_data$thread_id <- NULL
test_data$login <- NULL
test_data$subject <- NULL
test_data$synthetic <- NULL
test_data$toxicity_level <- NULL

str(train_data)
str(test_data)

# Creating R6 object train_data
train_data_obj = TaskClassif$new(id = "trainData", backend = train_data, target = "scenario_type")
train_data_obj

# (1) Ranger (including plots and result tables)
splits = partition(train_data_obj)
splits

lrn_ranger = lrn("classif.ranger")
lrn_ranger$train(train_data_obj, row_ids = splits$train)
lrn_ranger$model

lrn_ranger2 = lrn("classif.ranger", predict_type = "prob")
lrn_ranger2$train(train_data_obj, row_ids = splits$train)
lrn_ranger2$model
lrn_ranger2$train(train_data_obj)

prediction = lrn_ranger$predict(train_data_obj, row_ids = splits$test)
prd = as.data.table(prediction)
prd

prediction$score(msr("classif.acc"))     # Accuracy
prediction$score(msr("classif.ce"))      # Classification Error
prediction$confusion 


# Test 2 (Benchmarking)

learners2 = lrns(c("classif.rpart","classif.ranger"))
rsmp_cv5 = rsmp("cv", folds = 5)


# Test mit 7 Learnern

setup2 = benchmark_grid(train_data_obj, learners2, rsmp_cv5)
head(setup2)
bm2 = benchmark(setup2)
bm2$score()
bm2$aggregate()

bm2$aggregate(list(
  msr("classif.precision", average = "macro"),
  msr("classif.recall", average = "macro"),
  msr("classif.fbeta", beta = 1, average = "macro")  # F1
))

# Computational time calculation
end.time <- Sys.time()
time.taken <- end.time - start.time
time.taken

write_json(
  train_data,
  path = "E:/Hochschule München/Master/4.Semester/Projektstudium/Data sets/train_data.json",
  pretty = TRUE,
  na = "null",
  dataframe = "rows"
)

# Prediction
test_x = test_data[, setdiff(names(test_data), c("scenario_type"))]

pred_test = lrn_ranger$predict_newdata(test_x)

cluster_pred_rg = data.frame(
  ID = test_data$id,
  predicted_scenario_type = pred_test$response
)


pred_test2 = lrn_ranger2$predict_newdata(test_x)
cluster_pred_rg2 = data.frame(
  ID = test_data$id,
  predicted_scenario_type = pred_test2$response,
  as.data.frame(pred_test2$prob)
)

print(cluster_pred_rg2)

pred_test$response   # predicted class
pred_test$prob       # class probabilities
pred_test$truth      # true labels, usually NA for newdata
pred_test$row_ids    # row ids

as.data.table(pred_test2)

test_data_complete = data.frame(
  test_data,
  predicted_scenario_type = pred_test$response
)

test_data_complete = data.frame(
  test_data,
  predicted_scenario_type = pred_test2$response,
  as.data.frame(pred_test2$prob)
)