# ------------------------------------------------------------
# Datentypen und Missing Values bereinigen
# ------------------------------------------------------------
# Diese Hilfsfunktionen bilden die Datentyp- und NA-Logik aus der vollständigen
# Analyse nach. Dadurch bekommen Training und Bluesky-Prediction konsistente Features.

coerce_analysis_column_types <- function(data) {
  factor_columns_data <- intersect(FACTOR_COLUMNS, names(data))
  integer_columns_data <- intersect(INTEGER_COLUMNS, names(data))
  float_columns_data <- intersect(FLOAT_COLUMNS, names(data))

  data[, factor_columns_data] <- lapply(data[, factor_columns_data, drop = FALSE], factor)
  data[, integer_columns_data] <- lapply(data[, integer_columns_data, drop = FALSE], function(x) suppressWarnings(as.integer(x)))
  data[, float_columns_data] <- lapply(data[, float_columns_data, drop = FALSE], function(x) suppressWarnings(as.numeric(x)))

  data
}

handle_missing_values <- function(data) {
  numeric_cols <- names(data)[sapply(data, is.numeric) | sapply(data, is.integer)]

  for (col in numeric_cols) {
    data[[col]][is.na(data[[col]])] <- 0
  }

  factor_cols <- names(data)[sapply(data, is.factor)]

  for (col in factor_cols) {
    data[[col]] <- as.character(data[[col]])
    data[[col]][is.na(data[[col]]) | trimws(data[[col]]) == ""] <- "missing"
    data[[col]] <- factor(data[[col]])
  }

  data
}

align_factor_levels <- function(train_data, new_data, target = "synthetic_role") {
  factor_feature_cols <- names(train_data)[sapply(train_data, is.factor)]
  factor_feature_cols <- setdiff(factor_feature_cols, target)

  for (col in factor_feature_cols) {
    if (col %in% names(new_data)) {
      new_data[[col]] <- factor(as.character(new_data[[col]]), levels = levels(train_data[[col]]))
    }
  }

  new_data
}
