# BrandForge - AI Image Generation Platform

AI-powered image generation platform for brand-compliant marketing assets. Built for Betano's 19+ market operations with integrated brand guidelines enforcement, QA scoring, and multi-market legal compliance.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (React)                      │
│  Chat Interface │ Editor (Canvas) │ Templates │ Admin    │
├─────────────────────────────────────────────────────────┤
│                   Backend API (FastAPI)                   │
│  Auth │ Images │ Templates │ Brand │ Markets │ Integration│
├──────────┬──────────┬───────────┬───────────────────────┤
│ AI Layer │ QA Engine│ Template  │ Market Service         │
│ Google   │ Color    │ Analysis  │ Legal Compliance       │
│ OpenAI   │ Layout   │ Variation │ Data Partitioning      │
│ Stability│ Logo     │ Generator │ Storage Isolation      │
├──────────┴──────────┴───────────┴───────────────────────┤
│ PostgreSQL │ Redis │ MinIO/S3 │ Celery Workers          │
└─────────────────────────────────────────────────────────┘
```

## Key Features

- **AI Image Generation** — Multi-provider support (Google Imagen, OpenAI DALL-E, Stability AI) with layered output
- **Brand Guidelines Engine** — Automated enforcement of colors, typography, logo placement, imagery style
- **QA Scoring (0-100)** — Automated scoring across 6 categories: color, composition, logo, typography, legal, content
- **Template System** — Upload images for AI analysis, generate variations, structured layouts with safe areas
- **19-Market Support** — Per-market legal disclaimers, content restrictions, data partitioning, storage isolation
- **Layer Editor** — Canvas-based editor with layer management, effects, safe area visualization
- **Export System** — 22+ dimension presets (email, story, push, slider, casino, etc.) in PNG/JPG/WebP/PDF
- **Integration API** — REST API with API key auth for external platform integration (Campaign Builder)
- **User Roles** — Viewer, Creator, Admin, Super Admin with market-scoped access
- **Audit Logging** — Full action history, usage metrics, cost tracking
- **Feedback Loop** — Star ratings and thumbs up/down feed back into generation quality

## Dimension Presets

| Category | Preset | Dimensions |
|----------|--------|-----------|
| Newsletter | Single | 600x735 |
| Newsletter | Visual | 525x675 |
| Newsletter | Double | 450x450 |
| Newsletter | Half | 450x225 |
| Newsletter | Quarter | 225x300 |
| Story | Enhanced Thumb | 471x330 |
| Story | Background | 1862x2778 |
| Promotional | Slider | 2048x1152 |
| Promotional | Push | 458x258 |
| Promotional | PM | 1126x260 |
| Social | Story | 1080x1920 |
| Social | Post Square | 1080x1080 |
| Promo | Banner | 1200x628 |
| Casino | Thumbnail | 240x240 |

## Tech Stack

- **Frontend**: React 18 + TypeScript + Vite + Tailwind CSS + Fabric.js
- **Backend**: Python 3.11 + FastAPI + SQLAlchemy 2.0 (async) + Pydantic
- **Database**: PostgreSQL 16 with market-partitioned data
- **Cache/Queue**: Redis + Celery for async image generation
- **Storage**: S3-compatible (MinIO dev / AWS S3 / GCP Cloud Storage)
- **Auth**: OAuth2/OIDC (Kaizen SSO) + JWT fallback
- **AI**: Google Imagen, OpenAI DALL-E 3, Stability AI (pluggable)

## Quick Start

```bash
# 1. Clone and configure
cp .env.example .env
# Edit .env with your AI provider keys

# 2. Start all services
docker-compose up -d

# 3. Access
# Frontend:  http://localhost:3000
# Backend:   http://localhost:8000
# API Docs:  http://localhost:8000/docs
# MinIO:     http://localhost:9001
```

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── ai/              # AI provider abstraction (Google, OpenAI, Stability)
│   │   ├── api/             # FastAPI routes (auth, images, templates, markets, brand, editor, integration)
│   │   ├── auth/            # OAuth2/OIDC, JWT, RBAC
│   │   ├── brand/           # Guidelines engine, QA scoring, feedback loop
│   │   ├── models/          # SQLAlchemy models
│   │   ├── schemas/         # Pydantic request/response models
│   │   ├── services/        # Business logic (generation, templates, markets, storage, export)
│   │   └── workers/         # Celery async tasks
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/      # React components (Chat, Editor, Templates, Brand, Export, Markets)
│   │   ├── pages/           # Page views (Dashboard, Generate, Editor, Templates, Brand, Markets, Admin)
│   │   ├── api/             # API client with auth interceptor
│   │   ├── stores/          # Zustand state management
│   │   ├── types/           # TypeScript interfaces
│   │   └── utils/           # Dimension presets, helpers
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
└── .env.example
```

## Integration API

For external platforms (e.g., Campaign Builder):

```bash
# Generate image
curl -X POST http://localhost:8000/api/v1/integration/generate \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Sports promo banner", "market_id": "...", "preset": "Promo Banner"}'

# Check status
curl http://localhost:8000/api/v1/integration/status/{job_id} \
  -H "X-API-Key: your-api-key"
```

## Market Configuration

Each market has isolated:
- **Legal disclaimers** — Auto-applied to all generated images (e.g., Ontario: "18+ Terms & Conditions Apply")
- **Content restrictions** — AI validates prompts against rules (e.g., Ontario: no real tournament trophies)
- **Brand overrides** — Market-specific color/typography/logo adjustments
- **Storage** — Separate storage paths per market for compliance
- **Data partitioning** — Users only access their market's data

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GOOGLE_AI_API_KEY` | Google AI API key (Imagen/Gemini) | At least one AI key |
| `OPENAI_API_KEY` | OpenAI API key (DALL-E 3) | At least one AI key |
| `STABILITY_API_KEY` | Stability AI API key | At least one AI key |
| `OAUTH_CLIENT_ID` | Kaizen SSO client ID | For SSO |
| `OAUTH_CLIENT_SECRET` | Kaizen SSO client secret | For SSO |
| `OAUTH_DISCOVERY_URL` | OIDC discovery URL | For SSO |
| `SECRET_KEY` | JWT signing key | Yes |
| `DATABASE_URL` | PostgreSQL connection string | Yes |
