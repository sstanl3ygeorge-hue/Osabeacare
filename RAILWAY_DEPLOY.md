# Osabeacare - Railway Deployment Guide

## Quick Start

### 1. Create Railway Project

```bash
# Option A: Railway CLI
railway login
railway init

# Option B: Railway Dashboard
# Go to https://railway.app/new
# Select "Deploy from GitHub repo"
# Choose: sstanl3ygeorge-hue/Osabeacare
```

### 2. Add MongoDB Service

1. In Railway dashboard, click **"+ New"**
2. Select **"Database"** → **"MongoDB"**
3. Railway auto-creates `MONGO_URL` variable

### 3. Create Backend Service

1. Click **"+ New"** → **"GitHub Repo"**
2. Select `Osabeacare` repo
3. Set **Root Directory**: `backend`
4. Add environment variables:

```
MONGO_URL=${{MongoDB.MONGO_URL}}
DB_NAME=osabeacare_prod
JWT_SECRET=<generate-secure-32-char-string>
CORS_ORIGINS=https://<frontend-service>.up.railway.app
RESEND_API_KEY=<your-resend-key>
SENDER_EMAIL=Osabea Recruitment Team <recruitment@osabeacares.co.uk>
REPLY_TO_EMAIL=info@osabeacaresolutions.co.uk
ADMIN_EMAIL=admin@osabea.care
EMERGENT_LLM_KEY=<your-emergent-key>
```

5. Set **Start Command**: `uvicorn server:app --host 0.0.0.0 --port $PORT`

### 4. Create Frontend Service

1. Click **"+ New"** → **"GitHub Repo"**
2. Select `Osabeacare` repo
3. Set **Root Directory**: `frontend`
4. Add environment variables:

```
REACT_APP_BACKEND_URL=https://<backend-service>.up.railway.app
```

5. Set **Build Command**: `yarn install && yarn build`
6. Set **Start Command**: `npx serve -s build -l $PORT`

### 5. Generate Domain URLs

For each service:
1. Go to **Settings** → **Networking**
2. Click **"Generate Domain"**
3. Update `CORS_ORIGINS` (backend) and `REACT_APP_BACKEND_URL` (frontend) with actual URLs

---

## Service Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Railway Project                       │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐   ┌──────────────┐   ┌─────────────┐ │
│  │   MongoDB    │   │   Backend    │   │  Frontend   │ │
│  │   Service    │◄──│   (FastAPI)  │◄──│   (React)   │ │
│  │              │   │   :$PORT     │   │   :$PORT    │ │
│  └──────────────┘   └──────────────┘   └─────────────┘ │
│         │                  │                  │         │
│         │           /api/* routes      Static build     │
│         │                  │                  │         │
│  mongodb://...    backend.up.railway   frontend.up...   │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## Environment Variables Reference

### Backend Service

| Variable | Required | Description |
|----------|----------|-------------|
| `MONGO_URL` | Yes | MongoDB connection string |
| `DB_NAME` | Yes | Database name |
| `JWT_SECRET` | Yes | JWT signing secret (min 32 chars) |
| `CORS_ORIGINS` | Yes | Frontend URL for CORS |
| `RESEND_API_KEY` | Yes | Email service API key |
| `SENDER_EMAIL` | Yes | From email address |
| `REPLY_TO_EMAIL` | Yes | Reply-to email |
| `ADMIN_EMAIL` | Yes | Admin notification email |
| `EMERGENT_LLM_KEY` | Yes | LLM integration key |

### Frontend Service

| Variable | Required | Description |
|----------|----------|-------------|
| `REACT_APP_BACKEND_URL` | Yes | Backend API URL (with https://) |

---

## Post-Deployment Checklist

- [ ] MongoDB service running
- [ ] Backend health check: `curl https://<backend>.up.railway.app/api/health`
- [ ] Frontend loads: `https://<frontend>.up.railway.app`
- [ ] Login works with test credentials
- [ ] CORS configured correctly (no console errors)
- [ ] Email sending works (test reference request)

---

## Troubleshooting

### Backend won't start
```bash
# Check logs in Railway dashboard
# Common issues:
# - Missing MONGO_URL
# - Invalid JWT_SECRET
# - Port not using $PORT variable
```

### CORS errors
```bash
# Ensure CORS_ORIGINS matches exactly:
# - Include https://
# - No trailing slash
# - Must match frontend domain exactly
```

### MongoDB connection fails
```bash
# Use Railway's variable reference:
MONGO_URL=${{MongoDB.MONGO_URL}}
# NOT a hardcoded string
```

---

## Costs Estimate

| Service | Estimated Monthly |
|---------|------------------|
| Backend | ~$5-10 |
| Frontend | ~$2-5 |
| MongoDB | ~$5-15 (depends on storage) |
| **Total** | **~$12-30/month** |

Railway offers $5 free credit for new accounts.
