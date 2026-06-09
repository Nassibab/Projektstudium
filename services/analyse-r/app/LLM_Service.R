library(httr2)

call_llm <- function(prompt) {
  body <- list(
    model = "gpt-oss-120b",
    messages = list(
      list(
        role = "user",
        content = prompt
      )
    ),
    temperature = 0.2
  )

  response <- request("https://hub.nhr.fau.de/api/llmgw/v1/chat/completions") |>
    req_headers(
      Authorization = paste("Bearer", Sys.getenv("LLMAPI_KEY")),
      `Content-Type` = "application/json"
    ) |>
    req_body_json(body) |>
    req_perform()

  result <- resp_body_json(response)

  result$choices[[1]]$message$content
}