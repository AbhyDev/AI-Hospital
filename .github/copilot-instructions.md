# AI-Hospital Copilot Instructions

Purpose: help AI agents quickly navigate and extend this LangGraph-powered medical assistant.

## Architecture at a glance
- **Backend (FastAPI + LangGraph)**: `backend/main.py` is the FastAPI entrypoint. The core application logic resides in `backend/AI_hospital.py`, which defines the agentic states, tools, and the LangGraph graph (`myapp`). The API layer in `backend/api.py` exposes SSE endpoints for the frontend to start and resume graph streams.
- **Frontend (React + Vite)**: A single-page application in `frontend/`. The main chat UI is in `frontend/src/ui/App.tsx` (or a similar component in that directory), which communicates with the backend over SSE.
- **Knowledge Base (RAG)**: The system uses Chroma vector stores located in `backend/vector_stores/{specialty}`. These are initialized from PDFs in `backend/Knowledge Base/` by `backend/Knowledge_notebooks/initialize_rag.py`.

## How the agent system works (LangGraph)
- **State (`AgentState` in `AI_hospital.py`)**: The graph's memory. Keys include `messages` (for the GP), `specialist_messages`, `patho_messages`, `radio_messages` (for specialists and helpers), `next_agent` (for routing), and `current_report`.
- **Control Flow**:
  1. The `general_physician` agent starts, collecting patient data via the `ask_user` tool.
  2. Once enough data is gathered, it calls `Patient_data_report`.
  3. On its next turn, it emits the name of a specialist (e.g., "Ophthalmologist").
  4. The `router_gp` function directs the graph to the chosen specialist's node.
  5. The specialist works on the case, potentially calling helper agents (`Pathologist`, `Radiologist`) by name in its text output.
  6. Helper agents return reports, which are routed back to the calling specialist.
  7. The specialist concludes by first calling `add_report` with a final summary, and then, in the next turn, returning a plain string that starts with the exact phrase `Final Report:`. This terminates the graph.

## Tools and Conventions
- **`ask_user(question: str)`**: This tool call is intercepted by the graph. The graph pauses, and the `api.py` sends an `ask_user` event to the frontend. The user's reply is injected back into the graph via the `/graph/resume/stream` endpoint.
- **`VectorRAG_Retrival(query: str, agent: str)`**: Queries the Chroma vector store. The `agent` parameter must be one of the specialist keys (e.g., 'Ophthalmologist', 'Dermatology').
- **`Patient_data_report(data: str)`**: The General Physician MUST call this tool before routing to a specialist. It populates a global `patient_info` variable.
- **Calling Helpers**: A specialist invokes a helper by returning a string like `"I need a blood report from Pathologist, please check for..."`. The router (`router_opthal`, etc.) will catch the keyword "Pathologist" and route accordingly.
- **Final Report**: A specialist MUST end its work by first using the `add_report` tool for its final conclusions, and then returning `Final Report: ...` in the subsequent turn. This exact string is the signal for the graph to end.

## Streaming API (SSE Contract in `api.py`)
- **Start**: `GET /graph/start/stream?message=...`
  - Emits `thread` event with `thread_id`.
  - Emits `message` events with `{content, speaker}`.
  - Ends with either an `ask_user` event or a `final` event.
- **Resume**: `GET /graph/resume/stream?thread_id=...&user_reply=...`
  - Resumes the graph with the user's reply as a `ToolMessage`.
  - Follows the same event pattern as the start stream.
- **Speakers**: "GP", "Specialist", "Pathologist", "Radiologist". These are determined in `api.py` based on which message stream in the state was just updated.

## Running Locally
1.  **Environment**: Create a `.env` file in the root with your `GEMINI_API_KEY` and `TAVILY_API_KEY`.
2.  **Backend Dependencies**: `pip install -r requirements.txt`. Note: `uvicorn` and `sse-starlette` are required but might not be in the file.
3.  **Run Backend**: From the project root, run: `uvicorn backend.main:app --reload`.
4.  **Frontend Dependencies**: `cd frontend && npm install`.
5.  **Run Frontend**: `npm run dev`. The app will be available on `http://localhost:5173`.

## How to Extend the System
- **Add a New Specialist**:
  1. Define a new agent function (e.g., `Cardiologist`) and a router function (e.g., `router_cardio`) in `backend/AI_hospital.py`.
  2. Bind the necessary tools to an LLM instance for your new specialist.
  3. Add a `ToolNode` and an `AskUser` node to the graph.
  4. Register the new nodes and edges in the `workflow` StateGraph. Add the new specialist name to the `router_gp` logic.
  5. Add the new `*_AskUser` node name to the `interrupt_before` list and the `ASK_NODES` set in `api.py`.
- **Update RAG**:
  1. Add new PDF documents to the relevant folder in `backend/Knowledge Base/`.
  2. Run the `backend/Knowledge_notebooks/vector_rag.ipynb` notebook to re-index the data and persist it to the corresponding `backend/vector_stores/` directory.
