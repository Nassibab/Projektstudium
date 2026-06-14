# ------------------------------------------------------------
# Professor-Datensatz vorbereiten
# ------------------------------------------------------------
# Diese Datei filtert den Trainingsdatensatz, kodiert synthetic_role und ruft
# alle Feature-Engineering-Schritte in derselben Reihenfolge wie die vollständige
# Analyse auf.

map_synthetic_role <- function(data) {
  # Wandelt Rollenlabels in die numerischen Klassen 1-7 um.
  data %>%
    mutate(
      synthetic_role_original = synthetic_role,
      synthetic_role = as.character(synthetic_role),
      synthetic_role = case_when(
        synthetic_role == "root" ~ 1,
        synthetic_role == "meta" ~ 2,
        synthetic_role == "discussion" ~ 3,
        synthetic_role == "counter_speech" ~ 4,
        synthetic_role == "attack" ~ 5,
        synthetic_role == "target_response" ~ 6,
        synthetic_role == "deescalation" ~ 7,
        TRUE ~ NA_real_
      ),
      synthetic_role = factor(synthetic_role, levels = c(1, 2, 3, 4, 5, 6, 7))
    ) %>%
    filter(!is.na(synthetic_role))
}

add_timestamp_columns <- function(data) {
  # Erzeugt created_timestamp/date_timestamp, damit Thread-Sortierung und Modell
  # dieselbe Zeitbasis verwenden.
  data <- data %>%
    mutate(
      created_timestamp = suppressWarnings(as.numeric(as.POSIXct(created, tz = "Europe/Berlin")))
    )

  if (!"date_timestamp" %in% names(data)) {
    data$date_timestamp <- data$created_timestamp
  }

  if (all(is.na(data$date_timestamp)) && "id" %in% names(data)) {
    data$date_timestamp <- suppressWarnings(as.numeric(data$id))
  }

  data
}


#---------------------------------------------------------------------
#* Train full synthetic role model with structure features and TF-IDF
#---------------------------------------------------------------------

prepare_full_training_data <- function(data) {
  professor_data <- data[data[["source_platform"]] == "professor_dataset", ]

  professor_data <- professor_data %>%
    filter(
      !is.na(synthetic_role),
      trimws(as.character(synthetic_role)) != ""
    ) %>%
    mutate(
      synthetic_role = as.character(synthetic_role),
      synthetic_role = case_when(
        synthetic_role == "root" ~ 1,
        synthetic_role == "meta" ~ 2,
        synthetic_role == "discussion" ~ 3,
        synthetic_role == "counter_speech" ~ 4,
        synthetic_role == "attack" ~ 5,
        synthetic_role == "target_response" ~ 6,
        synthetic_role == "deescalation" ~ 7,
        TRUE ~ NA_real_
      ),
      created_timestamp = as.numeric(as.POSIXct(created, tz = "Europe/Berlin"))
    ) %>%
    filter(!is.na(synthetic_role))

  professor_data$synthetic_role <- factor(
    professor_data$synthetic_role,
    levels = c(1, 2, 3, 4, 5, 6, 7)
  )

  professor_data$comments_count <- as.integer(professor_data$comments_count)
  professor_data$created_timestamp <- as.numeric(professor_data$created_timestamp)

 professor_data <- add_thread_features(professor_data)
 professor_data <- add_user_features(professor_data)
 professor_data <- add_lexicon_features(professor_data)
 professor_data <- add_toxicity_features(professor_data)
 professor_data <- add_context_features(professor_data)
 professor_data <- handle_missing_values(professor_data)

  professor_data
}