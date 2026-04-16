from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import httpx
import os

app = FastAPI()

# Serve static files
app.mount("/static", StaticFiles(directory="."), name="static")

@app.get("/")
async def serve_index():
    return FileResponse("index.html")

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434")
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "mistral")

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: list[Message]
    model: str = DEFAULT_MODEL

class ChatResponse(BaseModel):
    role: str
    content: str

@app.get("/health")
async def health():
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{OLLAMA_API_URL}/api/tags", timeout=5.0)
            return {"status": "healthy", "ollama_connected": response.status_code == 200}
    except:
        return {"status": "unhealthy", "ollama_connected": False}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{OLLAMA_API_URL}/v1/chat/completions",
                json={
                    "model": request.model,
                    "messages": [{"role": msg.role, "content": msg.content} for msg in request.messages],
                    "max_tokens": 1000,
                    "temperature": 0.7
                },
                timeout=60.0
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail="Ollama API error")
            
            data = response.json()
            
            if "error" in data:
                raise HTTPException(status_code=400, detail=data["error"])
            
            assistant_message = data["choices"][0]["message"]["content"]
            return ChatResponse(role="assistant", content=assistant_message)
            
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Request timeout")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
