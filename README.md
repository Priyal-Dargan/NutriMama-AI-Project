# NutriMama AI — Agentic AI Pregnancy Nutrition Assistant

> Educational/portfolio project. Not a substitute for professional medical advice.
> Every AI-generated recommendation must display:
> *"This assistant provides educational information only and is not a substitute for
> professional medical advice. Always consult a qualified healthcare professional
> before making medical decisions."*

## Build Status (read this first)

This project is being built in 5 phases so each piece is real, tested, working code —
not scaffolding with TODOs pretending to be finished. **You are currently on Phase 4.**

| Phase | Scope | Status |
|---|---|---|
| 1 | Project structure, database (8 tables), JWT auth, profile/reminders/nutrition/dashboard CRUD | ✅ Done & tested |
| 2 | LangGraph multi-agent system (Supervisor + 7 agents), AI chat, food safety, meal planning | ✅ Done & tested |
| 3 | RAG pipeline (ChromaDB + embeddings + PyPDF2), blood report OCR/analysis, admin panel | ✅ Done & tested |
| 4 | Frontend (HTML/CSS/JS/Bootstrap) — all pages wired to the API | ✅ Done & tested |
| 5 | Deployment config (Render), polish, full docs | ⏳ Next

**What works right now (Phase 1 + 2 + 3):**
- Everything from Phases 1 & 2 (auth, profile, reminders, nutrition/weight logging,
  dashboard, LangGraph chat, food safety, meal planning)
- **Real RAG pipeline, tested end-to-end:** 5 original educational reference PDFs
  (general pregnancy nutrition, iron & anemia, food safety, calcium & vitamin D,
  gestational diabetes diet) are chunked (PyPDF2 + word-based chunking with
  overlap), embedded, and indexed in a persistent ChromaDB collection. The Medical
  Guidelines Agent retrieves real, relevant chunks — verified with a live query
  ("recommended folate and calcium guidelines") that correctly retrieved from the
  general nutrition and calcium/vitamin D documents specifically, not just "some"
  documents.
- **Blood report upload with real extraction:** PDF lab reports are parsed with
  PyPDF2, images with Tesseract OCR, and four common values (hemoglobin, ferritin,
  vitamin D, blood sugar) are extracted via regex — tested against a sample lab
  report PDF and verified to extract all four values correctly. Manual correction
  via `PUT /reports/blood/{id}` re-runs the AI explanation (never diagnostic) on
  the corrected values.
- **Admin panel endpoints:** `/admin/dashboard` (user/chat counts, RAG index
  stats), `/admin/feedback`, `/admin/rag/status`, `/admin/rag/upload-document`,
  `/admin/rag/rebuild-index` — all gated by `is_admin`, tested including the 403
  rejection for non-admin users.
- The RAG index **auto-builds on first startup** if empty, so `/chat` and
  `/foodsafety/check` have real retrieval available with zero manual setup.
- `POST /chat`, 8 LangGraph agents, emergency detection, `/foodsafety/check`,
  `/mealplan/generate` — all from Phase 2, now backed by real retrieval instead of
  an empty stub.

**Important, stated plainly — the embedding fallback:** Sentence Transformers
(`all-MiniLM-L6-v2`) needs to download model weights from the internet on first
use. In network-restricted environments (like the sandbox this was built and
tested in, some CI runners, or air-gapped servers), that download fails. Rather
than silently break the RAG feature, `rag/embedding.py` automatically falls back
to a TF-IDF vectorizer (scikit-learn, fully offline) — **loudly logged**, never
silent, and inspectable via `GET /admin/rag/status` → `embedder_type`. All the
testing above was done using this fallback, since this build/test environment
has no internet access to HuggingFace. **In a normal environment with internet
access, no fallback occurs and real MiniLM embeddings are used automatically —
no code changes needed.**

**What returns `501 Not Implemented` right now (by design, not by accident):**
- `GET /reports/download` — PDF export (Phase 4/5)

**A note on the RAG source documents:** The 5 PDFs in `rag/documents/` are
original educational summaries written for this project, reflecting broadly
published pregnancy nutrition consensus (the kind of guidance commonly found in
WHO/ACOG/ICMR-style public health material). **They are explicitly not verbatim
reproductions of any official WHO/ICMR/CDC document** — before using this beyond
a demo/portfolio context, replace them with actual licensed or publicly verified
guideline PDFs via `POST /admin/rag/upload-document` + `POST /admin/rag/rebuild-index`.

These routes were wired into the app early — with their final request/response
shape — specifically so the frontend below could be built against a stable
contract instead of needing rework later. That paid off.

