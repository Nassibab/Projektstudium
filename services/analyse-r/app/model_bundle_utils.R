# ------------------------------------------------------------
# Helpers to keep saved / loaded model bundles memory-efficient
# ------------------------------------------------------------

TFIDF_REFERENCE_COLUMNS <- c("subject", "text", "thread_title")

slim_tfidf_reference_data <- function(data) {
  cols <- intersect(TFIDF_REFERENCE_COLUMNS, names(data))
  if (length(cols) == 0) {
    stop("TF-IDF reference data must include at least one of: subject, text, thread_title")
  }

  data[, cols, drop = FALSE]
}

slim_factor_template_data <- function(data) {
  cols <- intersect(c("synthetic_role", STRUCTURE_FEATURES), names(data))
  data[, cols, drop = FALSE]
}

slim_model_bundle <- function(model_bundle) {
  model_bundle$train_data_for_tfidf <- slim_tfidf_reference_data(
    model_bundle$train_data_for_tfidf
  )
  model_bundle$train_model_template <- slim_factor_template_data(
    model_bundle$train_model_template
  )

  model_bundle
}
