library(jsonlite)

load_analysis_data <- function() {
  data <- jsonlite::fromJSON(
    ANALYSIS_COMMENTS_ENDPOINT,
    flatten = TRUE
  )

  as.data.frame(data)
}