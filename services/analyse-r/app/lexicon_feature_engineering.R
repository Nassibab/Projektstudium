# ------------------------------------------------------------
# Inhalts-/Lexikonfeatures normalisieren
# ------------------------------------------------------------
# Die vollständige Analyse berechnet diese Spalten nicht aus Text, sondern erwartet
# sie bereits im Datensatz. Diese Funktion stellt sicher, dass alle benötigten
# Inhaltsvariablen existieren und numerisch sind. Fehlende Spalten werden wie im
# Original mit 0 befüllt.

add_lexicon_features <- function(data) {
  
    lexicon_cols <- c(
    "irony",
    "swearword_count",
    "negative_word_count",
    "insult_count",
    "direct_address_count",
    "imperative_count",
    "accusation_marker_count",
    "mockery_marker_count"
  )

  for (col in lexicon_cols) {
    if (!col %in% names(data)) {
      data[[col]] <- 0L
    }

    data[[col]] <- suppressWarnings(as.integer(data[[col]]))
    data[[col]][is.na(data[[col]])] <- 0L
  }

  data
}