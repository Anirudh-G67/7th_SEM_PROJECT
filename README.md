# IntervueX FastAPI Backend

This project wraps the AI functions from the IntervueX Jupyter Notebook in a FastAPI service.

## Requirements

- Python 3.10+
- Ollama installed and running on the machine that runs this API
- Ollama models:
  - `phi3:latest`
  - `llama3.2:latest`

## 1. Create and activate a virtual environment

### Windows PowerShell

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, use Command Prompt:

```cmd
venv\Scripts\activate.bat
```

## 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

## 3. Install/check Ollama models

```bash
ollama pull phi3:latest
ollama pull llama3.2:latest
ollama list
```

Make sure the Ollama service is running before starting FastAPI.

## 4. Start the API

```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Open:

- API root: http://127.0.0.1:8000/
- Health check: http://127.0.0.1:8000/health
- Swagger UI: http://127.0.0.1:8000/docs

## API endpoints

### GET `/health`

Checks whether the FastAPI application is running.

### POST `/interviews/start`

Request JSON:

```json
{
  "education": "B.Tech Computer Science",
  "experience": 0,
  "interview_type": "Technical",
  "target_role": "AI/ML Engineer",
  "interview_difficulty": "Easy",
  "interview_length": 5
}
```

Returns a `session_id` and the first question.

### POST `/interviews/{session_id}/answer`

Request JSON:

```json
{
  "answer": "Machine Learning is a branch of AI..."
}
```

Returns the evaluation, extracted keywords, and either the next question or final results.

### GET `/interviews/{session_id}/status`

Returns basic session progress.

## Frontend speech input

The original notebook used `speech_recognition` with `sr.Microphone()`. That microphone code runs on the computer executing Python; it cannot directly access a remote website user's microphone.

For this initial API version, the frontend should capture speech and send the transcribed text in the same JSON `answer` field. Audio upload/transcription can be added as a separate API feature later.

## CORS

By default, local development origins for common React/Vite ports are allowed.

For deployment, set `INTERVUEX_FRONTEND_ORIGINS` to the exact frontend origin or comma-separated origins, for example:

```text
https://your-frontend.example.com
```

## Important deployment note

The `sessions` dictionary in `main.py` stores interview state in memory. It is suitable for local testing and a single-process prototype. It is not durable: sessions are lost when the server restarts, and multiple server workers will not share the same dictionary. Before production or multiple instances, move session storage to Redis or a database.

Ollama and both models must be available on the server that runs this API. Do not expose Ollama's port directly to the public internet; expose the FastAPI service instead.
