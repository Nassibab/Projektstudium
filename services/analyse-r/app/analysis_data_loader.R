#-----------------------------------
# Daten aus der FastAPI laden
#-----------------------------------

load_analysis_data <- function() {
  jsonlite::fromJSON(ANALYSIS_COMMENTS_ENDPOINT)
}

load_analysis_bluesky <- function(thread_id) {
  if (missing(thread_id) || is.null(thread_id) || trimws(as.character(thread_id)) == "") {
    stop("thread_id fehlt für Bluesky-Prediction.")
  }

  url <- paste0(
    API_URL,
    "/analysis/bluesky/prediction-data/",
    URLencode(as.character(thread_id), reserved = TRUE)
  )

  data <- jsonlite::fromJSON(url, flatten = TRUE)

  if (!is.data.frame(data)) {
    stop("Bluesky-Prediction erwartet eine flache Kommentar-Liste als DataFrame.")
  }

  if (!"source_platform" %in% names(data)) {
    data$source_platform <- "bluesky"
  }

  if (!"source_file" %in% names(data)) {
    data$source_file <- "bluesky"
  }

  data
}

load_analysis_data_for_thread <- function(thread_id, source_file) {
  url <- paste0(
    API_URL,
    "/analysis/comments?thread_id=", URLencode(thread_id, reserved = TRUE),
    "&source_file=", URLencode(source_file, reserved = TRUE)
  )

  jsonlite::fromJSON(url)
}