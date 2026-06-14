# ------------------------------------------------------------
# Kontextfeatures für Attack-/Toxicity-Verläufe
# ------------------------------------------------------------
# Diese Funktion nutzt vorhandene attack_score/toxicity_score-Werte und berechnet
# daraus Verlaufsvariablen pro Thread: vorherige Attacken, Attack-Raten,
# Toxicity-Historie, Recent-Attack-Rates und Attack-Streaks.

add_context_features <- function(data) {
  if (!"attack_score" %in% names(data)) {
    data$attack_score <- 1L
  }

  if (!"toxicity_score" %in% names(data)) {
    data$toxicity_score <- 1L
  }

  if (!"direct_address_count" %in% names(data)) {
    data$direct_address_count <- 0L
  }

  if (!"is_target_login_numeric" %in% names(data)) {
    data$is_target_login_numeric <- 0L
  }

  data <- data %>%
    mutate(
      attack_score_numeric_for_context = suppressWarnings(as.numeric(as.character(attack_score))),
      toxicity_score_numeric_for_context = suppressWarnings(as.numeric(as.character(toxicity_score))),
      attack_score_numeric_for_context = ifelse(is.na(attack_score_numeric_for_context), 1, attack_score_numeric_for_context),
      toxicity_score_numeric_for_context = ifelse(is.na(toxicity_score_numeric_for_context), 1, toxicity_score_numeric_for_context),
      is_attack_context = ifelse(attack_score_numeric_for_context >= 5, 1L, 0L)
    )

  data <- data %>%
    group_by(thread_id) %>%
    arrange(sort_timestamp, id, .by_group = TRUE) %>%
    mutate(
      previous_comment_attack = lag(is_attack_context),
      previous_comment_attack = ifelse(is.na(previous_comment_attack), 0L, previous_comment_attack),

      prev_attack_count = lag(cumsum(is_attack_context)),
      prev_attack_count = ifelse(is.na(prev_attack_count), 0L, prev_attack_count),

      prev_attack_rate = ifelse(num_previous_comments > 0, prev_attack_count / num_previous_comments, 0),

      prev_toxicity_score_sum = lag(cumsum(toxicity_score_numeric_for_context)),
      prev_toxicity_score_sum = ifelse(is.na(prev_toxicity_score_sum), 0, prev_toxicity_score_sum),

      prev_toxicity_score_mean = ifelse(num_previous_comments > 0, prev_toxicity_score_sum / num_previous_comments, 0),

      prev_toxicity_score_max = sapply(seq_along(toxicity_score_numeric_for_context), function(i) {
        if (i == 1) 0 else max(toxicity_score_numeric_for_context[1:(i - 1)], na.rm = TRUE)
      }),

      prev_attack_score_max = sapply(seq_along(attack_score_numeric_for_context), function(i) {
        if (i == 1) 0 else max(attack_score_numeric_for_context[1:(i - 1)], na.rm = TRUE)
      }),

      recent_attack_rate_3 = sapply(seq_along(is_attack_context), function(i) {
        start_i <- max(1, i - 3)
        end_i <- i - 1
        if (end_i < start_i) 0 else mean(is_attack_context[start_i:end_i], na.rm = TRUE)
      }),

      recent_attack_rate_5 = sapply(seq_along(is_attack_context), function(i) {
        start_i <- max(1, i - 5)
        end_i <- i - 1
        if (end_i < start_i) 0 else mean(is_attack_context[start_i:end_i], na.rm = TRUE)
      })
    ) %>%
    ungroup()

  data <- data %>%
    group_by(thread_id) %>%
    arrange(sort_timestamp, id, .by_group = TRUE) %>%
    mutate(
      attack_streak_current = sapply(seq_along(is_attack_context), function(i) {
        if (i == 1) {
          return(0L)
        }

        previous_values <- is_attack_context[1:(i - 1)]
        streak <- 0L

        for (j in length(previous_values):1) {
          if (previous_values[j] == 1L) {
            streak <- streak + 1L
          } else {
            break
          }
        }

        streak
      })
    ) %>%
    ungroup()

  data <- data %>%
    group_by(thread_id) %>%
    arrange(sort_timestamp, id, .by_group = TRUE) %>%
    mutate(
      target_recently_attacked = ifelse(prev_attack_count > 0, 1L, 0L),
      reply_after_attack = previous_comment_attack,
      target_response_context_score =
        is_target_login_numeric +
        target_recently_attacked +
        ifelse(direct_address_count > 0, 1L, 0L)
    ) %>%
    ungroup()

  data <- data %>%
    select(
      -attack_score_numeric_for_context,
      -toxicity_score_numeric_for_context,
      -is_attack_context,
      -prev_toxicity_score_sum
    )

  data
}
