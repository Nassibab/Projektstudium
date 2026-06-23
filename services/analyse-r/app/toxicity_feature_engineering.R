# ------------------------------------------------------------
# Attack-/Toxicity-Spalten normalisieren
# ------------------------------------------------------------

add_toxicity_features <- function(data) {

  if (!"attack_score" %in% names(data)) {
    data$attack_score <- 1L
  }

  if (!"toxicity_score" %in% names(data)) {
    data$toxicity_score <- 1L
  }

  data$attack_score <- suppressWarnings(as.integer(data$attack_score))
  data$toxicity_score <- suppressWarnings(as.integer(data$toxicity_score))

  data$attack_score[is.na(data$attack_score)] <- 1L
  data$toxicity_score[is.na(data$toxicity_score)] <- 1L

  if (!"is_attacking" %in% names(data)) {
    data$is_attacking <- ifelse(data$attack_score >= 5, 1L, 0L)
  } else {
    data$is_attacking <- suppressWarnings(as.integer(as.character(data$is_attacking)))
    data$is_attacking[is.na(data$is_attacking)] <- ifelse(data$attack_score[is.na(data$is_attacking)] >= 5, 1L, 0L)
  }

  data$is_attacking <- as.factor(data$is_attacking)

  data
}
