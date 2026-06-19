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

  numeric_force_cols <- c(
    "is_attacking",
    "attack_score",
    "toxicity_score",
    "irony",
    "swearword_count",
    "negative_word_count",
    "insult_count",
    "direct_address_count",
    "imperative_count",
    "accusation_marker_count",
    "mockery_marker_count"
  )

  for (col in intersect(numeric_force_cols, names(data))) {
    data[[col]] <- suppressWarnings(
      as.numeric(as.character(data[[col]]))
    )
    data[[col]][is.na(data[[col]])] <- 0
  }

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

structure_to_numeric_matrix <- function(df) {
  mat <- vapply(names(df), function(col) {
    x <- df[[col]]
    if (is.factor(x)) {
      as.numeric(x)
    } else {
      as.numeric(x)
    }
  }, numeric(nrow(df)))

  colnames(mat) <- names(df)
  mat
}

combine_structure_and_tfidf <- function(structure_df, tfidf_sparse) {
  structure_mat <- structure_to_numeric_matrix(structure_df)
  structure_sparse <- Matrix::Matrix(structure_mat, sparse = TRUE)
  combined <- Matrix::cbind2(structure_sparse, tfidf_sparse)
  colnames(combined) <- c(colnames(structure_mat), colnames(tfidf_sparse))
  combined
}
