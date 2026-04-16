"""
OPTION B: Hosted Model API (Together AI)
FastAPI backend that connects to Together AI for Mistral models
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import httpx
import os
import json

app = FastAPI(title="Chatbot API - Together AI")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your Vercel domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY", "")
TOGETHER_MODEL = os.getenv("TOGETHER_MODEL", "mistralai/Mistral-7B-Instruct-v0.2")
API_KEY = os.getenv("API_KEY", "")  # Optional API key for security

if not TOGETHER_API_KEY:
    raise ValueError("TOGETHER_API_KEY environment variable is required")

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: list[Message]
    model: str = TOGETHER_MODEL
    stream: bool = False
    api_key: str = ""  # Optional for security

class ChatResponse(BaseModel):
    role: str
    content: str

@app.get("/health")
async def health():
    """Health check endpoint"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Simple test call to Together AI
            response = await client.get(
                "https://api.together.xyz/v1/models",
                headers={"Authorization": f"Bearer {TOGETHER_API_KEY}"}
            )
            return {
                "status": "healthy",
                "together_connected": response.status_code == 200,
                "model": TOGETHER_MODEL
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "together_connected": False,
            "error": str(e)
        }

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Non-streaming chat endpoint
    POST /chat
    """
    # Optional API key validation
    if API_KEY and request.api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                "https://api.together.xyz/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {TOGETHER_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": request.model,
                    "messages": [{"role": msg.role, "content": msg.content} for msg in request.messages],
                    "max_tokens": 2000,
                    "temperature": 0.7,
                    "stream": False
                }
            )
            
            if response.status_code != 200:
                error_data = response.json()
                raise HTTPException(
                    status_code=response.status_code,
                    detail=error_data.get("error", {}).get("message", "Together AI error")
                )
            
            data = response.json()
            
            if "error" in data:
                raise HTTPException(status_code=400, detail=data["error"])
            
            assistant_message = data["choices"][0]["message"]["content"]
            return ChatResponse(role="assistant", content=assistant_message)
            
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Request timeout")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Streaming chat endpoint
    POST /chat/stream
    """
    # Optional API key validation
    if API_KEY and request.api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    async def generate():
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    "https://api.together.xyz/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {TOGETHER_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": request.model,
                        "messages": [{"role": msg.role, "content": msg.content} for msg in request.messages],
                        "max_tokens": 2000,
                        "temperature": 0.7,
                        "stream": True
                    }
                ) as response:
                    if response.status_code != 200:
                        yield f"data: {json.dumps({'error': 'Together AI error'})}\n\n"
                        return
                    
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                yield "data: [DONE]\n\n"
                                break
                            try:
                                data = json.loads(data_str)
                                if "choices" in data and len(data["choices"]) > 0:
                                    delta = data["choices"][0].get("delta", {})
                                    if "content" in delta:
                                        yield f"data: {json.dumps({'content': delta['content']})}\n\n"
                            except json.JSONDecodeError:
                                continue
                                
        except httpx.TimeoutException:
            yield f"data: {json.dumps({'error': 'Request timeout'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
