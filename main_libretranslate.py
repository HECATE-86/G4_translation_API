from fastapi import FastAPI, HTTPException, Depends, Request, UploadFile, File, Form
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
import httpx
import os
from datetime import datetime, timedelta
from collections import defaultdict
from dotenv import load_dotenv
from typing import Optional, List

# CONFIGURATION & ENVIRONMENT VARIABLES

load_dotenv()

API_KEY = os.getenv("API_KEY", "my-secret-api-key-123")
PUBLIC_RATE_LIMIT = 30    
GUEST_RATE_LIMIT = 5      
AUTH_RATE_LIMIT = 10      

# REQUEST TRACKING (For Rate Limiting)

public_request_counts = defaultdict(list)
guest_request_counts = defaultdict(list)
auth_request_counts = defaultdict(list)

# FASTAPI INITIALIZATION

app = FastAPI(
    title="Translation API - LibreTranslate",
    description="API using LibreTranslate with tiered access",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# AUTHENTICATION SETUP

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_auth(api_key: str = Depends(api_key_header)):
   
    if not api_key or api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API Key")
    return True

# RATE LIMITING FUNCTIONS

def rate_limit_public(request: Request):

    client_ip = request.client.host if request.client else "unknown"
    now = datetime.now()
    minute_ago = now - timedelta(minutes=1)
    
    counter = public_request_counts
    
    # Clean old requests
    counter[client_ip] = [ts for ts in counter[client_ip] if ts > minute_ago]
    
    if len(counter[client_ip]) >= PUBLIC_RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Public endpoints limited to {PUBLIC_RATE_LIMIT} requests per minute. Please wait before trying again."
        )
    
    counter[client_ip].append(now)

def rate_limit_guest(request: Request):

    client_ip = request.client.host if request.client else "unknown"
    now = datetime.now()
    day_ago = now - timedelta(days=1)
    
    counter = guest_request_counts
    
    # Clean old requests
    counter[client_ip] = [ts for ts in counter[client_ip] if ts > day_ago]
    
    if len(counter[client_ip]) >= GUEST_RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Guest translation limited to {GUEST_RATE_LIMIT} requests per day. Get an API key for higher limits."
        )
    
    counter[client_ip].append(now)

def rate_limit_auth(request: Request):
    
    client_ip = request.client.host if request.client else "unknown"
    now = datetime.now()
    minute_ago = now - timedelta(minutes=1)
    
    counter = auth_request_counts
    
    # Clean old requests
    counter[client_ip] = [ts for ts in counter[client_ip] if ts > minute_ago]
    
    if len(counter[client_ip]) >= AUTH_RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Authenticated users limited to {AUTH_RATE_LIMIT} requests per minute. Please wait before trying again."
        )
    
    counter[client_ip].append(now)

# PYDANTIC MODELS (Request/Response Validation)

# GUEST MODEL 
class GuestTranslateRequest(BaseModel):
    text: str
    target_language: str
    source_language: str  

# AUTHENTICATED MODEL - Has auto-detection and advanced features
class AuthTranslateRequest(BaseModel):
    text: str
    target_language: str
    source_language: str = "auto"
    format: str = "text"
    alternatives: Optional[int] = None

# Shared response model
class TranslateResponse(BaseModel):
    original_text: str
    translated_text: str
    source_language: str
    target_language: str
    alternatives: Optional[List[str]] = None
    service: str = "libretranslate"

# PUBLIC ENDPOINTS (No Authentication)

@app.get("/")
async def root():

    return {
        "message": "Translation API - LibreTranslate",
        "service": "LibreTranslate (self-hosted)",
        "docs": "/docs",
        "status": "running",
        "rate_limits": {
            "public_endpoints": "30 requests/minute",
            "guest_translation": "5 requests/day",
            "authenticated_endpoints": "10 requests/minute"
        },
        "note": "Use /guest/translate for no-auth translation. Add X-API-Key header for authenticated endpoints."
    }

@app.get("/health")
async def health(request: Request):

    rate_limit_public(request)
    
    libretranslate_ok = False
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get("http://localhost:5000/", timeout=2.0)
            libretranslate_ok = r.status_code == 200
    except:
        pass
    
    return {
        "status": "healthy",
        "libretranslate": "running" if libretranslate_ok else "not running"
    }

@app.get("/languages")
async def get_languages(request: Request):

    rate_limit_public(request)
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:5000/languages", timeout=10.0)
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="Could not fetch languages. Make sure LibreTranslate is running on port 5000.")
            
            return {
                "service": "libretranslate",
                "languages": [{"code": lang["code"], "name": lang["name"]} for lang in response.json()]
            }
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="LibreTranslate not running. Start it with: libretranslate --host 127.0.0.1 --port 5000")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get languages: {str(e)}")

