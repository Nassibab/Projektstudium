# Group Project Template (API + Vue Frontend)

## 🚀 Markdown Preview Shortcuts

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

## 🎯 Quick Start (Docker)

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

## � Stopping and Managing Services

Once running, use these commands to manage your containers (works on all platforms):

- **Stop services**: `docker compose down`
- **View logs**: `docker compose logs -f` (follow logs in real-time)
- **Restart services**: `docker compose restart`
- **Rebuild without cache**: `docker compose build --no-cache`
- **Check status**: `docker compose ps`
- **Clean up unused images/containers**: `docker system prune -a` (removes old builds, use carefully)

---

## �🔧 Local API Development (Fixes Uvicorn Error)

The error occurs because:

```
uvicorn app.main:app
```

cannot find the module when executed inside `services/api`, since Python’s import path does not include the project root.

---

### ✅ Option 1: Run from Project Root (Recommended)

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

### ✅ Option 2: Use `--app-dir` (Run inside services/api)

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

## 🧠 VSCode Setup

1. Open Command Palette: `Ctrl+Shift+P`
2. Select: **Python: Select Interpreter**
3. Choose your `.venv` environment

---

You're now ready to develop and run the API locally 🚀