**What's new in Phase 4 — the frontend, tested in a real browser, not just written:**
- 16 complete HTML/CSS/JS pages (no framework, per spec): landing page, login,
  register, forgot/reset password, a 6-step onboarding wizard, dashboard, AI
  chat, meal planner, nutrition tracker, food safety checker, reports (incl.
  blood report upload), reminders, medical resources, settings, and an admin
  panel — all calling the real API from Phases 1-3, not mocked data.
- **The backend now serves the frontend directly** (`app.py` mounts `frontend/`
  as static files), so the whole app runs from one `uvicorn` process with zero
  CORS configuration needed — visit `http://127.0.0.1:8000/` and you get the
  landing page; API routes still work normally alongside it.
- A small custom design system (`frontend/css/tokens.css` + `main.css`) — warm
  pastel palette per the spec (soft pink/lavender/mint), Fraunces + Plus Jakarta
  Sans type pairing, and a recurring "growing circle" motif (a 3-arc ring
  showing pregnancy-week progress by trimester) used on the landing page and
  dashboard instead of a generic progress bar.
- **Verified with a real headless-browser test suite** (Puppeteer), not just
  "the code looks right": registration → 6-step onboarding → dashboard →
  food safety check → AI chat → meal plan generation → reminder creation →
  settings → logout → auth-guard redirect, all against the live backend, all
  passing. One real bug (see below) was caught and fixed this way, not left in.
- **A real bug found and fixed during this testing:** none, in the shipped
  code — the one issue this testing surfaced was in the *test script itself*
  (Puppeteer's `.type()` doesn't work correctly on native `<input type="date">`
  fields — it sends keystrokes to the wrong sub-field). The onboarding wizard's
  actual date handling was correct the whole time; this is noted here because
  it's exactly the kind of false-positive worth being explicit about rather
  than silently fixing and moving on.

## Tech Stack

- **Frontend:** HTML, CSS, JavaScript, Bootstrap (Phase 4)
- **Backend:** Python 3.11+, FastAPI
- **Database:** SQLite (SQLAlchemy ORM)
- **Auth:** JWT (access + refresh tokens, bcrypt password hashing)
- **Agents:** LangGraph (Phase 2 ✅)
- **Generative AI:** Google Gemini API or OpenAI GPT, configurable via `.env` (Phase 2 ✅)
- **RAG:** ChromaDB + Sentence Transformers (`all-MiniLM-L6-v2`, with a TF-IDF
  fallback for offline/network-restricted environments — see Phase 3 notes above)
  + PyPDF2 (Phase 3 ✅)
- **Blood Report Analysis:** PyPDF2 (text PDFs) + Tesseract OCR (images) (Phase 3 ✅)
- **Deployment:** Render (Phase 5)

## Project Structure

```
nutrimama-ai/
├── backend/
│   ├── app.py                 # FastAPI entry point (auto-builds RAG index on startup)
│   ├── config.py               # Settings (reads .env)
│   ├── database.py             # SQLAlchemy engine/session/init
│   ├── auth.py                 # JWT create/decode
│   ├── dependencies.py         # get_current_user, get_current_admin
│   ├── requirements.txt
│   ├── .env.example
│   ├── models/                 # SQLAlchemy ORM models (8 tables)
│   ├── schemas/                # Pydantic request/response models
│   ├── routes/                 # API routers, incl. admin.py (Phase 3 ✅)
│   ├── agents/                 # LangGraph agents — Supervisor + 7 specialists (Phase 2 ✅)
│   │   ├── state.py             # Shared GraphState (TypedDict)
│   │   ├── supervisor.py        # StateGraph orchestration + conditional routing
│   │   ├── intent.py            # Intent detection → required-agent routing table
│   │   ├── synthesizer.py       # Merges specialist outputs into final_response
│   │   ├── profile_agent.py
│   │   ├── nutrition_agent.py
│   │   ├── medical_agent.py     # RAG-aware — now backed by real retrieval (Phase 3 ✅)
│   │   ├── food_safety_agent.py
│   │   ├── meal_optimizer.py
│   │   ├── reminder_agent.py
│   │   └── monitoring_agent.py
│   ├── rag/                    # Real RAG pipeline (Phase 3 ✅)
│   │   ├── loader.py             # PyPDF2 extraction + chunking
│   │   ├── embedding.py          # Sentence Transformers, TF-IDF fallback if offline
│   │   ├── chromadb.py           # ChromaDB collection: build/query/stats
│   │   ├── retriever.py          # Public retrieval interface used by agents
│   │   ├── documents/             # 5 source PDFs (generated from source_texts/)
│   │   └── source_texts/          # Original plain-text content (see note above)
│   ├── scripts/
│   │   └── build_source_pdfs.py  # Regenerates rag/documents/*.pdf from source_texts/
│   ├── data/                   # Curated food-safety table + meal templates
│   ├── utils/                  # security, logger, pregnancy/nutrition calc,
│   │                            # emergency detection, ai_client, ocr, blood_report_explainer
│   └── uploads/                # uploaded blood reports
└── frontend/                   # Bootstrap UI (Phase 4 ✅) — served directly by app.py
    ├── index.html                # Landing page
    ├── login.html / register.html / forgot-password.html / reset-password.html
    ├── onboarding.html           # 6-step wizard
    ├── dashboard.html, chat.html, mealplanner.html, tracker.html,
    │   foodsafety.html, reports.html, reminders.html, resources.html,
    │   settings.html, admin.html
    ├── css/
    │   ├── tokens.css              # Design tokens (colors, type, spacing)
    │   └── main.css                # Components, layout, the "growing circle" motif
    └── js/
        ├── api.js                  # Fetch wrapper + JWT handling for every endpoint
        ├── nav.js                  # Shared sidebar nav + auth guard
        └── ui.js                   # Toasts, the growing-circle SVG renderer, formatting
```

