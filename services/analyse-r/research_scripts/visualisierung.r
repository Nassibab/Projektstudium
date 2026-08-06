# ------------------------------------------------------------
# Visualisierungen für Dokumentation und Modellinterpretation
# ------------------------------------------------------------
# Dieser Block wird bewusst am Ende ausgeführt, damit alle Objekte aus
# Training, Evaluation und Feature Importance bereits vorhanden sind.
# Die Plots werden als PNG-Dateien in einem Unterordner gespeichert.
# ------------------------------------------------------------

figures_dir <- file.path(dirname(results_file), paste0("figures_", model_name))

if (!dir.exists(figures_dir)) {
  dir.create(figures_dir, recursive = TRUE)
}


# ------------------------------------------------------------
# Rollenlabels für plots
# ------------------------------------------------------------

role_labels_plot <- c(
  "1" = "root",
  "2" = "meta",
  "3" = "discussion",
  "4" = "counter_speech",
  "5" = "attack",
  "6" = "target_response",
  "7" = "deescalation"
)

add_role_label_plot <- function(x) {
  x_chr <- as.character(x)
  ifelse(x_chr %in% names(role_labels_plot), role_labels_plot[x_chr], x_chr)
}


# ------------------------------------------------------------
# Feature Labels bleiben bewusst auf Englisch
# ------------------------------------------------------------

add_feature_label_plot <- function(x) {
  as.character(x)
}


# ------------------------------------------------------------
# Einheitliches helles Theme für alle Plots
# ------------------------------------------------------------

theme_white_clean <- function() {
  theme_minimal() +
    theme(
      plot.background = element_rect(fill = "white", color = NA),
      panel.background = element_rect(fill = "white", color = NA),
      legend.background = element_rect(fill = "white", color = NA),
      legend.key = element_rect(fill = "white", color = NA),
      strip.background = element_rect(fill = "white", color = "grey80"),
      panel.grid.minor = element_blank(),
      plot.title = element_text(face = "bold"),
      plot.subtitle = element_text(color = "grey30")
    )
}


# ------------------------------------------------------------
# Datenbasis für Visualisierungen 
# ------------------------------------------------------------

data_vis <- data %>%
  mutate(
    synthetic_role_label = add_role_label_plot(synthetic_role),
    synthetic_role_label = factor(
      synthetic_role_label,
      levels = unname(role_labels_plot)
    )
  )


# ------------------------------------------------------------
# 1) Klassenverteilung
# ------------------------------------------------------------

class_distribution_plot <- data_vis %>%
  count(synthetic_role_label, name = "n") %>%
  mutate(
    percentage = n / sum(n) * 100
  ) %>%
  ggplot(
    aes(
      x = synthetic_role_label,
      y = n
    )
  ) +
  geom_col() +
  geom_text(
    aes(label = paste0(n, "\n", round(percentage, 1), "%")),
    vjust = -0.2,
    size = 3
  ) +
  labs(
    title = "Verteilung der Kommentarrollen im Datensatz",
    x = "Kommentarrolle",
    y = "Anzahl der Kommentare"
  ) +
  theme_white_clean() +
  theme(
    axis.text.x = element_text(angle = 35, hjust = 1)
  )

ggsave(
  filename = file.path(figures_dir, "01_klassenverteilung.png"),
  plot = class_distribution_plot,
  width = 10,
  height = 6,
  dpi = 300,
  bg = "white"
)