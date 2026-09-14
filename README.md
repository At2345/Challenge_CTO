# Invoice Booking System (MVP)

Local MVP for automated invoice-to-booking (steps 8c–10) with GREEN/YELLOW/RED governance.

## Setup on a New Machine & Run the Demo

### Prerequisites
- **Git**
- **Docker Desktop** (recommended path — no local Python/Node/Tesseract install needed), **or** Python 3.9+ and Node 20+ for a manual setup
- Windows/macOS/Linux all work; commands below assume Windows PowerShell (swap `venv\Scripts\activate` for `source venv/bin/activate` on macOS/Linux)

> **Windows: `docker` not recognized?** Docker Desktop doesn't always add itself to `PATH`. Add `C:\Program Files\Docker\Docker\resources\bin` to your user `PATH` (Environment Variables → Path → New), then reopen your terminal. Verify with `docker --version`.

### 1. Clone the repo
```
git clone <repo-url>
cd Challenge_CTO
```

### 2. Start the stack (pick one)

**Option A — Docker (recommended, one command):**
```
docker compose up --build
```
Wait for all 3 containers (`mongo`, `backend`, `frontend`) to report `Started`, then seed master data once:
```
docker compose exec backend python data/seed_data.py
```

**Option B — Manual (no Docker):**

First, get MongoDB running on `:27017` via **one** of these (skip if you already have an instance running):
- Install [MongoDB Community Server](https://www.mongodb.com/try/download/community) natively and start the `MongoDB` service, **or**
- Use a free [MongoDB Atlas](https://www.mongodb.com/cloud/atlas/register) cluster and set `MONGO_URI` to its connection string (`set MONGO_URI=mongodb+srv://...`) before starting the backend below, **or**
- If Docker *is* available: `docker run -d -p 27017:27017 --name mongo-invoice mongo:7`

```
# Backend
python -m venv venv
venv\Scripts\activate
pip install --upgrade pip
pip install -e backend
python backend/data/seed_data.py
uvicorn src.main:app --app-dir backend --host 0.0.0.0 --port 8000 --reload
```
In a second terminal:
```
cd frontend
npm install
npm run dev
```

### 3. Generate the sample invoice PDFs
Sample PDFs are generated, not committed to git (`backend/data/sample_invoices/*.pdf` is gitignored). Generate them once (requires `pymupdf`, already in `backend/requirements.txt`):
```
python backend/data/sample_invoices/generate_samples.py
```
If you're on the Docker path and don't have Python installed on the host, run it inside the container instead — `backend/` is bind-mounted into the container, so the generated files appear directly in `backend/data/sample_invoices/` on your host:
```
docker compose exec backend python data/sample_invoices/generate_samples.py
```

### 4. Run the demo
1. Open **http://localhost:5173**.
2. Click **Upload** and select `backend/data/sample_invoices/invoice_01_energie_saar.pdf` → expect a **GREEN** result with a full booking proposal.
3. Try `invoice_03_invalid_calc.pdf` → expect **RED** (blocked, arithmetic mismatch).
4. Try `invoice_04_unknown_vendor.pdf` → expect **YELLOW** (missing service date); edit the field in the form and click **Save & Revalidate** to flip it to GREEN.
5. See `@c:\Users\User\Challenge_CTO\Challenge_CTO\docs\manual-verification-guide.md` for a full feature-by-feature walkthrough.

## Quickstart (Backend)

Prerequisites: Python 3.9+, MongoDB running on localhost:27017 (or `docker run -d -p 27017:27017 --name mongo-invoice mongo:7`)

```
python -m venv venv
venv\Scripts\activate  # Windows
pip install --upgrade pip
pip install -e backend
python backend/data/seed_data.py
uvicorn src.main:app --app-dir backend --host 0.0.0.0 --port 8000 --reload
```

API docs: http://localhost:8000/docs
Master data check: http://localhost:8000/api/master-data

## Tests
```
pip install -r backend/requirements.txt
pytest backend/tests -v
```

## Frontend (React + Vite)

```
cd frontend
npm install
npm run dev
```

The UI is served at http://localhost:5173 and proxies `/api` requests to the backend on `:8000` (see `frontend/vite.config.ts`). Upload a PDF, review the traffic-light status, edit fields on YELLOW invoices, and inspect the booking proposal.

## Run Everything with Docker Compose

```
docker compose up --build
```

This starts MongoDB (`:27017`), the FastAPI backend (`:8000`), and the Vite frontend (`:5173`) together. Seed master data once the backend container is up:

```
docker compose exec backend python data/seed_data.py
```

## Optional: Hosted Open-Weight LLM Extraction

By default, invoice fields are extracted via deterministic regex heuristics (`backend/src/extraction/field_extractor.py`). You can optionally enable semantic extraction via an **open-source/open-weight model** (Llama, Qwen, DeepSeek, ...) served through any OpenAI-compatible API (Together.ai, Groq, Fireworks, ...) — an open alternative to routing invoice text through a closed-source model:

```
set LLM_API_KEY=your-api-key-here          # Windows
set LLM_BASE_URL=https://api.together.xyz/v1   # optional, this is the default
set LLM_MODEL=meta-llama/Llama-3.3-70B-Instruct-Turbo  # optional, this is the default
```

Only pseudonymized text (PII already swapped for surrogate tokens, see `security/anonymizer.py`) is ever sent to this endpoint. If `LLM_API_KEY` is unset, or the API call/response fails for any reason, the pipeline automatically falls back to the regex extractor — no functionality is lost by leaving it disabled. **Never commit an API key**; set it as an environment variable or in an untracked `.env` file.

## Documentation
See docs/development-plan.md for the architecture and development roadmap.
