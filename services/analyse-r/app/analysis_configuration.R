# ------------------------------------------------------------
# Zentrale Konfiguration für die R-Analyse
# ------------------------------------------------------------
# Diese Datei bündelt alle Konstanten, damit Training, Prediction,
# Feature Engineering und Speicherung dieselben Parameter verwenden.



MODERATION_URL <- "http://moderation:8000"

MODERATION_BLUESKY_PREDICTION_ENDPOINT <- paste0(
  MODERATION_URL,
  "/moderation/warning"
)

API_URL <- "http://api:8000"

ANALYSIS_COMMENTS_ENDPOINT <- paste0(API_URL, "/analysis/training/prof-comments/all")
ANALYSIS_BLUESKY_ENDPOINT <- paste0(API_URL, "/analysis/bluesky/prediction-data")
ANALYSIS_SAVE_RESULTS_ENDPOINT <- paste0(API_URL, "/analysis/save-results")

MODEL_NAME <- "ranger_structure_tfidf_unigram_bigram_best_importance"
SEED_VALUE <- 42
TRAIN_RATIO <- 0.8

# Beste bisherige TF-IDF-Konfiguration (statt 1500 und 20)
TFIDF_TOP_N <- 300
TFIDF_MIN_TERMFREQ <- 50
NGRAM_MIN <- 1
NGRAM_MAX <- 2


# Bestes Hauptmodell:
RANGER_NUM_THREADS <- max(1, parallel::detectCores() - 1)

ROLE_LABELS <- c(
  "1" = "root",
  "2" = "meta",
  "3" = "discussion",
  "4" = "counter_speech",
  "5" = "attack",
  "6" = "target_response",
  "7" = "deescalation"
)

# Diese Features entsprechen der Struktur-/Kontextlogik aus der vollständigen Analyse.
# Textspalten wie text, thread_id oder login werden nicht direkt ins Modell gegeben,
# weil sie entweder in TF-IDF verarbeitet oder nur für Zuordnung/Speicherung benötigt werden.
STRUCTURE_FEATURES <- c(
  "comments_count",
  "created_timestamp",
  "date_timestamp",

  "login_count",
  "login_percentage",
  "frequency_group",

  "attack_score",
  "toxicity_score",
  "is_attacking",

  "irony",
  "swearword_count",
  "negative_word_count",
  "insult_count",
  "direct_address_count",
  "imperative_count",
  "accusation_marker_count",
  "mockery_marker_count",

  "thread_position_abs",
  "thread_size",
  "thread_position_rel",
  "num_previous_comments",
  "is_thread_start",
  "is_reply",
  "previous_comment_exists",
  "time_since_thread_start",
  "time_since_previous_comment",

  "user_thread_comment_count_before",
  "user_thread_comment_count_total",
  "user_previous_thread_share",

  "reply_depth",
  "num_children",
  "parent_is_root",
  "is_target_login_numeric",

  "thread_user_count",
  "thread_comment_count",
  "thread_mean_comments_per_user",
  "thread_max_comments_by_one_user",
  "thread_single_comment_user_count",
  "thread_max_user_share",
  "thread_single_comment_user_share",

  "log_time_since_thread_start",
  "log_time_since_previous_comment",

  "previous_comment_attack",
  "prev_attack_count",
  "prev_attack_rate",
  "prev_toxicity_score_mean",
  "prev_toxicity_score_max",
  "prev_attack_score_max",
  "recent_attack_rate_3",
  "recent_attack_rate_5",
  "attack_streak_current",
  "target_recently_attacked",
  "reply_after_attack",
  "target_response_context_score"
)

# Spalten, die nach TF-IDF nicht als rohe Features ins Modell sollen.
# Wir wählen im API-Code zwar aktiv STRUCTURE_FEATURES aus, diese Liste dokumentiert
# die gleiche Bereinigungslogik wie in der vollständigen Analyse-Datei.
DROP_COLUMNS_AFTER_TFIDF <- c(
  "text", "subject", "name", "comment_id",
  "thread_id", "login", "parent_id", "target_login",
  "synthetic", "label_shitstorm", "toxicity_level", "scenario_type", "comment_scenario_type",
  "thread_title", "created_at", "sort_timestamp", "irony_binary_previous",
  "is_attacking_binary_previous", "synthetic_role_original",
  "has_counter_speech_marker", "counter_speech_marker_count", "boundary_marker_count",
  "thread_is_long_numeric", "has_tone_criticism", "tone_criticism_count",
  "has_norm_reminder", "norm_reminder_count", "has_solidarity_marker",
  "solidarity_marker_count", "has_deescalation_marker", "deescalation_marker_count",
  "has_meta_discussion_marker", "meta_discussion_marker_count", "has_attack_marker",
  "attack_marker_count", "has_argument_marker", "argument_marker_count",
  "has_target_response_marker", "first_person_defense_count", "justification_marker_count",
  "emotional_response_marker_count", "role_attack_score_marker",
  "role_counter_speech_score_marker", "role_deescalation_score_marker",
  "role_meta_score_marker", "role_discussion_score_marker"
)

FACTOR_COLUMNS <- c("synthetic_role", "is_attacking", "is_long_thread")

INTEGER_COLUMNS <- c(
  "irony", "swearword_count", "negative_word_count",
  "insult_count", "attack_score", "toxicity_score", "direct_address_count",
  "imperative_count", "accusation_marker_count", "mockery_marker_count",
  "login_count", "frequency_group", "thread_position_abs", "thread_size",
  "num_previous_comments", "is_thread_start", "is_reply", "previous_comment_exists",
  "user_thread_comment_count_total", "user_thread_comment_count_before",
  "reply_depth", "num_children", "parent_is_root", "is_target_login_numeric",
  "thread_user_count", "thread_comment_count", "thread_max_comments_by_one_user",
  "thread_single_comment_user_count", "previous_comment_attack", "prev_attack_count",
  "prev_toxicity_score_max", "prev_attack_score_max", "recent_attack_rate_3",
  "recent_attack_rate_5", "attack_streak_current", "target_recently_attacked",
  "reply_after_attack", "target_response_context_score"
)

FLOAT_COLUMNS <- c(
  "login_percentage", "date_timestamp", "sort_timestamp", "created_timestamp",
  "thread_position_rel", "time_since_thread_start", "time_since_previous_comment",
  "log_time_since_thread_start", "log_time_since_previous_comment",
  "user_previous_thread_share", "thread_mean_comments_per_user",
  "thread_max_user_share", "thread_single_comment_user_share",
  "prev_attack_rate", "prev_toxicity_score_mean"
)


# ------------------------------------------------------------
# Speicherort für trainiertes Professor-Modell
# ------------------------------------------------------------
MODEL_DIR <- "models"
MODEL_PATH <- file.path(MODEL_DIR, "professor_synthetic_role_model.rds")