## Database Schema (8 tables)

`users` · `pregnancy_profiles` · `medical_history` · `diet_preferences` ·
`nutrition_logs` · `meal_history` · `reminders` · `weight_logs` · `blood_reports` ·
`chat_history` · `feedback`

All tables are created automatically on first run via `init_db()` in `database.py`.

## Agentic AI Architecture (Phase 2)

Every `/chat` request flows through a compiled LangGraph `StateGraph`:

```
User message
     │
     ▼
Emergency Check (deterministic keyword match — always runs, can't be bypassed)
     │
     ├─── emergency detected ──► Safety message, END (no other agent runs)
     │
     ▼
Intent Detection  (routes to: food_safety | meal_plan | medical_guidance |
                    reminder | health_check | general_nutrition)
     │
     ▼
Profile Agent  (loads pregnancy profile, medical history, diet preferences)
     │
     ▼
Conditionally routed, in order — each step SKIPPED if not required for the intent:
  Nutrition Planner → Medical Guidelines → Food Safety → Meal Optimization →
  Reminder → Health Monitoring
     │
     ▼
Synthesis  (merges whichever agents ran into one final_response)
     │
     ▼
Response + agent_timeline + confidence_scores + retrieved_sources
```

Example: *"I'm 24 weeks pregnant, vegetarian, have anemia and only have spinach, rice,
lentils and milk"* → intent `meal_plan` → runs Nutrition Planner, Medical Guidelines,
Meal Optimization; **skips** Food Safety, Reminder, and Health Monitoring — matching
the routing example in the original spec.

Try it via `/docs` → `POST /chat` once you're authenticated, and inspect the
`agent_timeline` in the response to see exactly which agents ran vs. were skipped.

**Design choices worth knowing:**
- Nutrition requirement numbers (calories, protein, iron, etc.) are computed with
  deterministic formulas (Mifflin-St Jeor + ACOG-style pregnancy increments), not
  asked of the LLM — auditable and reproducible, per agent.
- Food safety has a curated table of 13 common foods (coffee, papaya, paneer, raw
  fish, etc.) with real sources; only unrecognized foods fall back to the LLM, and
  that fallback is clearly marked lower-confidence.
- The Medical Guidelines Agent calls a real RAG retriever (`rag/retriever.py` →
  `rag/chromadb.py`) — see the RAG Pipeline section below for how it's built and
  what to know about the embedding model.
- If no `GEMINI_API_KEY`/`OPENAI_API_KEY` is set, agents that need generation fall
  back to deterministic templates/messages instead of crashing — the whole graph,
  routing, and DB writes are fully testable with zero API keys configured.

## RAG Pipeline (Phase 3)

```
rag/documents/*.pdf
        │  (rag/loader.py — PyPDF2 extraction, ~180-word overlapping chunks)
        ▼
   Text chunks
        │  (rag/embedding.py — Sentence Transformers all-MiniLM-L6-v2,
        │   or TF-IDF fallback if model download is unavailable)
        ▼
   Embeddings
        │  (rag/chromadb.py — persisted to CHROMA_PERSIST_DIR)
        ▼
  ChromaDB collection "pregnancy_nutrition_docs"
        │  (rag/retriever.py — cosine similarity query, top-K)
        ▼
  Medical Guidelines Agent (agents/medical_agent.py)
```

