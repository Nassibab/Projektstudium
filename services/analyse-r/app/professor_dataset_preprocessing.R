library(dplyr)

prepare_training_data <- function(data) {
  professor_data <- data[data[["source_platform"]] == "professor_dataset", ]

  professor_data <- professor_data %>%
    mutate(
      scenario_type = as.character(scenario_type),
      scenario_type = case_when(
        scenario_type == "kein_shitstorm" ~ 1,
        scenario_type == "grenzfall_deeskalation" ~ 2,
        scenario_type == "polarisierung" ~ 3,
        scenario_type == "langsame_eskalation" ~ 4,
        scenario_type == "ereignisgetriebene_eskalation" ~ 5,
        scenario_type == "dogpiling_einzelperson" ~ 6,
        TRUE ~ NA_real_
      ),
      created_timestamp = as.numeric(as.POSIXct(created, tz = "Europe/Berlin"))
    )

  model_data <- professor_data[, c(
    "scenario_type",
    "comments_count",
    "created_timestamp"
  )]

  model_data$scenario_type <- factor(
    model_data$scenario_type,
    levels = c(1, 2, 3, 4, 5, 6)
  )

  model_data$comments_count <- as.integer(model_data$comments_count)

  na.omit(model_data)
}