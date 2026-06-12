library(dplyr)

prepare_prediction_data <- function(data) {
  bluesky_data <- data[data[["source_platform"]] == "bluesky", ]

  bluesky_data <- bluesky_data %>%
    mutate(
      created_timestamp = as.numeric(as.POSIXct(created, tz = "Europe/Berlin"))
    )

  model_data <- bluesky_data[, c(
    "comments_count",
    "created_timestamp"
  )]

  model_data$comments_count <- as.integer(model_data$comments_count)

  valid_rows <- complete.cases(model_data)

  list(
    original = bluesky_data[valid_rows, ],
    model_data = model_data[valid_rows, ]
  )
}