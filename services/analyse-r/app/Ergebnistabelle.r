evaluate_test_predictions <- function(test_data_ranger, test_identifiers, prob_df, start.time_total, model_name, seed_value, test_accuracy, test_classification_error, pred_response) {
  prediction_results_table_full <- test_data_ranger %>%
    mutate(across(where(is.factor), as.character)) %>%
    select(-synthetic_role) %>%
    mutate(predicted_synthetic_role = as.character(pred_response)) %>%
    bind_cols(test_identifiers, ., prob_df)
    
  cat("\nR-Ergebnistabelle pro Testkommentar erfolgreich generiert.\n")
  
  end.time_total <- Sys.time()
  total_time <- end.time_total - start.time_total
  
  results_row <- data.frame(
    model = model_name,
    seed = seed_value,
    test_accuracy = test_accuracy,
    test_classification_error = test_classification_error,
    total_time_min = as.numeric(total_time, units = "mins")
  )

  return(list(
    status = "success",
    full_prediction_results = prediction_results_table_full, 
    model_comparison_metrics = results_row
  ))
}