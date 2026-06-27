# WikiMind — Project Structure Guide
### For AI Coding Assistant

This document explains what goes where and why. Do not deviate from this structure. Every directory has a single responsibility. Files never reach into directories they don't own.

---

## Root Directory

The root holds only infrastructure and configuration files. No Python code lives here. This includes the docker-compose file that orchestrates all containers, the nginx configuration, the environment variable template, the gitignore, and the README. Nothing else.

---

## backend/

This is the entire server-side application. Everything that involves agents, databases, LLMs, pipelines, and the API lives here. The backend is completely self-contained — it has no knowledge of the frontend.

### backend/steps/

This is where all agent logic lives. Each agent is its own file. An agent is a function that receives the shared pipeline state and returns an updated version of that state. Agents are the workers of the system — each one does exactly one job.

There is one file per pipeline node:
- `query_understanding.py` (Step) — takes the raw user query, uses an LLM to expand it into specific Wikipedia search terms, detects the type of query, and decides how many articles to fetch
- `fetch.py` (Step) — takes the search terms and fetches Wikipedia articles in parallel with no LLM involved, just API calls
- `graph_builder.py` (Agent) — this is the only genuine agent. It processes Wikipedia article sections iteratively, makes extraction decisions, handles per-article failures autonomously, and writes to Neo4j.
- `embedder.py` (Step) — takes the same fetched articles, chunks them, embeds them using Gemini, and stores them in Pinecone
- `retrieval.py` (Step) — queries both Neo4j and Pinecone simultaneously and combines the results into a unified context
- `generator.py` (Step) — takes the combined context and generates the final answer using an LLM

Rules for this directory:
- Nodes never import from each other
- Agents never contain database connection logic — that lives in graph/ and vector/
- Agents never contain API endpoint logic — that lives in main.py
- Every agent only reads what it needs from state and writes only its own outputs

### backend/graph/

This directory owns everything related to Neo4j. Nothing outside this directory should write raw Cypher queries. There is one file here — a Neo4j client that manages the database connection and exposes clean functions for the rest of the codebase to use. Functions it provides: get the driver, clear the graph, write nodes, write edges, fetch all edges, fetch edges for a specific concept, close the driver.

The driver is created once at startup and reused — never created per request.

### backend/vector/

This directory owns everything related to Pinecone. Nothing outside this directory should interact with Pinecone directly. There is one file here — a Pinecone client that manages the index connection and exposes clean functions. Functions it provides: get the index, clear the current namespace, upsert chunks, query for similar vectors.

The index connection is created once at startup and reused.

### backend/pipeline/

This directory defines how the agents connect to form a complete pipeline. There are two files here.

The first file defines the state schema — a TypedDict that lists every single field that can exist in the pipeline at any point. This is the contract between all agents. Every agent reads from and writes to this schema. This file is imported by every agent and by the pipeline orchestrator.

The second file defines the LangGraph graph — which agents are nodes, how they connect via edges, which agents run in parallel, and how the pipeline handles conditional routing (like stopping early if no articles were fetched). This file also contains the single entry-point function that the FastAPI endpoint calls to run the full pipeline.

### backend/utils/

This directory holds shared utilities used across the backend. There are two files here.

The first file is the logger — a structured JSON logger that every agent and the API uses. It writes one JSON object per log line to a rotating log file. Every log entry includes a timestamp, log level, query ID, which step logged it, a message, and optional structured data.

The second file contains Pydantic models — the data shapes for FastAPI request validation and response serialization. This includes the request body model, the response model, the trace step model, the graph data model, and the health check model.

### backend/main.py

This is the FastAPI application entry point. It does only four things: sets up the app and middleware, defines the two endpoints (the query endpoint and the health endpoint), handles startup and shutdown lifecycle (initializing and closing database connections), and maps pipeline state to API response models. No business logic, no database calls, no agent code lives here.

### backend/requirements.txt

All Python dependencies for the backend listed here. This is what gets installed in the backend Docker container.

### backend/Dockerfile

Defines how to build the backend container. Installs dependencies from requirements.txt, copies the backend code, creates the logs directory, and starts the FastAPI server with uvicorn on port 8000.

---

## frontend/

The frontend is completely isolated from the backend. It contains no agent code, no database code, and no LangGraph code. It communicates with the backend exclusively via HTTP calls to the FastAPI API.

There is one Python file here — the entire Streamlit application. It handles the UI layout, makes HTTP requests to the backend, renders the answer, renders the interactive knowledge graph using pyvis, and displays the agent trace. It reads the backend URL from an environment variable so the same code works locally and on AWS.

There is also a requirements.txt for frontend-only dependencies and a Dockerfile that builds the frontend container and starts Streamlit on port 8501.

---

## nginx/

One configuration file lives here. Nginx acts as the reverse proxy sitting in front of both containers. It routes requests with the /api/ prefix to the FastAPI backend and all other requests to the Streamlit frontend. This means the user only ever sees one URL — Nginx handles routing internally.

---

## .github/workflows/

One file lives here — the GitHub Actions CI/CD workflow. It triggers on every push to the main branch, SSHes into the EC2 instance, pulls the latest code, rebuilds Docker containers, and runs a health check to confirm the deployment succeeded.

---

## Summary Table

| Directory | Owns | Does not own |
|---|---|---|
| backend/steps/ | Agent logic, LLM calls, state read/write | DB connections, API endpoints |
| backend/graph/ | Neo4j connection, Cypher queries | Any other database |
| backend/vector/ | Pinecone connection, embedding storage | Any other database |
| backend/pipeline/ | State schema, LangGraph graph definition | Agent logic, API logic |
| backend/utils/ | Logging, Pydantic models | Business logic |
| backend/main.py | FastAPI setup, endpoints, lifecycle | Agent logic, DB calls |
| frontend/ | Streamlit UI, HTTP calls to backend | Any backend logic |
| nginx/ | Reverse proxy config | Application logic |
| .github/workflows/ | CI/CD deployment | Application logic |

---

## Key Rules — Never Violate These

1. Frontend never imports anything from backend — HTTP only
2. Nodes never import from each other — state only
3. Database logic never lives in agents — use the client files
4. Business logic never lives in main.py — use the pipeline
5. The state schema in pipeline/state.py is the single source of truth for all data shapes in the pipeline — if a new field is needed, add it there first
6. Every file has one job — if a file is doing two unrelated things, it needs to be split

