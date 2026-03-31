from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
import httpx
import os
from datetime import datetime, timedelta
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY", "my-secret-api-key-123")
RATE_LIMIT = 5

request_counts = defaultdict(list)
    
app = FastAPI(
    title="Translation API - LibreTranslate",
    description="API using LibreTranslate (self-hosted translation service)",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

api_key_header = APIKeyHeader(name="X-API-Key")

def verify_api_key(api_key: str = Depends(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return api_key

def rate_limit(request: Request):
    client_ip = request.client.host if request.client else "unknown"
    now = datetime.now()
    minute_ago = now - timedelta(minutes=1)
    
    # Clean old requests
    request_counts[client_ip] = [
        timestamp for timestamp in request_counts[client_ip]
        if timestamp > minute_ago
    ]
    
    # Check limit
    if len(request_counts[client_ip]) >= RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=f"Naughty Boy, Rate limit exceeded. Maximum {RATE_LIMIT} requests per minute."
        )
    
    request_counts[client_ip].append(now)

class TranslateRequest(BaseModel):
    text: str
    target_language: str
    source_language: str = "auto"

class TranslateResponse(BaseModel):
    original_text: str
    translated_text: str
    source_language: str
    target_language: str
    service: str = "libretranslate"

@app.get("/")
async def root():
    return {
        "message": "Translation API - LibreTranslate",
        "service": "LibreTranslate (self-hosted)",
        "docs": "/docs",
        "status": "running"
    }

@app.get("/health")
async def health():
    libretranslate_ok = False
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get("http://localhost:5000/", timeout=2.0)
            libretranslate_ok = r.status_code == 200
    except:
        pass
    
    return {
        "status": "healthy",
        "libretranslate": "running" if libretranslate_ok else "not running (start with: libretranslate --host 127.0.0.1 --port 5000)"
    }

@app.post("/translate", response_model=TranslateResponse)
async def translate_text(
    request: TranslateRequest,
    api_key: str = Depends(verify_api_key),
    rate_limit_check: None = Depends(rate_limit)
):

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:5000/translate",
                json={
                    "q": request.text,
                    "source": request.source_language,
                    "target": request.target_language
                },
                timeout=30.0
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="LibreTranslate service error")
            
            result = response.json()
            
            return TranslateResponse(
                original_text=request.text,
                translated_text=result.get("translatedText", ""),
                source_language=result.get("detectedLanguage", {}).get("language", request.source_language),
                target_language=request.target_language,
                service="libretranslate"
            )
            
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="LibreTranslate timeout")
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="LibreTranslate not running. Start with: libretranslate --host 127.0.0.1 --port 5000")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Translation failed: {str(e)}")


@app.get("/languages")
async def get_languages(api_key: str = Depends(verify_api_key)):
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:5000/languages", timeout=10.0)
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="Could not fetch languages")
            
            full_languages = response.json()
            simplified_languages = [
                {"code": lang["code"], "name": lang["name"]} 
                for lang in full_languages
            ]
            
            return {
                "service": "libretranslate", 
                "languages": simplified_languages,
                "note": "For detailed translation pairs (targets), use /languages/detailed"
            }
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="LibreTranslate not running")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get languages: {str(e)}")

@app.get("/languages/detailed")
async def get_languages_detailed(api_key: str = Depends(verify_api_key)):

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:5000/languages", timeout=10.0)
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="Could not fetch languages")
            
            return {
                "service": "libretranslate", 
                "languages": response.json(),
                "note": "Each language shows its 'targets' - all languages you can translate from that source"
            }
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="LibreTranslate not running")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get languages: {str(e)}")