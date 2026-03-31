# Translation API with FastAPI and LibreTranslate

A production-ready REST API that translates text using [LibreTranslate](https://libretranslate.com/) (free open-source alternative to Google Cloud Translation), with API key authentication and rate limiting.

## Table of Contents
- [Project Overview](#project-overview)
- [Features](#features)
- [Technology Stack](#technology-stack)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [API Endpoints](#api-endpoints)
- [Authentication](#authentication)
- [Rate Limiting](#rate-limiting)
- [Error Handling](#error-handling)
- [Testing](#testing)
- [Project Structure](#project-structure)
- [Challenges & Solutions/ Troubleshooting](#challenges--solutions-troubleshooting)

## Project Overview

This FastAPI-based translation service provides secure REST endpoints for text translation to 40+ languages. Major languages **No Google billing required** – uses self-hosted LibreTranslate.

**Key Features:**
- API Key Authentication
- Rate Limiting (5 req/min/IP)
- Auto language detection
- Swagger UI docs at `/docs`
- Health monitoring

## Features

| Feature | Description |
|---------|-------------|
| Text Translation | 40+ languages (en, es, tl, de, fr, etc.) |
| Language Detection | Auto-detect or specify source language |
| API Key Auth | Secure `X-API-Key` header |
| Rate Limiting | 5 requests/minute per IP |
| Swagger UI | Interactive docs at `/docs` |
| Language List | Simple (`/languages`) & Detailed (`/languages/detailed`) |
| Health Check | API + LibreTranslate status |

## Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Web Framework | FastAPI | REST API |
| Server | Uvicorn | ASGI server |
| Translation | LibreTranslate | Open-source engine |
| HTTP Client | httpx | Async requests |
| Config | python-dotenv | .env vars |
| Language | Python 3.9+ | Runtime |

## Prerequisites

```bash
python --version  # 3.9+
pip --version
git --version
```

## Installation

### 1. Clone & Setup Venv
```bash
git clone <repo>
cd syscall_translation_API
```

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Mac/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
pip install libretranslate
```

### 3. Create .env
```
API_KEY=my-secret-api-key-123 /You can change this to your preferred API Key/
```

## Running (2 Terminals Required)

**Terminal 1 - LibreTranslate (downloads models first time ~30min, might be faster or will take more time depending on the internet speed):**
```bash
libretranslate --host 127.0.0.1 --port 5000
```
```
Running on http://127.0.0.1:5000
```

**Terminal 2 - FastAPI:**
```bash
uvicorn main_libretranslate:app --reload --host 0.0.0.0 --port 8000
```
```
Uvicorn running on http://0.0.0.0:8000
```

**Open:** http://localhost:8000/docs

## API Endpoints

### 1. Root
`GET /`
```json
{
  "message": "Translation API - LibreTranslate",
  "service": "LibreTranslate (self-hosted)",
  "docs": "/docs",
  "status": "running"
}
```

### 2. Health
`GET /health`
```json
{
  \"status\": \"healthy\",
  \"libretranslate\": \"running\"
}
```

### 3. Translate
`POST /translate`
**Headers:** `X-API-Key: my-secret-api-key-123`

**Body:**
```json
{
  \"text\": \"Hello World\",
  \"target_language\": \"es\",
  \"source_language\": \"auto\"
}
```

**Response:**
```json
{
  \"original_text\": \"Hello World\",
  \"translated_text\": \"Hola Mundo\",
  \"source_language\": \"en\",
  \"target_language\": \"es\"
}
```

### 4a. Languages (Simple)
`GET /languages`
Returns a list of all supported languages with their codes.

**Response:**
```json
{
  "service": "libretranslate",
  "languages": [
    {"code": "en", "name": "English"},
    {"code": "es", "name": "Spanish"},
    {"code": "tl", "name": "Tagalog"},
    {"code": "de", "name": "German"},
    {"code": "fr", "name": "French"}
  ],
  "note": "For detailed translation pairs (targets), use /languages/detailed"
}
```

### 4b. Languages (Detailed)
`GET /languages/detailed`
Returns full language data including translation targets (what languages you can translate from each source /its a bit long/ ).

**Response:**
```json
{
  "service": "libretranslate",
  "languages": [
    {
      "code": "en",
      "name": "English",
      "targets": ["es", "fr", "tl", "de", "zh", "ja", "ko"]
    }
  ],
  "note": "Each language shows its 'targets' - all languages you can translate from that source"
}
```

## Authentication
- Header: `X-API-Key: my-secret-api-key-123`
- 401 on invalid/missing

## Rate Limiting
- 5 requests/minute per IP (you can configure this part. Set it to "number of tries per second/minute/hour/day)
- 429 on exceed
- In-memory tracking

## Error Handling

| Code | Error | Cause |
|------|-------|-------|
| 401 | Unauthorized | Bad API key |
| 429 | Rate Limit | Too many requests |
| 503 | Service Unavailable | LibreTranslate down |
| 504 | Timeout | LibreTranslate slow |

## Testing

**cURL Examples:**
```bash
# Health
curl -H "X-API-Key: my-secret-api-key-123" http://localhost:8000/health

# Translate Spanish
curl -X POST -H "X-API-Key: my-secret-api-key-123" -H "Content-Type: application/json" -d '{"text":"Hello","target_language":"es"}' http://localhost:8000/translate

# Simplified Version of Languages List
curl -H "X-API-Key: my-secret-api-key-123" http://localhost:8000/languages

# Detailed Languages List (with translation targets)
curl -H "X-API-Key: my-secret-api-key-123" http://localhost:8000/languages/detailed
```
**or just use Swagger UI**
http://127.0.0.1:8000/docs

## Project Structure
```
syscall_translation_API/
├── main_libretranslate.py    # FastAPI app
├── requirements.txt          # Deps
├── README.md                 # This file
├── .env                      # API key
├── pyrightconfig.json        # Type checking
└── venv/                     # Virtual env
```

## Challenges & Solutions/ Troubleshooting

1. **Pyright Warnings**: Added `pyrightconfig.json`, null checks.
2. **Python 3.13 Compat**: Used latest httpx/LibreTranslate.
3. **LibreTranslate Download**: Documented one-time setup.
4. **Two Terminals**: One to run the translation service and one to run the API.
5. **googletrans Avoided**: Compat issues with googletrans, thus I stuck with LibreTranslate.

| Problem | Possible Cause | Solution |
|---------|----------------|----------|
| **`LibreTranslate not running` error** | LibreTranslate service not started | Run `libretranslate --host 127.0.0.1 --port 5000` in Terminal 1 |
| **`Connection refused` error** | Wrong port or service not running | Check Terminal 1 shows `Running on http://127.0.0.1:5000` |
| **401 Unauthorized** | Wrong or missing API key | Verify `.env` file contains `API_KEY=my-secret-api-key-123`. Check this part, either you did not put anything or you may have put a different API Key |
| **429 Rate Limit Exceeded** | Too many requests in 1 minute | Wait 60 seconds before trying again |
| **Translation takes too long (first run)** | Downloading language models | Wait 30-60 minutes for models to download (one-time only) |
| **Translation takes too long (after first run)** | LibreTranslate may be frozen | Restart Terminal 1 (Ctrl+C, then run again) |
| **ModuleNotFoundError** | Missing Python packages | Run `pip install -r requirements.txt` |
| **`uvicorn: command not found`** | Virtual environment not activated | Run `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Mac/Linux) |
| **Port 8000 already in use** | Another app using the port | Change port: `uvicorn main_libretranslate:app --port 8001` |
| **Port 5000 already in use** | Another app using the port | Change port: `libretranslate --host 127.0.0.1 --port 5001` |
| **Swagger UI not loading** | FastAPI not running | Check Terminal 2 shows `Application startup complete` |
| **Pyright warnings in Sublime** | Type checker warnings (harmless) | Create `pyrightconfig.json` or ignore them |
| **`No module named 'cgi'` error** | Python 3.13 incompatibility | We use LibreTranslate (compatible) instead of googletrans |
| **Models not downloading** | Internet connection issue | Check internet connection, restart LibreTranslate |

## Team Members & Contributions

| Member | Role | Contributions |
|--------|------|---------------|
| Marcos, Russel E. | Student | Complete end-to-end development of the Translation API|
| Martin, Aiza |  |  |
| Omipet, Sairen |  |  |
| Raras, Debbie |  |  |
| Ngados, Alma |  |  |
| Dawayen, Jan | | |

## License
Educational project for ITP 322 - Systems Integration and Architecture 2.

