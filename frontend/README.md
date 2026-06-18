# Sports Card Kickoff — Frontend

Next.js 16 (App Router, TypeScript, Tailwind v4) frontend for the Sports Card
Kickoff search engine. **Phase 1** is the public, SEO-friendly search experience
built on the public catalog API.

## What's here (Phase 1)

- **Home** (`/`) — natural-language search box with examples.
- **Results** (`/search?q=...`) — calls `GET /catalog/search/`, shows the
  *interpreted query* chips and a grid of cards with market value.
- **Card detail** (`/cards/[id]`) — server-rendered (good for SEO) with
  `generateMetadata`; shows market summary, a **price history chart**, a
  by-grade breakdown, and a recent-comps table with source (eBay/130Point/
  COMC/Goldin) and type (Sold/Listing/Auction) badges.

Data is fetched **server-side** (Next server → Django), so the backend's CORS
config does not need changing for Phase 1.

## Run

```bash
# 1. Start the backend (from the repo root) so the API is at :8000
#    python manage.py runserver

# 2. Frontend
cd frontend
npm install
npm run dev        # http://localhost:3000
```

## Configuration

| Env var | Default | Purpose |
|---------|---------|---------|
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000/api/v1` | Base URL of the DRF API |

Create `frontend/.env.local` to override:

```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
```

## Build

```bash
npm run build && npm start
```

## Next phases

- **Phase 2** — auth (JWT), watchlist, price alerts, portfolio, and real-time
  notifications over the `ws/notifications/` WebSocket. This will require adding
  the frontend origin to the backend `CORS_ALLOWED_ORIGINS`.
- **Phase 3** — SEO/growth: OpenGraph images, sitemaps, PWA.
