API_URL <- "http://api:8000"
ANALYSIS_COMMENTS_ENDPOINT <- paste0(API_URL, "/analysis/comments")

RANDOM_SEED <- 123
TRAIN_RATIO <- 0.8

SCENARIO_LABELS <- c(
  "1" = "kein_shitstorm",
  "2" = "grenzfall_deeskalation",
  "3" = "polarisierung",
  "4" = "langsame_eskalation",
  "5" = "ereignisgetriebene_eskalation",
  "6" = "dogpiling_einzelperson"
)