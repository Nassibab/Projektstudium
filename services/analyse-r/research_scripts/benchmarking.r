# ------------------------------------------------------------
# Benchmarking mit ausgewählten Learnern
# ------------------------------------------------------------

learners_ranger <- list(
  lrn(
    "classif.ranger",
    predict_type = "prob",
    importance = "none",
    num.threads = ranger_num_threads
  )
)

learners_encoded <- list(
  lrn(
    "classif.glmnet",
    predict_type = "prob",
    s = 0.01,
    maxit = 200000
  ),

  lrn(
    "classif.xgboost",
    predict_type = "prob",
    nrounds = 100,
    max_depth = 4,
    eta = 0.1,
    nthread = ranger_num_threads
  ),
  lrn(
    "classif.naive_bayes",
    predict_type = "prob"
  )
)


rsmp_cv5 <- rsmp("cv", folds = 5)


# ------------------------------------------------------------
# Benchmark grid getrennt nach Datenversion
# ------------------------------------------------------------

setup_ranger <- benchmark_grid(
  tasks = train_data_obj,
  learners = learners_ranger,
  resamplings = rsmp_cv5
)

setup_encoded <- benchmark_grid(
  tasks = train_data_obj_encoded,
  learners = learners_encoded,
  resamplings = rsmp_cv5
)

setup <- rbind(setup_ranger, setup_encoded)

head(setup)


# ------------------------------------------------------------
# Benchmark ausführen
# ------------------------------------------------------------

bm <- benchmark(setup)


# ------------------------------------------------------------
# Scores und Aggregation
# ------------------------------------------------------------

benchmark_measures <- list(
  msr("classif.acc"),
  msr("classif.ce"),
  msr("classif.precision", average = "macro"),
  msr("classif.recall", average = "macro"),
  msr("classif.fbeta", beta = 1, average = "macro")
)

bm_scores <- bm$score(benchmark_measures)

bm_aggregate <- bm$aggregate(benchmark_measures)

print(bm_scores)
print(bm_aggregate)


# ------------------------------------------------------------
# Median / Minimum / Maximum pro Learner
# ------------------------------------------------------------

scores_ce <- bm$score(msr("classif.ce"))

median_scores <- scores_ce[
  ,
  .(median_ce = median(classif.ce)),
  by = learner_id
]

minimum_scores <- scores_ce[
  ,
  .(minimum_ce = min(classif.ce)),
  by = learner_id
]

maximum_scores <- scores_ce[
  ,
  .(maximum_ce = max(classif.ce)),
  by = learner_id
]

ce_summary <- merge(median_scores, minimum_scores, by = "learner_id")
ce_summary <- merge(ce_summary, maximum_scores, by = "learner_id")

print(ce_summary)


# ------------------------------------------------------------
# Accuracy Plot
# ------------------------------------------------------------

autoplot(bm, measure = msr("classif.acc"))