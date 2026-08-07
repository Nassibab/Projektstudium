# Project Description
The project is an early-warning and analysis system for toxic social-media discussions: Live Bluesky comments are collected and stored in a database. They are then enriched by an LLM with linguistic features such as irony and evaluated by an ML model using these additional features. Afterwards, toxicity scores are calculated across different time periods to detect a potential "shitstorm." Finally, in the moderation component, the LLM suggests situation-specific countermeasures, such as deleting a comment or post, providing an explanation, or blocking a user.


# Group Project Template (API + Vue Frontend)

## Markdown Preview Shortcuts

| Platform          | Split Preview | New Tab        |
| ----------------- | ------------- | -------------- |
| **Windows/Linux** | `Ctrl+K V`    | `Ctrl+Shift+V` |
| **Mac**           | `Cmd+K V`     | `Shift+Cmd+V`  |

*Click 📄 icon (top-right) in VSCode for instant preview*

---

## Requirements

### 1. Docker Desktop

* **Windows**: [Docker Desktop for Windows](https://docs.docker.com/desktop/setup/install/windows-install/)
* **macOS**: [Docker Desktop for macOS](https://docs.docker.com/desktop/install/mac-install/)
* **Linux**: [Docker Engine + Compose plugin](https://docs.docker.com/engine/install/)

### 2. VSCode Extensions

| Extension          | ID                                   | Purpose                            |
| ------------------ | ------------------------------------ | ---------------------------------- |
| **Containers**     | `ms-vscode-remote.remote-containers` | Docker integration                 |
| **Vue - Official** | `Vue.volar`                          | Vue.js IntelliSense                |
| **Python**         | `ms-python.python`                   | Python virtual environment support |

---

## Quick Start (Docker)

### Unix-like systems (Linux/macOS)

```bash
chmod +x scripts/build.sh
./scripts/build.sh
```

### Windows

Ensure Docker Desktop is running. If you haven't already, allow PowerShell scripts to run (open PowerShell as Administrator and run: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`).

Then, open PowerShell and navigate to the project root:

```powershell
.\scripts\build.ps1
```

This PowerShell script automates the build and startup process, including waiting for services to be ready.

This builds all services, including the Vue frontend via npm.

---

## Stopping and Managing Services

Once running, use these commands to manage your containers (works on all platforms):
- **Creates/updates and starts all containers (or only specific ones if specified)**: `docker compose up <service-name>`
- **start a single container (standalone, not via Compose)**: `docker run`
- **Stop services**: `docker compose down`
- **View logs**: `docker compose logs -f` (follow logs in real-time)
- **xxx**: docker compose up --build
- **Restart services**: `docker compose restart`
- **Rebuild without cache**: `docker compose build --no-cache`
- **Check status**: `docker compose ps`
- **Clean up unused images/containers**: `docker system prune -a` (removes old builds)


---

## Local API Development (Fixes Uvicorn Error)

The error occurs because:

```
uvicorn app.main:app
```

cannot find the module when executed inside `services/api`, since Python’s import path does not include the project root.

---

### Option 1: Run from Project Root (Recommended)

```bash
cd services/api
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate

# Mac/Linux:
source .venv/bin/activate

pip install -r requirements.txt

cd ..  # Back to project root

uvicorn services.api.app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

### Option 2: Use `--app-dir` (Run inside services/api)

```bash
cd services/api
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate

# Mac/Linux:
source .venv/bin/activate

pip install -r requirements.txt

uvicorn app.main:app --app-dir . --host 0.0.0.0 --port 8000 --reload
```

---

## VSCode Setup

1. Open Command Palette: `Ctrl+Shift+P`
2. Select: **Python: Select Interpreter**
3. Choose your `.venv` environment

---

You're now ready to develop and run the API locally 🚀

---

# Shitstorm Detection System

## Projektbeschreibung

Dieses Projekt implementiert eine serviceorientierte Architektur zur Erkennung und Analyse von Shitstorms in Social-Media-Diskussionen. Unterstützt werden sowohl ein annotierter Professor-Datensatz als auch Live-Daten der Plattform Bluesky.

Die Verarbeitung umfasst:

- Import und Speicherung der Daten
- LLM-basierte Merkmalsgenerierung
- ML-basierte Vorhersage
- Moderationsbewertung
- optionale graphbasierte Visualisierung mit Neo4j

---

# Voraussetzungen

## Verfügbare Services

| Service | URL |
|----------|-----|
| Frontend | http://localhost:3000/ |
| API-Service | http://localhost:8000/docs |
| Ingestion-Service | http://localhost:8001/docs |
| LLM-Service | http://localhost:8011/docs |
| Analyse-Engine | http://localhost:8020/__docs__/ |
| Mongo Express | http://localhost:8081/db/shitstorm_db/ |
| Neo4j Browser | http://localhost:7474 |

---

# 📊 Datenbank-Dokumentation

## MongoDB

MongoDB dient als zentrale Datenbank zur Speicherung aller Rohdaten, Analysemerkmale und Vorhersageergebnisse.

### Mongo Express

```
http://localhost:8081/db/shitstorm_db/
```

### Collections

#### Rohdaten

- threads
- comments

#### LLM-Analyse

- llm_analysis_results

#### Professor-Datensatz

- professor_test_comment_results
- professor_test_thread_results
- professor_test_user_results
- professor_test_model_results

#### Bluesky

- bluesky_prediction_comments_results
- bluesky_prediction_thread_results
- bluesky_prediction_user_results
- bluesky_prediction_model_results

---

## Neo4j

Neo4j dient der optionalen graphbasierten Darstellung der Beziehungen zwischen Datensätzen, Threads, Kommentaren und Nutzern.

### Browser

```
http://localhost:7474
```

Login

```
User: neo4j
Password: password
```

### Graphmodell

#### Knoten

| Typ | Beschreibung |
|------|--------------|
| Dataset | Herkunft der Daten |
| Thread | Diskussionsstrang |
| Comment | Einzelner Kommentar |
| User | Verfasser eines Kommentars |

#### Beziehungen

```text
(:Dataset)-[:CONTAINS_THREAD]->(:Thread)
(:Thread)-[:CONTAINS_COMMENT]->(:Comment)
(:User)-[:WROTE]->(:Comment)
(:Comment)-[:REPLY_TO]->(:Comment)
(:User)-[:REPLIED_TO_USER]->(:User)
```

---

## Frontend Nutzung

Das Frontend erlaubt es einen Thread auszuaehlen aus dem Professordatensatz oder Bluesky. Entsprechend braucht es etwa beim Professordatensatz die Angabe eines Source Files.

Als Beispiel kann als Thread_ID ```SYN0001``` angegeben werden.
Dann ```Professor``` in der Auswahl.
Und zuletzt bspw. dieser Datensatz 
```synthetic_shitstorm_dataset_3.json```


---

## Synchronisation MongoDB → Neo4j

Swagger

```
http://localhost:8000/docs
```

Synchronisation starten

```http
POST /sync/graph
```

Synchronisationsbericht

```http
GET /report/threads
```

---

# 🔄 Gesamtablauf der Datenverarbeitung

Nachfolgend wird die Verarbeitung der beiden unterstützten Datenquellen beschrieben.

# Professor-Datensatz

## 1. Professor-Datensatz importieren

Swagger

```
http://localhost:8000/docs
```

Endpoint

```http
POST /import/professor
```

**Ergebnis**

- Import der JSON-Dateien
- Speicherung in `threads`
- Speicherung in `comments`

---

## 2. LLM-Merkmale importieren

Die LLM-Merkmale wurden bereits einmalig erzeugt und anschließend als JSON exportiert.

```http
POST /analysis/import-professor-llm
```

**Ergebnis**

- Speicherung in `llm_analysis_results`

---

## 3. Trainingsdatensatz erzeugen

Swagger

```
http://localhost:8000/docs
```

Alle Threads

```http
GET /analysis/training/prof-comments/all
```

Einzelner Thread

```http
GET /analysis/training/prof-comments/thread/{thread_id}
```

Verwendete Collections

- threads
- comments
- llm_analysis_results

---

## 4. Modell trainieren

Swagger

```
http://localhost:8020/__docs__/
```

```http
GET /train-full-model
```

Erzeugte Collections

- professor_test_comment_results
- professor_test_thread_results
- professor_test_user_results
- professor_test_model_results

---

# Bluesky-Daten

## 1. Bluesky-Stream starten

Swagger

```
http://localhost:8001/docs
```

```http
GET /stream?url={post_url}
```

**Ergebnis**

- Thread importieren
- Kommentare speichern
- Jetstream starten

---

## 2. Automatische Verarbeitung

Bei jedem neu eingehenden Kommentar startet automatisch:

```http
POST /pipeline/bluesky/comment-ingested
```

### LLM-Analyse

```http
POST http://llm-service:8011/analyze/thread
```

Speichert

- llm_analysis_results

### ML-Vorhersage

```http
GET http://analyse-r:8000/predict-bluesky
```

Speichert

- bluesky_prediction_comments_results
- bluesky_prediction_thread_results
- bluesky_prediction_user_results
- bluesky_prediction_model_results

---

# Gesamtablauf

## Professor

```text
Professor JSON
      │
      ▼
POST /import/professor
      │
      ▼
threads
comments
      │
      ▼
POST /analysis/import-professor-llm
      │
      ▼
llm_analysis_results
      │
      ▼
GET /analysis/training/prof-comments/all
      │
      ▼
GET /train-full-model
      │
      ▼
professor_test_*_results
```

---

## Bluesky

```text
GET /stream?url=...
      │
      ▼
Ingestion-Service
      │
      ▼
threads
comments
      │
      ▼
POST /pipeline/bluesky/comment-ingested
      │
      ▼
POST /analyze/thread
      │
      ▼
llm_analysis_results
      │
      ▼
GET /predict-bluesky
      │
      ▼
bluesky_prediction_*_results
```





# Shitstorm Moderation Service

Dieser Service bewertet Kommentare und Threads auf mögliche Shitstorm-Dynamiken.  
Er berechnet ein Shitstorm-Barometer, gibt Warnstufen zurück und kann bei Bedarf Gegenrede / Counter Speech erzeugen.

Der Service basiert auf FastAPI.

---

## Starten

Im Projektverzeichnis:

```bash
docker compose up --build
```

Oder falls der Container bereits gebaut wurde:

```bash
docker compose up
```

Die API läuft standardmäßig unter:

```text
http://localhost:8000
```

---

## Wichtige Umgebungsvariablen

Für die Counter-Speech-Generierung wird ein LLM-Zugang benötigt.

```env
LLMAPI_KEY=dein_api_key
COUNTER_SPEECH_MODEL=gpt-oss-120b
API_BASE_URL=http://api:8000
```

`LLMAPI_KEY` ist nötig, wenn echte Gegenrede generiert werden soll.  
`COUNTER_SPEECH_MODEL` ist optional. Wenn nichts gesetzt ist, wird standardmäßig `gpt-oss-120b` verwendet.

---

# Endpoints

## 1. Health Check

```http
GET /
```

Prüft, ob der Moderation-Service läuft.

### Beispiel

```bash
curl http://localhost:8000/
```

### Beispiel-Response

```json
{
  "message": "Moderation Service is running"
}
```

---

## 2. Einzelnen Kommentar live moderieren

```http
POST /moderation/comment
```

Dieser Endpoint verarbeitet einen einzelnen Kommentar.  
Der Kommentar wird in ein Zeitfenster einsortiert, aggregiert und anschließend mit dem Shitstorm-Scorer bewertet.

### Verwendung

```bash
curl -X POST "http://localhost:8000/moderation/comment" \
  -H "Content-Type: application/json" \
  -d '{
    "comment_id": "9000165",
    "thread_id": "SYN0001",
    "login": "USR0211",
    "text": "Das ist alles andere als normal!",
    "created_at": "2026-01-02 03:09:00",
    "parent_id": "9000001",

    "irony": 0,
    "attack_score": 1,
    "toxicity_score": 1,
    "swearword_count": 0,
    "negative_word_count": 0,
    "insult_count": 0,
    "direct_address_count": 0,
    "imperative_count": 2,
    "accusation_marker_count": 0,
    "mockery_marker_count": 0,
    "is_attacking": 0,

    "reply_depth": 1,
    "parent_is_root": 1,
    "num_children": 2,
    "thread_position_abs": 354,
    "thread_position_rel": 0.2939,
    "num_previous_comments": 353,

    "prev_attack_rate": 0.017,
    "prev_toxicity_score_mean": 1.402,
    "prev_attack_count": 6,
    "prev_toxicity_score_max": 6,
    "prev_attack_score_max": 6,

    "recent_attack_rate_3": 0,
    "recent_attack_rate_5": 0,
    "attack_streak_current": 0,
    "target_recently_attacked": 1,
    "reply_after_attack": 0,
    "target_response_context_score": 1,

    "predicted_synthetic_role": "3",
    "predicted_synthetic_role_label": null,

    "prob_class_1": 0.0002,
    "prob_class_2": 0.2082,
    "prob_class_3": 0.7245,
    "prob_class_4": 0.023,
    "prob_class_5": 0.0395,
    "prob_class_6": 0,
    "prob_class_7": 0.0046
  }'
```

### Wichtig

Dieser Endpoint erwartet das vollständige Standardformat, weil der `WindowAggregator` viele Felder benötigt.

Pflichtfelder sind unter anderem:

```text
comment_id
thread_id
login
text
created_at
parent_id
attack_score
toxicity_score
is_attacking
reply_depth
thread_position_abs
recent_attack_rate_3
recent_attack_rate_5
target_recently_attacked
reply_after_attack
prob_class_1 bis prob_class_7
```

Wenn Felder fehlen, kann der Service mit einem Fehler abbrechen.

### Beispiel-Response

```json
{
  "status": "success",
  "comment_id": "9000165",
  "thread_id": "SYN0001",
  "current_window_metrics": {
    "thread_id": "SYN0001",
    "window_start": "2026-01-02T03:05:00",
    "window_end": "2026-01-02T03:10:00",
    "comment_count": 1,
    "unique_users": 1,
    "attack_count": 0,
    "attack_ratio": 0.0,
    "toxic_count": 0,
    "toxic_ratio": 0.0
  },
  "shitstorm_prediction": {
    "barometer_score_0_1": 0.3605,
    "shitstorm_barometer": 36.05,
    "warning_level": "watch",
    "evaluation_status": "ready"
  },
  "countermeasures": {
    "level": "watch",
    "actions": ["increase_monitoring"]
  },
  "counter_speech": {
    "should_generate": false,
    "reason": "Counter speech is not required for this comment.",
    "generated_text": null,
    "error": null
  }
}
```

---

## 3. Live-Warning-Payload verarbeiten

```http
POST /moderation/warning
```

Dieser Endpoint ist für einen Live-Payload gedacht, der aus einem aktuellen Kommentar und vorherigen Kommentaren besteht.

Er ist besonders nützlich, wenn zusätzlich zur Moderationsbewertung auch Kontext für Counter Speech übergeben werden soll.

### Erwartetes Format

```json
{
  "platform": "professor",
  "source_file": "synthetic_shitstorm_dataset_3.json",
  "thread": {
    "thread_id": "SYN0001",
    "title": "re",
    "text": "Ausgangskommentar oder Thread-Kontext"
  },
  "latest_comment": {
    "comment_id": "9000165",
    "thread_id": "SYN0001",
    "parent_id": "9000001",
    "login": "USR0211",
    "created_at": "2026-01-02 03:09:00",
    "text": "Aktueller Kommentar",

    "irony": 0,
    "attack_score": 1,
    "toxicity_score": 1,
    "swearword_count": 0,
    "negative_word_count": 0,
    "insult_count": 0,
    "direct_address_count": 0,
    "imperative_count": 2,
    "accusation_marker_count": 0,
    "mockery_marker_count": 0,
    "is_attacking": 0,

    "reply_depth": 1,
    "parent_is_root": 1,
    "num_children": 2,
    "thread_position_abs": 354,
    "thread_position_rel": 0.2939,
    "num_previous_comments": 353,

    "prev_attack_rate": 0.017,
    "prev_toxicity_score_mean": 1.402,
    "prev_attack_count": 6,
    "prev_toxicity_score_max": 6,
    "prev_attack_score_max": 6,

    "recent_attack_rate_3": 0,
    "recent_attack_rate_5": 0,
    "attack_streak_current": 0,
    "target_recently_attacked": 1,
    "reply_after_attack": 0,
    "target_response_context_score": 1,

    "predicted_synthetic_role": "3",
    "predicted_synthetic_role_label": null,

    "prob_class_1": 0.0002,
    "prob_class_2": 0.2082,
    "prob_class_3": 0.7245,
    "prob_class_4": 0.023,
    "prob_class_5": 0.0395,
    "prob_class_6": 0,
    "prob_class_7": 0.0046
  },
  "previous_comments": [
    {
      "comment_id": "9000002",
      "parent_id": "9000001",
      "login": "USR0348",
      "created_at": "2026-01-01 12:11:00",
      "text": "Vorheriger Kommentar 1"
    },
    {
      "comment_id": "9000032",
      "parent_id": "9000001",
      "login": "USR0434",
      "created_at": "2026-01-01 15:12:00",
      "text": "Vorheriger Kommentar 2"
    }
  ]
}
```

# Typischer Workflow


## Evaluation eines gespeicherten Threads

1. Thread liegt im API-Service vor.
2. `/moderation/evaluate-thread/{thread_id}` wird aufgerufen.
3. Service lädt den Thread über `API_BASE_URL`.
4. Kommentare werden nacheinander verarbeitet.
 
---

## Counter Speech testen

1. `LLMAPI_KEY` setzen.
2. `/moderation/counter-speech/test` mit `previous_comments` aufrufen. 
3. Für den nötigen JSON dies aufrufen: /moderation/thread/{thread_id}/latest-comment-contex


---

## Fehler: fehlender `LLMAPI_KEY`

Wenn Counter Speech generiert werden soll, muss `LLMAPI_KEY` gesetzt sein.

```env
LLMAPI_KEY=dein_api_key
```

Ohne diesen Key kann die Shitstorm-Bewertung weiterhin funktionieren, aber die LLM-Gegenrede nicht.


---

# Kurzüberblick

| Endpoint | Zweck |
|---|---|
| `GET /` | Health Check |
| `POST /moderation/comment` | Einzelnen Kommentar vollständig bewerten |
| `POST /moderation/warning` | Live-Payload mit aktuellem Kommentar und Verlauf verarbeiten |
| `POST /moderation/counter-speech/test` | Nur Counter Speech testen |
| `GET /moderation/evaluate-thread/{thread_id}` | Kompletten Thread aus API laden und evaluieren |


