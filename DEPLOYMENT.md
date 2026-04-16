# Deployment Guide

## OPTION A: Self-hosted Ollama on VPS

### Prerequisites
- VPS with GPU (NVIDIA GPU recommended for Mistral)
- Domain name (optional but recommended)
- SSL certificate (Let's Encrypt recommended)

### Step 1: Set up VPS
1. Rent a GPU VPS (e.g., AWS, DigitalOcean, Lambda Labs, RunPod)
2. Install Ubuntu 20.04 or later
3. Install NVIDIA drivers and CUDA

### Step 2: Install Ollama on VPS
```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull Mistral model
ollama pull mistral

# Start Ollama server (exposed to internet)
ollama serve --host 0.0.0.0 --port 11434
```

### Step 3: Set up Nginx (SSL/Reverse Proxy)
```bash
# Install Nginx
sudo apt install nginx certbot python3-certbot-nginx

# Configure Nginx
sudo nano /etc/nginx/sites-available/ollama
```

Nginx config:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:11434;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/ollama /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Get SSL certificate
sudo certbot --nginx -d your-domain.com
```

### Step 4: Deploy Backend to Vercel
```bash
# Copy backend file
cp backend_option_a.py api/

# Update vercel.json
{
  "version": 2,
  "builds": [
    {
      "src": "api/backend_option_a.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "api/backend_option_a.py"
    }
  ],
  "env": {
    "OLLAMA_API_URL": "https://your-domain.com",
    "OLLAMA_MODEL": "mistral",
    "API_KEY": "your-secret-key"
  }
}
```

### Step 5: Deploy Frontend to Vercel
```bash
# Copy production frontend
cp index_production.html index.html

# Deploy to Vercel
vercel --prod
```

### Step 6: Configure Frontend
- Set backend URL to your Vercel API URL
- Add API key if configured

---

## OPTION B: Hosted Model API (Together AI)

### Prerequisites
- Together AI account (https://together.ai/)
- API key from Together AI
- Vercel account

### Step 1: Get Together AI API Key
1. Sign up at https://together.ai/
2. Go to Settings → API Keys
3. Create new API key
4. Copy the key

### Step 2: Deploy Backend to Vercel
```bash
# Copy backend file
cp backend_option_b.py api/

# Update vercel.json
{
  "version": 2,
  "builds": [
    {
      "src": "api/backend_option_b.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "api/backend_option_b.py"
    }
  ],
  "env": {
    "TOGETHER_API_KEY": "your-together-api-key",
    "TOGETHER_MODEL": "mistralai/Mistral-7B-Instruct-v0.2",
    "API_KEY": "your-secret-key"
  }
}
```

### Step 3: Deploy Frontend to Vercel
```bash
# Copy production frontend
cp index_production.html index.html

# Deploy to Vercel
vercel --prod
```

### Step 4: Configure Frontend
- Set backend URL to your Vercel API URL
- Add API key if configured

---

## API Endpoint Structure

### POST /chat
Non-streaming chat endpoint

**Request:**
```json
{
  "messages": [
    {"role": "user", "content": "Hello"}
  ],
  "model": "mistral",
  "stream": false,
  "api_key": "optional-api-key"
}
```

**Response:**
```json
{
  "role": "assistant",
  "content": "Hello! How can I help you?"
}
```

### POST /chat/stream
Streaming chat endpoint

**Request:**
```json
{
  "messages": [
    {"role": "user", "content": "Hello"}
  ],
  "model": "mistral",
  "stream": true,
  "api_key": "optional-api-key"
}
```

**Response:** Server-Sent Events (SSE)
```
data: {"content": "Hello"}
data: {"content": "!"}
data: {"content": " How"}
data: {"content": " can"}
data: {"content": " I"}
data: {"content": " help"}
data: {"content": " you"}
data: {"content": "?"}
data: [DONE]
```

### GET /health
Health check endpoint

**Response:**
```json
{
  "status": "healthy",
  "ollama_connected": true,
  "model": "mistral"
}
```

---

## Environment Variables

### OPTION A (.env.option_a)
```
OLLAMA_API_URL=https://your-ollama-server.com
OLLAMA_MODEL=mistral
API_KEY=your-secret-api-key-here
```

### OPTION B (.env.option_b)
```
TOGETHER_API_KEY=your-together-api-key-here
TOGETHER_MODEL=mistralai/Mistral-7B-Instruct-v0.2
API_KEY=your-secret-api-key-here
```

---

## Security Considerations

1. **API Key Protection**
   - Never commit API keys to git
   - Use environment variables
   - Rotate keys regularly

2. **CORS Configuration**
   - In production, specify your Vercel domain
   - Don't use `allow_origins=["*"]` in production

3. **Rate Limiting**
   - Implement rate limiting on backend
   - Use API keys for user authentication

4. **SSL/TLS**
   - Always use HTTPS in production
   - Use valid SSL certificates

---

## Error Handling

The backend includes:
- Timeout handling (120s default)
- HTTP error handling
- JSON parsing errors
- API validation errors
- Graceful degradation

Frontend includes:
- Network error handling
- Timeout detection
- User-friendly error messages
- Retry capability (manual)

---

## Cost Comparison

### OPTION A: Self-hosted
- VPS cost: $50-200/month (GPU server)
- Maintenance: High
- Control: Full
- Scalability: Manual
- **Total: $50-200/month**

### OPTION B: Together AI
- API cost: $0.0002/1K tokens (Mistral)
- Maintenance: None
- Control: Limited
- Scalability: Automatic
- **Total: Pay per usage (~$10-50/month for typical usage)**
