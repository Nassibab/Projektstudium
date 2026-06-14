# ------------------------------------------------------------
# Attack-/Toxicity-Spalten normalisieren
# ------------------------------------------------------------
# Die vollständige Analyse erzeugt attack_score/toxicity_score nicht aus Text.
# Sie nutzt vorhandene Werte und setzt fehlende Werte auf 1. Diese Funktion
# übernimmt genau diese Logik und erzeugt daraus is_attacking.

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
  }

  data$is_attacking <- as.factor(data$is_attacking)

  data
}
