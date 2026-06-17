# ------------------------------------------------------------
# User-Frequenzfeatures
# ------------------------------------------------------------
# Diese Funktion berechnet, wie aktiv ein User im Datensatz ist.
# Die Variablen entsprechen dem Frequency-&-User-Block der vollständigen Analyse.

add_user_features <- function(data) {
  if (!"login" %in% names(data)) {
    data$login <- "unknown_user"
  }

  data$login[is.na(data$login) | trimws(as.character(data$login)) == ""] <- "unknown_user"

# ------------------------------------------------------------
# Frequency & User variables
# ------------------------------------------------------------
  user_counts <- data %>%
    count(login, name = "login_count") %>%
    mutate(
      login_percentage = login_count / nrow(data) * 100,
      frequency_group = dplyr::ntile(login_count, 4)
    )

  data %>%
    left_join(user_counts, by = "login")
}
