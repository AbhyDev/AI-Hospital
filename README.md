# AI Hospital

An AI-powered virtual hospital system that simulates medical consultations using a multi-agent architecture. Patients interact with a General Practitioner (GP) who triages and routes to specialists (e.g., Ophthalmologist, Dermatologist), with optional helpers like Pathologist or Radiologist for advanced diagnostics. The system leverages LangGraph for agent orchestration, ChromaDB for knowledge retrieval, and a React frontend for real-time streaming chat.

## Features

- **Multi-Agent Consultation Flow**: GP triage → Specialist routing → Helper assistance (e.g., Pathology, Radiology).
- **Knowledge-Based RAG**: Retrieves medical insights from specialty-specific PDF documents using vectorized embeddings.
- **Real-Time Streaming**: Server-Sent Events (SSE) for live chat updates with speaker tagging (GP, Specialist, Helper).
- **Specialties Supported**: Ophthalmology, Dermatology, ENT, Gynecology, Internal Medicine, Orthopedics, Pediatrics, Psychiatry.
- **Extensible Architecture**: Easily add new specialists or helpers by following the LangGraph patterns.
- **Deployment-Ready**: Optimized for GitHub private repos and cloud hosting (e.g., DigitalOcean App Platform).

## Architecture Overview

### System Topology
- **Backend (`backend/`)**: FastAPI server handling API routes, LangGraph state graph, and CORS.
- **LangGraph Orchestrator (`backend/AI_hospital.py`)**: Defines `AgentState`, tool bindings, and routing logic for GP, specialists, and helpers.
- **Frontend (`frontend/`)**: Vite/React SPA with SSE streaming and speaker-highlighted chat UI.
- **Knowledge Base**: Persistent Chroma vector stores in `backend/vector_stores/` seeded from PDFs in `backend/Knowledge Base/`.

### LangGraph Flow Essentials
- `AgentState` tracks conversation history, Q&A for helpers, next agent routing, and current reports.
- GP interrogates patients via `ask_user`, calls `Patient_data_report`, then routes to specialists.
- Specialists use helpers for Pathology/Radiology Q&A, accumulate reports, and finalize with "Final Report:".
- Helpers respond directly into the specialist's stream.

### Tool Usage
- `ask_user(question)`: Triggers patient input pauses.
- `VectorRAG_Retrival(query, agent)`: Queries specialty-specific Chroma retrievers (k=5 docs).
- `Patient_data_report`: Persists GP summaries for specialists.
- `add_report`: Builds final diagnosis/treatment reports.

### Frontend ↔ Backend Contract
- SSE endpoints: `/api/graph/start/stream`, `/api/graph/resume/stream`.
- Events: `thread`, `message`, `ask_user`, `final`.
- Speaker tags ensure consistent UI highlighting.

## Installation & Setup

### Prerequisites
- Python 3.11+ (with `uv` for dependency management).
- Node.js 18+ (for frontend).
- API Keys: `GEMINI_API_KEY` (for AI models), `TAVILY_API_KEY` (for web search/tools).

### Backend Setup
1. Navigate to `backend/`:
   ```bash
   cd backend
   ```
2. Install dependencies:
   ```bash
   uv sync
   ```
3. Create `.env` file with API keys:
   ```
   GEMINI_API_KEY=your_key_here
   TAVILY_API_KEY=your_key_here
   ```
4. Run the server:
   ```bash
   uv run uvicorn backend.main:app --reload
   ```
   - Server starts at `http://localhost:8000`.

### Frontend Setup
1. Navigate to `frontend/`:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Run the dev server:
   ```bash
   npm run dev
   ```
   - App runs at `http://localhost:5173` (proxies `/api` to backend).

### Knowledge Base Initialization
- PDFs are in `backend/Knowledge Base/{specialty}/`.
- Vector stores are pre-built in `backend/vector_stores/`.
- To refresh: Run `backend/Knowledge_notebooks/vector_rag.ipynb` (uses HuggingFace embeddings on CPU).

## Usage

1. Start backend and frontend as above.
2. Open the frontend in your browser.
3. Start a consultation: Describe symptoms to the GP.
4. Follow the flow: GP triage → Specialist → Helpers (if needed) → Final report.
5. Chat streams in real-time with speaker labels.

### API Endpoints
- `POST /api/graph/start/stream`: Initiate a new consultation thread.
- `POST /api/graph/resume/stream`: Resume with user input for `ask_user` prompts.

## Deployment

### GitHub (Private Repo)
1. Push the entire monorepo to a private GitHub repo.
2. Add `.gitignore` in root: Exclude `.venv/`, `node_modules/`, `.env`, `backend/vector_stores/` (if large), `__pycache__/`.

### DigitalOcean App Platform
1. Connect your GitHub repo.
2. Set build commands:
   - Backend: `cd backend && uv sync && uv run uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
   - Frontend: `cd frontend && npm install && npm run build`
3. Configure environment variables (API keys) in app settings.
4. For multi-service: Use a Dockerfile in root for containerized deployment (Python + Node stages).
5. Ensure model assets (HuggingFace embeddings) are accessible in production.

## Contributing

- Follow the [Copilot Playbook](.github/copilot-instructions.md) for architecture guidelines.
- When adding specialists: Update `router_gp`, `ASK_NODES`, and graph wiring.
- Test changes: Run backend with `uv run uvicorn`, frontend with `npm run dev`.
- Vector store updates: Re-run notebooks after adding PDFs.

## License

This project is private and not licensed for public use.