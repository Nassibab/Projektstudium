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





