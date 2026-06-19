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


# 📊 Datenbank-Dokumentation

## 1. Überblick

Dieses Projekt verwendet eine **hybride Datenbankarchitektur**, bestehend aus:

* **MongoDB** (NoSQL)
  → Speicherung der Rohdaten (Threads, Kommentare, Analysen)

* **Neo4j** (Graphdatenbank)
  → Modellierung von Beziehungen zwischen Nutzern, Kommentaren und Threads

Ziel ist es, sowohl strukturierte Daten effizient zu speichern als auch komplexe Interaktionen (z. B. Reply-Strukturen oder Nutzerbeziehungen) analysierbar zu machen.

---

## 2. Systemstart

Alle Services werden über Docker gestartet:

```bash
docker-compose up -d --build
```

Gestartete Container:

* `psb1-127-api-1`
* `psb1-127-mongodb-1`
* `psb1-127-neo4j-1`

---

## 3. MongoDB

### 3.1 Verbindung

```bash
docker compose exec mongodb mongosh
```

```js
use shitstorm_db
```

---

### 3.2 Datenstruktur

MongoDB speichert die Rohdaten in folgenden Collections:

* `threads`
* `comments`
* `analysis_results`
* `moderation_suggestions`
* `alerts`

---

### 3.3 Beispielabfragen

Anzahl Threads:

```js
db.threads.countDocuments()
```

Anzahl Kommentare:

```js
db.comments.countDocuments()
```

Alle Threads anzeigen:

```js
db.threads.find().limit(5)
```

Kommentare zu einem Thread:

```js
db.comments.find({ thread_id: "THREAD_ID" })
```

---

## 4. Neo4j

### 4.1 Zugriff

Browser öffnen:

```
http://localhost:7474
```

Login:

```
User: neo4j
Password: password
```

---
### 4.2 Datenmodell

### 🟢 Knoten (Nodes)

Folgende Knotentypen werden verwendet:

- **User**  
  Repräsentiert einen Nutzer (z. B. Social Media Account)

- **Comment**  
  Einzelne Beiträge oder Kommentare innerhalb eines Threads

- **Thread**  
  Diskussionsstrang (z. B. Post + Kommentare)

- **Dataset**  
  Quelle der Daten (z. B. JSON-Datei oder externe Plattform wie Bluesky, Instagram)

---

## 🔗 Beziehungen (Relationships)

```text
(:Dataset)-[:CONTAINS_THREAD]->(:Thread)
(:User)-[:WROTE]->(:Comment)
(:Comment)-[:IN_THREAD]->(:Thread)
(:Comment)-[:REPLY_TO]->(:Comment)
(:User)-[:REPLIED_TO_USER]->(:User)
```
---

### 4.3 Beispielabfragen

Alle Knoten:

```cypher
MATCH (n) RETURN n LIMIT 50;
```

Alle Beziehungen:

```cypher
MATCH p=()-[]->() RETURN p LIMIT 25;
```

---

User → Comments:

```cypher
MATCH (u:User)-[:WROTE]->(c:Comment)
RETURN u, c LIMIT 50;
```

Kommentare → Threads:

```cypher
MATCH (c:Comment)-[:IN_THREAD]->(t:Thread)
RETURN c, t LIMIT 50;
```

Antwortstrukturen:

```cypher
MATCH (c1:Comment)-[:REPLY_TO]->(c2:Comment)
RETURN c1, c2 LIMIT 50;
```

User-Interaktionen:

```cypher
MATCH (u1:User)-[:REPLIED_TO_USER]->(u2:User)
RETURN u1, u2 LIMIT 50;
```

---

## 5. Synchronisation (MongoDB → Neo4j)

Die Daten werden über die API synchronisiert.

### 5.1 Swagger UI

```
http://localhost:8000/docs
```

---

### 5.2 Endpoint

```
POST /sync/graph
```

Alternativ per Terminal:

```bash
curl -X POST http://localhost:8000/sync/graph
```

---


## 6. Reset & Debugging

### Neo4j komplett zurücksetzen

```cypher
MATCH (n) DETACH DELETE n;
```

---

### MongoDB prüfen

```js
db.comments.countDocuments()
db.threads.countDocuments()
```

---

### Logs prüfen

```bash
docker-compose logs api --tail=100
```

---




