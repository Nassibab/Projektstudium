# ----------------------------------------------------------------------------
# TF-IDF Feature Engineering
# ----------------------------------------------------------------------------
# Diese Funktion erzeugt Unigramm-/Bigramm-TF-IDF-Features aus subject + text.


get_text_field <- function(data, field_name) {
  if (field_name %in% names(data)) {
    ifelse(is.na(data[[field_name]]), "", as.character(data[[field_name]]))
  } else {
    rep("", nrow(data))
  }
}

create_tfidf_features <- function(train_data, test_data) {
  start_time <- Sys.time()

  train_subject <- get_text_field(train_data, "subject")
  test_subject <- get_text_field(test_data, "subject")

  if (all(train_subject == "") && "thread_title" %in% names(train_data)) {
    train_subject <- get_text_field(train_data, "thread_title")
  }

  if (all(test_subject == "") && "thread_title" %in% names(test_data)) {
    test_subject <- get_text_field(test_data, "thread_title")
  }

  train_text <- paste(train_subject, get_text_field(train_data, "text"))
  test_text <- paste(test_subject, get_text_field(test_data, "text"))

  tokens_train <- quanteda::tokens(
    quanteda::corpus(train_text),
    remove_punct = TRUE,
    remove_numbers = TRUE,
    remove_symbols = TRUE
  )

  tokens_test <- quanteda::tokens(
    quanteda::corpus(test_text),
    remove_punct = TRUE,
    remove_numbers = TRUE,
    remove_symbols = TRUE
  )

  tokens_train <- quanteda::tokens_tolower(tokens_train)
  tokens_test <- quanteda::tokens_tolower(tokens_test)

  tokens_train <- quanteda::tokens_ngrams(tokens_train, n = NGRAM_MIN:NGRAM_MAX, concatenator = "_")
  tokens_test <- quanteda::tokens_ngrams(tokens_test, n = NGRAM_MIN:NGRAM_MAX, concatenator = "_")

  dfm_train <- quanteda::dfm(tokens_train)
  dfm_train <- quanteda::dfm_trim(dfm_train, min_termfreq = TFIDF_MIN_TERMFREQ)

  top_terms <- names(quanteda::topfeatures(dfm_train, n = TFIDF_TOP_N))

  dfm_train <- quanteda::dfm_select(dfm_train, pattern = top_terms, selection = "keep")

  dfm_test <- quanteda::dfm(tokens_test)
  dfm_test <- quanteda::dfm_match(dfm_test, features = quanteda::featnames(dfm_train))

  train_counts <- as(dfm_train, "dgCMatrix")
  test_counts <- as(dfm_test, "dgCMatrix")

  train_row_sums <- Matrix::rowSums(train_counts)
  train_row_sums[train_row_sums == 0] <- 1

  test_row_sums <- Matrix::rowSums(test_counts)
  test_row_sums[test_row_sums == 0] <- 1

  train_tf <- train_counts / train_row_sums
  test_tf <- test_counts / test_row_sums

  n_train_docs <- nrow(train_counts)
  df_train <- Matrix::colSums(train_counts > 0)
  idf_train <- log((1 + n_train_docs) / (1 + df_train)) + 1

  train_tfidf <- t(t(train_tf) * idf_train)
  test_tfidf <- t(t(test_tf) * idf_train)

  train_tfidf_df <- as.data.frame(as.matrix(train_tfidf))
  test_tfidf_df <- as.data.frame(as.matrix(test_tfidf))

  tfidf_names <- paste0("tfidf_", make.names(quanteda::featnames(dfm_train), unique = TRUE))

  names(train_tfidf_df) <- tfidf_names
  names(test_tfidf_df) <- tfidf_names

  stopifnot(identical(names(train_tfidf_df), names(test_tfidf_df)))

  list(
    train_tfidf = train_tfidf_df,
    test_tfidf = test_tfidf_df,
    n_tfidf_features = ncol(train_tfidf_df),
    tfidf_time = Sys.time() - start_time
  )
}
