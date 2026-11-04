# ContractIQ — Production Deployment Guide 🚀

This document provides step-by-step instructions for deploying the **ContractIQ Legal Intelligence Platform** into production environments.

---

## 🏗️ Architecture Overview

ContractIQ is structured as a cloud-native, decoupled full-stack application:

```
                      ┌───────────────────────────┐
                      │    Client Browser / SPA   │
                      └─────────────┬─────────────┘
                                    │
                                    ▼
                      ┌───────────────────────────┐
                      │   Nginx (Port 80 / 443)   │
                      │  - Gzip Compression       │
                      │  - Static Asset Caching   │
                      │  - Reverse Proxy (/api/)  │
                      └─────────────┬─────────────┘
                                    │
                                    ▼
                      ┌───────────────────────────┐
                      │  FastAPI Backend (:8000)  │
                      │  - Uvicorn Multi-Worker   │
                      │  - LangGraph Workflows    │
                      │  - JWT Auth & Guest TTL   │
                      └──────┬───────┬───────┬────┘
                             │       │       │
              ┌──────────────┘       │       └──────────────┐
              ▼                      ▼                      ▼
┌──────────────────────────┐ ┌───────────────┐ ┌──────────────────────────┐
│ PostgreSQL (Neon / RDS)  │ │ Qdrant Cloud  │ │  Cloudinary Storage      │
│ Relational Data & Users  │ │ Vector Search │ │  Original PDF Contracts  │
└──────────────────────────┘ └───────────────┘ └──────────────────────────┘
```

---

## ⚡ Deployment Options

### Option 1: Docker Compose (Single VM / VPS / Droplet)

Recommended for AWS EC2, DigitalOcean Droplets, Hetzner, or private Linux servers.

#### Prerequisites
- Docker (v24.0+)
- Docker Compose (v2.20+)

#### Steps
1. **Clone repository onto the server:**
   ```bash
   git clone <your-repo-url>
   cd legal-contract-analyzer
   ```

2. **Configure environment variables:**
   ```bash
   cp .env.example backend/.env
   nano backend/.env
   ```
   *Fill in your database URL, Qdrant Cloud URL, and LLM API keys.*

3. **Launch production containers:**
   ```bash
   docker compose -f docker-compose.prod.yml up -d --build
   ```

4. **Verify container health:**
   ```bash
   docker compose -f docker-compose.prod.yml ps
   curl -f http://localhost:8000/health
   ```

5. **Configure Domain & SSL (Certbot):**
   ```bash
   sudo apt-get install certbot python3-certbot-nginx
   sudo certbot --nginx -d yourdomain.com
   ```

---

### Option 2: Cloud PaaS Deployment (Render / Railway / Fly.io)

ContractIQ is designed for seamless deployment across modern container clouds.

#### Backend Deployment (FastAPI):
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2`
- **Health Check Path:** `/health`
- **Environment Variables:**
  - `DATABASE_URL`: `postgresql+asyncpg://...` (Ensure `ssl=require` for Neon/RDS)
  - `QDRANT_URL`: `https://your-cluster.qdrant.io:6333`
  - `QDRANT_API_KEY`: `<your_key>`
  - `OPENAI_API_KEY`: `sk-...`
  - `GROQ_API_KEY`: `gsk_...`
  - `CLOUDINARY_CLOUD_NAME`: `<cloud_name>`
  - `CLOUDINARY_API_KEY`: `<api_key>`
  - `CLOUDINARY_API_SECRET`: `<api_secret>`
  - `JWT_SECRET`: `<secure-random-32-char-string>`

#### Frontend Deployment (Vercel / Netlify / Cloudflare Pages):
- **Framework Preset:** Vite
- **Root Directory:** `frontend`
- **Build Command:** `npm run build`
- **Output Directory:** `dist`
- **Environment Variables:**
  - `VITE_API_URL`: `https://api.yourdomain.com`

---

## 🛡️ Production Security Checklist

| Check | Requirement | Implemented |
| :--- | :--- | :---: |
| **Authentication** | Passwords hashed with standard bcrypt / argon2 | ✅ |
| **JWT Tokens** | Signed with HMAC-SHA256, expiration enforced | ✅ |
| **IDOR Protection** | Strict owner-check on all contract retrieval & deletion | ✅ |
| **Guest Data TTL** | Expired guest contracts purged every 15 minutes | ✅ |
| **CORS Policy** | Restricted to authorized production frontend domains | ✅ |
| **Reverse Proxy** | Nginx buffers large uploads (max 50MB) and strips internal headers | ✅ |
| **Log Rotation** | Docker logs capped at 20MB per file with max 5 backups | ✅ |

---

## 🧪 Post-Deployment Verification

Run the automated smoke test script after deployment:

```bash
# 1. Verify healthcheck returns HTTP 200
curl -f https://api.yourdomain.com/health

# 2. Verify CORS headers
curl -I -X OPTIONS https://api.yourdomain.com/api/v1/contracts \
  -H "Origin: https://yourdomain.com" \
  -H "Access-Control-Request-Method: GET"

# 3. Test legal search index
curl -X POST https://api.yourdomain.com/api/v1/legal/search \
  -H "Content-Type: application/json" \
  -d '{"query": "non-compete agreement enforceability", "document_type": "ALL", "top_k": 3}'
```