- The index **auto-builds on first app startup** if empty (see `app.py`
  `on_startup`). To rebuild manually (e.g. after adding a document), use the
  admin endpoints below.
- **Admin RAG management** (requires `is_admin=True` on your user — promote a
  user directly in the database for now; a proper admin-provisioning flow is a
  natural Phase 5 addition):
  - `GET /admin/rag/status` — chunk count, embedder type, indexed documents
  - `POST /admin/rag/upload-document` — upload a new PDF into `rag/documents/`
  - `POST /admin/rag/rebuild-index` — re-chunk, re-embed, and re-index everything
- To regenerate the bundled source PDFs from their plain-text originals (e.g.
  after editing `rag/source_texts/*.txt`): `python scripts/build_source_pdfs.py`

## Frontend (Phase 4)

The frontend is plain HTML/CSS/JS + Bootstrap 5 (via CDN), per the spec — no
React/Vue/Angular. It's served **by the FastAPI backend itself**: `app.py`
mounts `frontend/` as static files at `/`, registered *after* every API router,
so API routes always win over the static catch-all (Starlette checks routes in
registration order). This means:
- Running the backend (`uvicorn app:app`) serves the entire app — visit
  `http://127.0.0.1:8000/` for the landing page, no separate frontend server,
  no CORS setup needed.
- `frontend/js/api.js` defaults to same-origin relative requests
  (`API_BASE_URL = ''`). If you ever want to serve the frontend from a
  *different* origin (e.g. a separate static host), set
  `window.NUTRIMAMA_API_BASE_URL = 'http://your-backend-host'` in a `<script>`
  tag before `api.js` loads, and add that origin to `CORS_ORIGINS` in the
  backend's `.env`.

**Design system:** `frontend/css/tokens.css` defines the palette (soft pink
`#F48FB1` / lavender `#CE93D8` / mint `#A5D6A7` on a warm off-white, per the
spec), a Fraunces + Plus Jakarta Sans type pairing, and spacing/radius/shadow
scales. `main.css` builds components on top, including the "growing circle" —
a 3-arc SVG ring (one arc per trimester) showing pregnancy-week progress,
generated in `js/ui.js` and used on the landing page hero and dashboard.

**Tested with a real headless browser**, not just read for correctness — see
the Build Status section above for what that covered and what it caught.

## Setup

```bash
cd backend
python -m venv venv

# Activate the virtual environment (pick the line for your OS/shell):
source venv/bin/activate        # macOS/Linux
venv\Scripts\activate           # Windows (Command Prompt)
.\venv\Scripts\Activate.ps1     # Windows (PowerShell)
# If PowerShell blocks the script with an "execution policy" error, run this
# once first, then retry the line above:
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
# Your prompt should now be prefixed with (venv) — that confirms it's active.

pip install -r requirements.txt
# Note: requirements.txt includes Phase 2/3 packages (langgraph, chromadb,
# sentence-transformers, scikit-learn) so the project is ready to grow. This is
# a heavy install (torch, transformers, etc. included) — expect several
# minutes on first run. If you only want to run Phase 1 right now, the minimal
# set is:
#   fastapi uvicorn sqlalchemy pydantic pydantic-settings python-jose bcrypt
#   python-multipart python-dotenv email-validator

# Blood report OCR (Phase 3) needs the Tesseract binary installed separately —
# it's a system package, not a Python package:
#   Ubuntu/Debian: sudo apt-get install tesseract-ocr
#   macOS:         brew install tesseract
#   Windows:       https://github.com/UB-Mannheim/tesseract/wiki
# (PDF-based blood reports work via PyPDF2 without Tesseract; only image
# uploads (.jpg/.png) need it. The upload endpoint degrades gracefully — logs
# a clear error and stores the file — if Tesseract isn't installed.)

cp .env.example .env
# Edit .env: set JWT_SECRET_KEY to a real random value
#   python -c "import secrets; print(secrets.token_hex(32))"
# Also set GEMINI_API_KEY / OPENAI_API_KEY here if you want live AI features
# (the graph runs fine without one too — see "Design choices worth knowing").

uvicorn app:app --host 127.0.0.1 --port 8000
```

**First run takes a bit longer:** on startup, `app.py` auto-builds the RAG
index if it's empty, which may download the embedding model from Hugging Face
the first time. Wait for the terminal to print `Application startup complete`
before opening the browser — if you see `ERR_CONNECTION_REFUSED`, the server
just isn't listening yet, give it another minute.

