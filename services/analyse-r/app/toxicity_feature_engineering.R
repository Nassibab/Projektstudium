# ------------------------------------------------------------
# Attack-/Toxicity-Spalten normalisieren
# ------------------------------------------------------------
# Die vollständige Analyse erzeugt attack_score/toxicity_score nicht aus Text.
# Sie nutzt vorhandene Werte und setzt fehlende Werte auf 1. Diese Funktion
# übernimmt genau diese Logik und erzeugt daraus is_attacking.

use_llm_features_if_available <- function(data) {
  if ("llm_attack_score" %in% names(data)) {
    data$attack_score <- data$llm_attack_score
  }

  if ("llm_toxicity_score" %in% names(data)) {
    data$toxicity_score <- data$llm_toxicity_score
  }

  if ("llm_is_attacking" %in% names(data)) {
    data$is_attacking <- data$llm_is_attacking
  }

  if ("llm_irony" %in% names(data)) {
    data$irony <- data$llm_irony
  }

  if ("llm_swearword_count" %in% names(data)) {
    data$swearword_count <- data$llm_swearword_count
  }

  if ("llm_negative_word_count" %in% names(data)) {
    data$negative_word_count <- data$llm_negative_word_count
  }

  if ("llm_insult_count" %in% names(data)) {
    data$insult_count <- data$llm_insult_count
  }

  if ("llm_direct_address_count" %in% names(data)) {
    data$direct_address_count <- data$llm_direct_address_count
  }

  if ("llm_imperative_count" %in% names(data)) {
    data$imperative_count <- data$llm_imperative_count
  }

  if ("llm_accusation_marker_count" %in% names(data)) {
    data$accusation_marker_count <- data$llm_accusation_marker_count
  }

  if ("llm_mockery_marker_count" %in% names(data)) {
    data$mockery_marker_count <- data$llm_mockery_marker_count
  }

  data
}


add_toxicity_features <- function(data) {
  data <- use_llm_features_if_available(data)

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
