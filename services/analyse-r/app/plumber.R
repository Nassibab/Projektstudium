library(plumber)
library(jsonlite)


#* @get /
function() {
  list(message = "R-Analyse is running")
}

#* Vorhersage / Klassifikation
#* @post /predict
function(req) {
  body <- jsonlite::fromJSON(req$postBody)

  # TODO:
  # 1. Daten entgegennehmen
  # 2. Features/KPIs berechnen oder übernehmen
  # 3. Modell laden
  # 4. Vorhersage machen
  # 5. Ergebnis zurückgeben

  list(
    classification = "kein_shitstorm",
    confidence = 0.75,
    kpis = list()
  )
}