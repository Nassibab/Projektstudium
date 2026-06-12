create_prediction_html_table <- function(result) {
  paste0(
    "<html><head><meta charset='UTF-8'>",
    "<style>
      body { font-family: Arial; margin: 30px; }
      table { border-collapse: collapse; width: 100%; }
      th, td { border: 1px solid #ddd; padding: 8px; vertical-align: top; }
      th { background-color: #f2f2f2; }
      td { max-width: 450px; word-wrap: break-word; }
    </style>",
    "</head><body>",
    "<h2>Bluesky Predictions</h2>",
    "<table>",
    "<tr>",
    paste0("<th>", names(result), "</th>", collapse = ""),
    "</tr>",
    paste(
      apply(result, 1, function(row) {
        paste0(
          "<tr>",
          paste0("<td>", row, "</td>", collapse = ""),
          "</tr>"
        )
      }),
      collapse = ""
    ),
    "</table></body></html>"
  )
}