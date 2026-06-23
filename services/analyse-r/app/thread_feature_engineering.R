# ------------------------------------------------------------
# Thread- und Reply-Strukturfeatures
# ------------------------------------------------------------
# Diese Datei erzeugt Positions-, Reply-, Parent- und Thread-Frequenzfeatures.
# Wichtig: Bluesky-IDs sind Text-IDs. Deshalb werden id/parent NICHT als Integer
# berechnet, sondern über struktur_id und struktur_parent als Character behandelt.
# ------------------------------------------------------------

calculate_reply_depth <- function(ids, parents) {
  ids <- as.character(ids)
  parents <- as.character(parents)

  parent_lookup <- setNames(parents, ids)
  depth_vec <- integer(length(ids))

  for (i in seq_along(ids)) {
    current_parent <- parents[i]
    depth <- 0L
    safety_counter <- 0L

    while (
      !is.na(current_parent) &&
        current_parent != "" &&
        current_parent != "0" &&
        current_parent %in% names(parent_lookup) &&
        safety_counter < 100
    ) {
      depth <- depth + 1L
      current_parent <- parent_lookup[[current_parent]]
      safety_counter <- safety_counter + 1L
    }

    depth_vec[i] <- depth
  }

  depth_vec
}


add_thread_features <- function(data) {
  required_cols <- c("thread_id", "comment_id", "parent", "login")
  missing_cols <- setdiff(required_cols, names(data))

  if (length(missing_cols) > 0) {
    stop(paste(
      "Folgende Spalten fehlen für Thread-Features:",
      paste(missing_cols, collapse = ", ")
    ))
  }

  data <- data %>%
    mutate(
      row_id_temp = row_number(),

      structure_id = ifelse(
        !is.na(comment_id) & trimws(as.character(comment_id)) != "",
        as.character(comment_id),
        as.character(id)
      ),

      structure_parent = ifelse(
        is.na(parent),
        "",
        as.character(parent)
      )
    )

  if (!"date_timestamp" %in% names(data)) {
    data$date_timestamp <- if ("created_timestamp" %in% names(data)) {
      suppressWarnings(as.numeric(data$created_timestamp))
    } else {
      suppressWarnings(as.numeric(row_number()))
    }
  }

  if (all(is.na(data$date_timestamp))) {
    data$date_timestamp <- suppressWarnings(as.numeric(seq_len(nrow(data))))
  }

  data <- data %>%
    mutate(
      sort_timestamp = ifelse(
        is.na(date_timestamp),
        as.numeric(row_id_temp),
        date_timestamp
      )
    )

  data <- data %>%
    group_by(thread_id) %>%
    arrange(sort_timestamp, row_id_temp, .by_group = TRUE) %>%
    mutate(
      thread_position_abs = row_number(),
      thread_size = n(),

      thread_position_rel = ifelse(
        thread_size > 1,
        (thread_position_abs - 1) / (thread_size - 1),
        0
      ),

      num_previous_comments = thread_position_abs - 1,

      is_thread_start = ifelse(
        as.character(structure_id) == as.character(thread_id) |
          is.na(structure_parent) |
          structure_parent == "" |
          structure_parent == "0",
        1L,
        0L
      ),

      is_reply = ifelse(
        is_thread_start == 1L,
        0L,
        1L
      ),

      previous_comment_exists = ifelse(num_previous_comments > 0, 1L, 0L),

      time_since_thread_start = as.numeric(sort_timestamp - first(sort_timestamp)),

      time_since_previous_comment = as.numeric(sort_timestamp - lag(sort_timestamp)),
      time_since_previous_comment = ifelse(
        is.na(time_since_previous_comment),
        0,
        time_since_previous_comment
      )
    ) %>%
    ungroup()

# ---------------------------------------------------------------------------
# User-Aktivität innerhalb eines Threads
# ---------------------------------------------------------------------------

  data <- data %>%
    group_by(thread_id, login) %>%
    arrange(sort_timestamp, row_id_temp, .by_group = TRUE) %>%
    mutate(
      user_thread_comment_count_before = row_number() - 1,
      user_thread_comment_count_total = n()
    ) %>%
    ungroup() %>%
    mutate(
      user_previous_thread_share = ifelse(
        num_previous_comments > 0,
        user_thread_comment_count_before / num_previous_comments,
        0
      )
    )

# ---------------------------------------------------------------------------
# Reply Depth je Thread berechnen
# ---------------------------------------------------------------------------

  reply_depth_data <- data %>%
    group_by(thread_id) %>%
    arrange(sort_timestamp, row_id_temp, .by_group = TRUE) %>%
    mutate(
      reply_depth = calculate_reply_depth(structure_id, structure_parent)
    ) %>%
    ungroup() %>%
    select(row_id_temp, reply_depth)

  data <- data %>%
    left_join(reply_depth_data, by = "row_id_temp")

# --------------------------------------------------------------------------
# Anzahl direkter Antworten pro Kommentar berechnen
# --------------------------------------------------------------------------

  children_counts <- data %>%
    filter(!is.na(structure_parent), structure_parent != "", structure_parent != "0") %>%
    count(thread_id, structure_parent, name = "num_children")

  data <- data %>%
    left_join(
      children_counts,
      by = c("thread_id" = "thread_id", "structure_id" = "structure_parent")
    ) %>%
    mutate(
      num_children = ifelse(is.na(num_children), 0L, num_children)
    )

# --------------------------------------------------------------------------
# Prüfen, ob Parent-Kommentar der Root-Kommentar des Threads ist
# --------------------------------------------------------------------------

  root_lookup <- data %>%
    group_by(thread_id) %>%
    arrange(sort_timestamp, row_id_temp, .by_group = TRUE) %>%
    summarise(
      root_structure_id = first(structure_id),
      .groups = "drop"
    )

  data <- data %>%
    left_join(root_lookup, by = "thread_id") %>%
    mutate(
      parent_is_root = ifelse(
        !is.na(structure_parent) &
          structure_parent != "" &
          structure_parent == root_structure_id,
        1L,
        0L
      )
    ) %>%
    select(-root_structure_id)

# -------------------------------------------------------------------------
# Zielaccount-Variable
# -------------------------------------------------------------------------

  if ("target_login" %in% names(data)) {
    data <- data %>%
      mutate(
        is_target_login_numeric = ifelse(
          !is.na(login) &
            !is.na(target_login) &
            as.character(login) == as.character(target_login),
          1L,
          0L
        )
      )
  } else {
    data$is_target_login_numeric <- 0L
  }


# -------------------------------------------------------------------------
# Zusätzliche Thread-Frequenzvariablen
# -------------------------------------------------------------------------

  thread_frequency_vars <- data %>%
    group_by(thread_id) %>%
    summarise(
      thread_user_count = n_distinct(login),
      thread_comment_count = n(),
      thread_mean_comments_per_user = thread_comment_count / thread_user_count,
      thread_max_comments_by_one_user = max(as.numeric(table(login))),
      thread_single_comment_user_count = sum(as.numeric(table(login)) == 1),
      .groups = "drop"
    )

  data <- data %>%
    left_join(thread_frequency_vars, by = "thread_id") %>%
    mutate(
      thread_max_user_share = thread_max_comments_by_one_user / thread_comment_count,
      thread_single_comment_user_share = thread_single_comment_user_count / thread_user_count,
      log_time_since_thread_start = log1p(time_since_thread_start),
      log_time_since_previous_comment = log1p(time_since_previous_comment)
    ) %>%
    select(-row_id_temp)

  data
}