@app.get("/languages/detailed")
async def get_languages_detailed(request: Request):
   
    rate_limit_public(request)
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:5000/languages", timeout=10.0)
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="Could not fetch languages. Make sure LibreTranslate is running on port 5000.")
            
            return {
                "service": "libretranslate",
                "languages": response.json()
            }
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="LibreTranslate not running. Start it with: libretranslate --host 127.0.0.1 --port 5000")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get languages: {str(e)}")

@app.post("/detect")
async def detect_language(text: str, req: Request):
    
    rate_limit_public(req)
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post("http://localhost:5000/detect", json={"q": text}, timeout=10.0)
            
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="Language detection failed. Make sure LibreTranslate is running and text is not empty.")
            
            result = response.json()
            if result and len(result) > 0:
                return {
                    "language": result[0].get("language", "unknown"),
                    "confidence": result[0].get("confidence", 0)
                }
            return {"language": "unknown", "confidence": 0}
            
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="LibreTranslate not running. Start it with: libretranslate --host 127.0.0.1 --port 5000")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Detection failed: {str(e)}")

# GUEST ENDPOINTS (No Authentication)

@app.post("/guest/translate")
async def guest_translate(request: GuestTranslateRequest, req: Request):
    
    rate_limit_guest(req)
    
    try:
        async with httpx.AsyncClient() as client:
            payload = {
                "q": request.text,
                "source": request.source_language,
                "target": request.target_language,
                "format": "text"
            }
            
            response = await client.post("http://localhost:5000/translate", json=payload, timeout=30.0)
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=500, 
                    detail=f"LibreTranslate service error (HTTP {response.status_code}). Check if source/target languages are valid. Use GET /languages to see supported languages."
                )
            
            result = response.json()
            
            return TranslateResponse(
                original_text=request.text,
                translated_text=result.get("translatedText", ""),
                source_language=request.source_language,
                target_language=request.target_language,
                alternatives=None,
                service="libretranslate (guest)"
            )
            
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Translation request timed out. The text may be too long or LibreTranslate is slow. Try again with shorter text.")
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="LibreTranslate not running. Start it with: libretranslate --host 127.0.0.1 --port 5000")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Translation failed: {str(e)}")

# AUTHENTICATED ENDPOINTS (API Key Required)

@app.post("/translate", response_model=TranslateResponse)
async def translate_text(
    request: AuthTranslateRequest, 
    req: Request, 
    authenticated: bool = Depends(require_auth)
):
    
    rate_limit_auth(req)
    
    try:
        async with httpx.AsyncClient() as client:
            payload = {
                "q": request.text,
                "source": request.source_language,
                "target": request.target_language,
                "format": request.format
            }
            if request.alternatives:
                payload["alternatives"] = request.alternatives
            
            response = await client.post("http://localhost:5000/translate", json=payload, timeout=30.0)
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=500, 
                    detail=f"LibreTranslate service error (HTTP {response.status_code}). Check if source/target languages are valid. Use GET /languages to see supported languages."
                )
            
            result = response.json()
            
            return TranslateResponse(
                original_text=request.text,
                translated_text=result.get("translatedText", ""),
                source_language=result.get("detectedLanguage", {}).get("language", request.source_language),
                target_language=request.target_language,
                alternatives=result.get("alternatives"),
                service="libretranslate"
            )
            
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Translation request timed out. The text may be too long or LibreTranslate is slow. Try again with shorter text.")
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="LibreTranslate not running. Start it with: libretranslate --host 127.0.0.1 --port 5000")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Translation failed: {str(e)}")

# FILE TRANSLATION (API Key Required - 10 req/min)

@app.post("/translate/file")
async def translate_file(
    file: UploadFile = File(...),
    target_language: str = Form(...),
    source_language: str = Form("auto"),
    req: Request = None,
    authenticated: bool = Depends(require_auth)
):

    rate_limit_auth(req)
    
    try:
        content = await file.read()
        
        try:
            text_content = content.decode('utf-8')
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="File must be a text file with UTF-8 encoding. Supported formats: .txt")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:5000/translate",
                json={
                    "q": text_content,
                    "source": source_language,
                    "target": target_language,
                    "format": "text"
                },
                timeout=60.0
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=500, 
                    detail=f"File translation failed (HTTP {response.status_code}). Check if source/target languages are valid. Use GET /languages to see supported languages."
                )
            
            result = response.json()
            
            return {
                "original_filename": file.filename,
                "translated_text": result.get("translatedText", ""),
                "source_language": result.get("detectedLanguage", {}).get("language", source_language),
                "target_language": target_language,
                "service": "libretranslate"
            }
            
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="File translation timed out. The file may be too large. Try a smaller file (max 5MB recommended).")
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="LibreTranslate not running. Start it with: libretranslate --host 127.0.0.1 --port 5000")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File translation failed: {str(e)}")