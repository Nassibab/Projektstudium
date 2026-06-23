#-----------------------------------
# Daten aus der FastAPI laden
#-----------------------------------

load_analysis_data <- function() {
  jsonlite::fromJSON(ANALYSIS_COMMENTS_ENDPOINT)
}

load_analysis_bluesky <- function(thread_id = NULL) {
  url <- ANALYSIS_BLUESKY_ENDPOINT

  if (!is.null(thread_id) && nzchar(thread_id)) {
    url <- paste0(
      ANALYSIS_BLUESKY_ENDPOINT,
      "?thread_id=", URLencode(thread_id, reserved = TRUE)
    )
  }

  jsonlite::fromJSON(url)
}

load_analysis_data_for_thread <- function(thread_id, source_file) {
  url <- paste0(
    API_URL,
    "/analysis/comments?thread_id=", URLencode(thread_id, reserved = TRUE),
    "&source_file=", URLencode(source_file, reserved = TRUE)
  )

  jsonlite::fromJSON(url)
}