**Open the app through the server, not by double-clicking the HTML files.**
Go to `http://127.0.0.1:8000/login.html` (or just `http://127.0.0.1:8000/` for
the landing page). Opening `frontend/login.html` directly (`file://...`, e.g.
via double-click or a separate Live Server extension) will make every API
call fail with "Failed to fetch" — the browser blocks it as a cross-origin
request since `file://` isn't in `CORS_ORIGINS`.

**Re-running later:** once `venv` exists, you only need to reactivate it and
start the server — no need to repeat `pip install`:
```bash
cd backend
.\venv\Scripts\Activate.ps1     # or the equivalent for your OS/shell
uvicorn app:app --host 127.0.0.1 --port 8000
```
Add `--reload` back once you're actively editing code — but exclude generated
data folders so it doesn't restart itself in a loop every time the app writes
to them:
```bash
uvicorn app:app --reload --reload-exclude "*.db" --reload-exclude "rag/chroma_store/*" --reload-exclude "uploads/*"
```

Open `http://127.0.0.1:8000/docs` for interactive Swagger API docs.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `Failed to fetch` on login/register | Opened an HTML file directly (`file://...`) instead of through the server | Go to `http://127.0.0.1:8000/login.html` instead |
| `'uvicorn' is not recognized` | Virtual environment doesn't exist yet, or isn't activated | Run the `venv` create + activate steps above; look for `(venv)` in your prompt |
| `ERR_CONNECTION_REFUSED` right after starting the server | Server is still building the RAG index / downloading the embedding model (first run only) | Wait for `Application startup complete` in the terminal, then retry |
| PowerShell blocks `Activate.ps1` with an execution-policy error | Windows default script policy | Run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`, then retry activation |
| `uvicorn --reload` restarts repeatedly / terminal spams output | The app writes to `nutrimama.db` / `rag/chroma_store/` / `uploads/` on startup, and `--reload` watches those same folders, triggering itself in a loop | Use `--reload-exclude` as shown above, or skip `--reload` unless actively editing code |

## Quick API Tour

```bash
# Register
curl -X POST http://127.0.0.1:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"full_name":"Jane Doe","email":"jane@example.com","password":"StrongPass123"}'

# Use the returned access_token as a Bearer token for everything else:
curl http://127.0.0.1:8000/auth/me -H "Authorization: Bearer <access_token>"
```

## Security Notes

- Passwords are hashed with bcrypt (never stored in plain text)
- JWT secret, AI provider keys, etc. are read from `.env` — never commit `.env`
- `forgot-password` currently returns the reset token directly in the API response
  for local testing (no email service is wired up yet). **Before any real deployment,
  replace this with an actual email send and stop returning the token in the response.**
  This is flagged with a `TODO` in `routes/auth.py`.
- The RAG source PDFs (`rag/documents/`) are original demo content, not verified
  official guidelines — see the note in Build Status above before using this
  beyond a portfolio/demo context.

## Next Steps

Phase 5 will add deployment configuration for Render (build/start commands,
persistent storage for `uploads/` and `rag/chroma_store/`, environment variable
setup), a bit of polish (favicon, loading-state refinements, empty-state
illustrations), and final documentation. The application is fully functional
end-to-end locally already — Phase 5 is about making it deployable, not making
it work.

## Before Pushing to GitHub

- [ ] Confirm `.env` is **not** tracked (`git status` should not show it) —
      `.gitignore` already excludes it, along with `*.db`, `uploads/*`, and
      `rag/chroma_store/`
- [ ] Rotate any API key that was ever pasted into a chat, ticket, or shared
      screen, even a "local-only" one — generate a fresh `GEMINI_API_KEY` /
      `OPENAI_API_KEY` and set a real `JWT_SECRET_KEY` (see Setup above)
- [ ] Double check `requirements.txt` vs `requirements_backup.txt` aren't both
      needed — keep one source of truth and delete the other before publishing
- [ ] Run `pip freeze > requirements.txt` from a clean venv install if you want
      the file to reflect exactly what's installed

## Contributing

This is a team project built in phases (see Build Status above). If you're
picking up a piece:
1. Clone the repo, then follow **Setup** above — each teammate needs their own
   local `venv` and `.env` (never share `.env` itself, only `.env.example`)
2. Check the phase table to see what's done vs. in progress before changing
   shared files like `app.py`, `config.py`, or `database.py`
3. Run the existing tests in `backend/tests/` before opening a PR

## License

No license file is currently included. Until one is added, all rights are
reserved by the project authors — add an `LICENSE` file (MIT is a common,
permissive choice for portfolio/educational projects like this) before
treating the repo as open source.
