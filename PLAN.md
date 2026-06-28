# WikiMind — Build Plan for AI Coding Assistant
### Multi-Agent GraphRAG Knowledge Explorer
**Version:** 1.0
**Purpose:** This document is the single source of truth for building WikiMind. It describes what to build, why, and in what order — without code samples. Follow this plan step by step. Do not skip steps. Do not make assumptions about implementation details not covered here.

---

## Table of Contents

1. [What WikiMind Is](#1-what-wikimind-is)
2. [How the System Works — Big Picture](#2-how-the-system-works--big-picture)
3. [Technology Stack](#3-technology-stack)
4. [Folder Structure](#4-folder-structure)
5. [Environment Variables](#5-environment-variables)
6. [Agent Design — What Each Agent Does](#6-agent-design--what-each-agent-does)
7. [Data Flow — What Data Exists at Each Stage](#7-data-flow--what-data-exists-at-each-stage)
8. [Database Design](#8-database-design)
9. [API Design](#9-api-design)
10. [UI Design](#10-ui-design)
11. [Docker Setup](#11-docker-setup)
12. [AWS Deployment](#12-aws-deployment)
13. [CI/CD Pipeline](#13-cicd-pipeline)
14. [Logging](#14-logging)
15. [LangGraph State Schema](#15-langgraph-state-schema)
16. [Error Handling Strategy](#16-error-handling-strategy)
17. [Known Issues to Fix During Implementation](#17-known-issues-to-fix-during-implementation)
18. [Day by Day Build Plan](#18-day-by-day-build-plan)

---

## 1. What WikiMind Is

WikiMind is a multi-agent AI system. When a user types a question, the system fetches relevant Wikipedia articles, builds a live knowledge graph from the article content, embeds the articles into a vector store, retrieves context from both the knowledge graph and vector store simultaneously, and uses a large language model to generate a structured answer.

The system was originally designed to start fresh for each query, but it now acts as a persistent, append-only knowledge base for space and astronomy. Instead of wiping its memory, the Neo4j graph accumulates a rich interconnected map of space knowledge covering planets, missions, telescopes, phenomena, and discoveries. If the system has already processed relevant concepts, it instantly retrieves them, becoming faster and more knowledgeable with every query. It is a portfolio project demonstrating production-grade multi-agent orchestration and GraphRAG architecture.

---

## 2. How the System Works — Big Picture

The user interacts with a React frontend. When a query is submitted, the React app sends it to a FastAPI backend via HTTP. The FastAPI backend runs a LangGraph pipeline made up of 6 pipeline steps. Only one of them (Graph Builder) is genuinely an agent. The pipeline runs the nodes in a specific order, with two of them running in parallel. After the pipeline completes, FastAPI returns a structured response to React, which displays the answer, an interactive knowledge graph visualization, and an execution timing trace.

The pipeline steps in order:

- Step 1 - Query Understanding: analyzes the user query and produces a search plan
- Step 2 - Wikipedia Fetch: fetches Wikipedia articles based on that search plan
- Step 3 (Agent) - Graph Builder: extracts a knowledge graph from the articles and writes it to Neo4j (runs in parallel with Step 4)
- Step 4 - Vector Embedder: chunks and embeds the articles into Pinecone (runs in parallel with Step 3)
- Step 5 - Dual Retrieval: retrieves relevant context from both Neo4j and Pinecone simultaneously
- Step 6 - Generator: generates the final answer using the retrieved context

FastAPI and React (via Nginx or a static server) run as separate Docker containers. A third Nginx container acts as a reverse proxy, routing traffic to the right container. All databases are cloud-hosted — Neo4j AuraDB for the knowledge graph and Pinecone for vector embeddings. No local databases.

---

## 3. Technology Stack

**LLM Models:**
- Agent 1 (Query Understanding) uses Google Gemini via AI Studio (Model `gemma-4-31b-it`)
- Agent 3 (Graph Builder) uses OpenRouter (Model `nemotron-3-super-120b-a12b:free`) for highly detailed extraction and rate limit avoidance
- Agent 6 (Generator) uses Google Gemini via AI Studio (Model `gemini-3.1-flash-lite`) to avoid rate limit issues and ensure fast response generation
- OpenRouter calls use the OpenAI Python SDK pointed at the OpenRouter base URL. Gemini calls use the `google-generativeai` SDK.

**Embeddings:**
- Pinecone Inference API. Model name is `llama-text-embed-v2`. Output dimension is 1024.

**Databases:**
- Neo4j AuraDB free tier for knowledge graph. One instance. Connect via the official Neo4j Python driver.
- Pinecone free tier for vector embeddings. One index. Connect via the official Pinecone Python SDK. Note: the PINECONE_ENVIRONMENT variable is a legacy concept in newer Pinecone SDK versions — check the current SDK docs and remove it if not needed.

**Agent Framework:**
- LangGraph for the agent pipeline, state management, node definitions, and parallel execution
- LangChain for document chunking utilities

**Wikipedia:**
- The wikipedia Python library (PyPI package name: wikipedia). No API key required. It can throw DisambiguationError in addition to standard not-found errors — both must be caught explicitly.

**Backend:** FastAPI with Uvicorn. Pydantic for request and response validation.

**Frontend:** React with Vite. Tailwind CSS for styling. React Flow and `dagre` for knowledge graph visualization. React Markdown (with `remark-math` and `rehype-katex` configured for `html` output) for answer rendering. Lucide React for icons. Axios for HTTP calls.

**Infrastructure:** Docker, Docker Compose, Nginx, AWS EC2 t3.micro, GitHub Actions.

---

## 4. Folder Structure

The project root is wikimind/. The structure is as follows:

The backend/ folder contains all agent and pipeline code. Inside it: an agents/ subfolder with one file per agent, a graph/ subfolder with the Neo4j client, a vector/ subfolder with the Pinecone client, a pipeline/ subfolder with the LangGraph state schema and graph definition, a utils/ subfolder with the logger and Pydantic models, and main.py as the FastAPI entry point.

The frontend/ folder contains the Vite React app. The frontend must be completely independent — it imports nothing from backend/.

The nginx/ folder contains only nginx.conf.

The .github/workflows/ folder contains deploy.yml for CI/CD.

The root contains docker-compose.yml, .env.example (committed), .gitignore, and README.md. The actual .env file is never committed.

**Rules:**
- Agent logic never goes in main.py
- Database connection logic never goes in agents — it belongs in graph/ and vector/ client files
- The frontend never imports from the backend — it only makes HTTP calls

---

## 5. Environment Variables

The .env file holds all secrets and config. It is never committed to GitHub. The .env.example file with placeholder values is committed.

Variables needed:
- OPENROUTER_API_KEY and OPENROUTER_BASE_URL for OpenRouter LLM calls
- GOOGLE_API_KEY for Gemini/Gemma models via AI Studio
- NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD for AuraDB connection
- PINECONE_API_KEY and PINECONE_INDEX_NAME for Pinecone connection
- BACKEND_URL for the React frontend to know where FastAPI is (localhost:8000 locally, EC2 IP on AWS)
- App config variables: MAX_ARTICLES, CHUNK_SIZE, CHUNK_OVERLAP, LOG_FILE_PATH

---

## 6. Agent Design — What Each Agent Does

Each agent is a Python function that accepts the current LangGraph state dict and returns an updated state dict. Agents never call each other directly. They only read from and write to the shared state.

---

### Agent 1 — Query Understanding

**File:** backend/steps/query_understanding.py
**Model:** Nemotron via OpenRouter (`nvidia/llama-3.3-nemotron-super-49b-v1.5`)

This agent takes the raw user query and produces a structured search plan. Its job is to make the query concrete enough for Wikipedia searching.

What it does:
- Expands abbreviations and acronyms relevant to space and astronomy (for example "JWST" becomes "James Webb Space Telescope", "CMB" becomes "cosmic microwave background").
- Appends domain context to all search terms only when genuinely ambiguous (e.g., "corona (astronomy)"). It prefers the most specific Wikipedia article title without adding unnecessary filler words.
- Determines the query type: explanation (one concept, fetch 2 articles), comparison (multiple concepts, fetch 3 articles), or broad (overview topic, fetch 3-4 articles)
- Produces a list of 2-4 specific Wikipedia search queries and the number of articles to fetch

The prompt to Gemini must instruct it to return only a JSON object with no markdown, no backticks, and no explanation text. The JSON must contain: core_concepts (list of strings), wikipedia_queries (list of strings), query_type (string), num_articles (integer).

If the OpenRouter call fails or returns unparseable output, retry once. If the retry also fails, fall back to splitting the query into keywords and using them directly. Never block the pipeline on this step.

---

### Step 2 — Wikipedia Fetch

**File:** backend/steps/fetch.py
**Model:** None

This agent takes the list of Wikipedia search queries and fetches the corresponding articles.

What it does:
- Fetches all articles in parallel using ThreadPoolExecutor (not sequentially)
- For each query, takes the top search result
- Deduplicates by article title — if two queries return the same article, keeps only one copy
- Returns articles as structured objects containing: title, summary, full content, URL, and which query fetched it

Two exception types must be caught explicitly: the standard not-found exception and wikipedia.exceptions.DisambiguationError. For DisambiguationError, either take the first option from the disambiguation list or skip that query. Do not crash.

If zero articles are fetched after all queries, stop the pipeline and return a user-facing error message. Otherwise continue with however many articles were successfully fetched.

Do not clean or parse the article content at this stage. Pass raw content forward.

---

### Step 3 — Graph Builder

**File:** backend/steps/graph_builder.py
**Model:** Nemotron via OpenRouter (`nvidia/llama-3.3-nemotron-super-49b-v1.5`)

This agent takes the fetched Wikipedia articles and builds a knowledge graph in Neo4j.

What it does:
- Performs a pre-flight check in Neo4j for the queried concepts. If they already exist, it skips extraction and instantly sets `graph_ready=True` (zero-shot graph building).
- If concepts are missing, it sends the new article content to Nemotron to extract entities and relationships.
- Merges the extracted nodes and edges into a persistent, append-only Neo4j AuraDB knowledge graph.
- Returns a summary of what was built or bypassed: node count, edge count, list of node names, and the full nodes/edges data for the UI visualization.

Chunking strategy for extraction: Wikipedia articles have section headers (== Section Name ==). Split by section and process each section separately. This keeps each LLM call focused and improves extraction quality.

Prompt rules for Nemotron: return only valid JSON with no markdown. Extract pristine, space-specific entities only in their singular form. No generic filler nodes (like "surroundings", "researchers", "telescope parts"). Relation names must be snake_case and directional. Extract 15-30 granular, detailed relationships per article focused strictly on astronomical phenomena and missions.

Since OpenRouter free tier does not support the response_format JSON parameter, parse the response by extracting content between the first opening brace and the last closing brace. This is the primary parsing strategy, not a fallback.

Neo4j write strategy: normalize all node names (strip whitespace and apply consistent casing) before any write operation. Write all nodes first using MERGE to avoid duplicates, then write all edges. Use MERGE not MATCH when looking up nodes for edge creation, to prevent silent failures when node names have minor variations.

If Nemotron returns unparseable output for an article, skip that article and continue. If the Neo4j write fails, log the error and set graph_ready to False in state so the next agent knows to use vector-only retrieval.

---

### Step 4 — Vector Embedder

**File:** backend/steps/embedder.py
**Model:** Pinecone Inference API (`llama-text-embed-v2`)

This agent takes the same fetched articles as Agent 3 (they run in parallel) and stores them in Pinecone as vector embeddings.

What it does:
- Splits each article into overlapping chunks using LangChain's RecursiveCharacterTextSplitter (chunk size 500 words, overlap 50 words)
- Embeds each chunk using Pinecone Inference API (`llama-text-embed-v2`)
- Stores embeddings in Pinecone with metadata: chunk text, article title, article URL, chunk index
- Returns the total number of chunks embedded

Embedding cache: maintain a module-level in-memory dictionary keyed by the hash of each chunk's text. Check the cache before calling the Pinecone API. Store results in the cache after calling. This prevents re-embedding the same content across similar queries in the same session.

Pinecone namespace strategy: use the Wikipedia article title (e.g., `black_hole`) as the namespace. This allows cross-query retrieval and deduplication of embedded articles. Once an article is embedded, future queries that fetch the same article can instantly retrieve its chunks without needing to re-embed them.

When querying in Agent 5, filter by the specific namespaces of the articles fetched for the current query, allowing the system to reuse previously embedded data.

If the Pinecone write fails, log the error and set vector_ready to False in state. Never crash the pipeline.

---

### Step 5 — Dual Retrieval

**File:** backend/steps/retrieval.py
**Model:** None

This agent runs after both Agent 3 and Agent 4 complete. It retrieves relevant context from both databases simultaneously and combines the results.

What it does:
- Checks the graph_ready and vector_ready flags in state to know which databases are available
- Runs Neo4j and Pinecone queries in parallel
- Combines results into a single context object for the Generator

Neo4j retrieval: run two Cypher queries. First, fetch all nodes and edges in the current graph (limit 50). Second, for each core concept from Agent 1, find nodes whose names contain that keyword and return their relationships. Format all graph results as plain English sentences (for example "Transformer uses self-attention mechanism") rather than raw Cypher output.

Pinecone retrieval: embed the original user query using Pinecone Inference API, then search Pinecone for the top 5 most similar chunks. Filter the search by the current query's namespace. Return chunk text and metadata.

Combined output written to state: a list of graph fact strings, a list of vector chunk objects (each with text, source article title, and URL), and a list indicating which retrieval sources were used.

Graceful degradation: if graph_ready is False, skip Neo4j and note "Graph unavailable" in retrieval_sources. If vector_ready is False, skip Pinecone and note "Vector unavailable". If both are unavailable, return empty context and let the Generator handle it with a warning.

---

### Step 6 — Generator

**File:** backend/steps/generator.py
**Model:** `gemini-3.1-flash-lite` via `google-generativeai`

This agent takes the original query and the combined retrieval context and generates the final answer.

What it does:
- Constructs a prompt containing the original query, an enumerated SOURCES list, graph facts formatted as bullet points, and vector chunks formatted with source labels
- Instructs the model to answer strictly from the provided context, cite exact sources inline using numeric bracket notation (e.g., `[1]`) with a strict rule of only ONE citation at the very end of each paragraph, provide a "References" list at the bottom, format all math equations using LaTeX (KaTeX compatible `$inline$` and `$$block$$`), and explicitly state when the context is insufficient rather than hallucinating
- Includes built-in retry logic (retry once after a 2-second wait on failure)
- Returns the generated answer text, a list of source objects (title and URL), and a record of which retrieval methods were used

The target audience in the prompt is space enthusiasts and astronomers. The generator must use high-level technical terminology (e.g., orbital mechanics, spectroscopy, stellar evolution) and avoid over-explaining basics.

If the generation call fails, retry once after a 2-second wait. If the retry also fails, return an error message to the user that includes the raw retrieval context so they still get value from the query.

---

## 7. Data Flow — What Data Exists at Each Stage

**Stage 1 — User submits query:**
React sends a POST request to FastAPI with a JSON body containing the query string.

**Stage 2 — After Agent 1:**
State contains: the list of core concepts, the list of Wikipedia search queries, the query type, and the number of articles to fetch.

**Stage 3 — After Agent 2:**
State contains: a list of article objects (each with title, summary, full content, URL, and originating query), and a list of any fetch errors.

**Stage 4 — After Agents 3 and 4 (parallel):**
Step 3 adds to state: node count, edge count, list of node names, full nodes list, full edges list, and graph_ready boolean.
Step 4 adds to state: number of chunks embedded and vector_ready boolean.
These writes go to different state keys so there is no conflict.

**Stage 5 — After Step 5:**
State contains: list of graph fact strings, list of vector chunk objects, and list of retrieval sources used.

**Stage 6 — After Step 6:**
State contains: the generated answer string, list of source objects, and list of retrieval methods used.

**Stage 7 — Response to React:**
FastAPI serializes the relevant state fields into a response JSON containing: answer, sources, graph data (nodes and edges for visualization), agent timing trace, total duration in milliseconds, and retrieval methods used.

---

## 8. Database Design

### Neo4j AuraDB

Create a free account at neo4j.com/cloud/aura. Create one free AuraDB instance. Download the connection credentials. Store URI, username, and password in .env.

Graph schema is schema-free. All nodes have a single property called name. All relationships have a single property called type (the relation name extracted by the LLM).

The Neo4j Python driver creates one connection at backend startup and reuses it across all requests. It does not create a new connection per request.

Add a startup ping — execute a simple query like RETURN 1 when the backend starts — to wake the AuraDB instance if it has paused due to inactivity. This prevents the first real query from hitting a cold-start connection error.

Operations used: clear all data before each query, MERGE nodes by name, MERGE edges using node lookups, fetch all edges, fetch edges for specific keyword matches.

### Pinecone

Create a free account at pinecone.io. Create one index named wikimind. Set dimension to 768 (matches Gemini embedding output — verify before creating). Set metric to cosine. Store API key in .env.

Each query uses a unique namespace (query_id). Old namespaces are never deleted during a session. Metadata stored per vector: chunk text, article title, article URL, chunk index. Always specify the namespace when upserting and when querying.

---

## 9. API Design

**File:** backend/main.py

Two endpoints:

POST /query — the main endpoint. Accepts a JSON body with a query string. Invokes the full LangGraph pipeline. Returns a JSON response containing: answer, sources list, graph data (nodes and edges), agent trace (list of steps with name, duration in milliseconds, and detail message), total duration in milliseconds, and retrieval methods used.

GET /health — simple health check. Returns a JSON object with status "ok". Used by Nginx and GitHub Actions.

Every agent call is wrapped with a timer. Duration in milliseconds is recorded and added to the trace list. The trace list is built by the pipeline orchestrator, not by individual agents.

Enable CORS middleware in FastAPI to allow the React app (running on a different port like 5173) to make requests. Allow all origins — this is acceptable for a portfolio project.

The FastAPI app imports the LangGraph pipeline and invokes it per request. All agent logic lives in the agents/ files, not in main.py.

---

## 10. UI Design

**File:** frontend/src/App.jsx

The UI features a dark space aesthetic (`#07080f` background) with a pure CSS-generated starfield.

**Top section — Hero & Query input:**
A landing hero section titled "EXPLORE THE UNIVERSE". A wide search bar with an indigo glow and suggested query chips below it. While processing, animated skeleton loaders display cycling status messages.

**Results section:**
Fades in and smoothly scrolls into view after a query. Split into two columns:
- **Left column (`AnswerPanel.jsx`)**: Displays the generated answer rendered as markdown. Below the answer, shows clickable source links and small badges indicating which retrieval methods were used (Neo4j Graph, Pinecone Vector).
- **Right column (`KnowledgeGraph.jsx`)**: Displays the interactive knowledge graph using React Flow integrated with `dagre` for an automated Directed Acyclic Graph (DAG) layout. Nodes are dynamically color-coded by type (celestial bodies, missions, phenomena).

**Bottom section — Pipeline Trace:**
An expandable accordion panel (`PipelineTrace.jsx`) showing the agent trace. Each step has a name, duration in milliseconds, and a detail message. Shows total duration and cache/error badges.

The frontend reads the FastAPI URL from the VITE_BACKEND_URL environment variable.

---

## 11. Docker Setup

**Backend Dockerfile:** Use python:3.11-slim as base. Set working directory to /app. Install dependencies from requirements.txt. Copy all backend code. Create the /app/logs directory. Expose port 8000. Start with uvicorn pointing to main:app on 0.0.0.0 port 8000.

**Frontend Dockerfile:** Use node:18-alpine as base. Set working directory to /app. Copy package.json and install dependencies. Copy frontend code. Expose port 5173. Start with `npm run dev` on 0.0.0.0 port 5173 (for development).

**docker-compose.yml:** Define three services: backend (port 8000, loads .env file, mounts logs volume), frontend (port 5173, receives VITE_BACKEND_URL as environment variable pointing to the backend service), nginx (uses official nginx image, mounts nginx.conf, exposes port 80, depends on both backend and frontend).

**nginx.conf:** All requests to /api/ are proxied to the backend container on port 8000. All other requests are proxied to the frontend container on port 5173.

Local development: run docker-compose up --build from the project root. React app is accessible at http://localhost. FastAPI docs are accessible at http://localhost/api/docs.

---

## 12. AWS Deployment

**EC2 instance:** t3.micro (free tier eligible), Ubuntu 22.04 LTS, 20GB storage. Security group opens ports 22 (SSH), 80 (HTTP), and 443 (HTTPS for future use). Generate a key pair and store the .pem file securely — never commit it.

**One-time manual setup on the server:** Update the system packages. Install Docker using the official Docker install script. Install Docker Compose. Install Git. Clone the GitHub repository. Manually create the .env file on the server with all real values. Run docker-compose up -d --build to start all containers. Verify with docker-compose ps that all three containers are running.

After this initial setup, all future deployments are handled automatically by GitHub Actions.

---

## 13. CI/CD Pipeline

**File:** .github/workflows/deploy.yml

Triggers on every push to the main branch only.

Steps in order:
1. Checkout the code
2. Run basic checks: verify requirements.txt files exist, Dockerfiles exist, and no .env file was accidentally committed
3. SSH into the EC2 instance using the appleboy/ssh-action GitHub Action. On the server: pull the latest code, rebuild and restart containers with docker-compose up -d --build, verify containers are running
4. Make a health check HTTP GET to the /api/health endpoint on the EC2 public IP. If the response is not status "ok", mark the deployment as failed.

GitHub Secrets required: EC2_HOST (public IP or DNS), EC2_USERNAME (ubuntu for Ubuntu instances), EC2_PRIVATE_KEY (full contents of the .pem key file). Environment variables from .env are NOT stored in GitHub — they live only on the EC2 server.

---

## 14. Logging

**File:** backend/utils/logger.py

Every log entry is a single-line JSON object written to a log file. Fields: timestamp (ISO format with UTC), level (INFO/ERROR/WARNING), query_id, step (which agent or operation), message, and a data object with step-specific fields like duration_ms and counts.

What gets logged: every agent start and completion with duration, every external API call, every error with full exception message and traceback, query start with query text and query_id, query completion with total duration and success or failure status.

What never gets logged: full Wikipedia article content, full LLM prompts, API keys or any credentials.

Log file location is /app/logs/wikimind.log inside the backend container. This path is mounted as a Docker volume so logs persist if the container restarts.

Use Python's RotatingFileHandler with a max size of 10MB per file and 3 backup files.

---

## 15. LangGraph State Schema

**File:** backend/pipeline/state.py

The state is a TypedDict. Every field used by any agent must be declared here. Agents read what they need and write only their own output keys.

Fields by category:

Input fields: query (string), query_id (string).

Step 1 output fields: core_concepts (list of strings), wikipedia_queries (list of strings), query_type (string — one of explanation, comparison, broad), num_articles (integer).

Step 2 output fields: articles (list of dicts), fetch_errors (list of strings).

Step 3 output fields: graph_node_count (integer), graph_edge_count (integer), graph_node_names (list of strings), graph_nodes (list of strings, for UI), graph_edges (list of dicts, for UI), graph_ready (boolean).

Step 4 output fields: chunks_embedded (integer), vector_ready (boolean).

Step 5 output fields: graph_facts (list of strings), vector_chunks (list of dicts), retrieval_sources (list of strings).

Step 6 output fields: answer (string), sources (list of dicts).

Orchestrator fields: trace (list of dicts), total_duration_ms (integer).

Error field: pipeline_error (optional string).

**Critical implementation note:** The trace field is a list that gets appended to by the orchestrator after each agent completes. In LangGraph, when two parallel nodes (Agents 3 and 4) both write to a shared list field, the second write can overwrite the first. Declare the trace field with a reducer annotation using operator.add so that list additions from parallel nodes are merged rather than overwritten. Apply this same treatment to any other list field that parallel agents might append to.

**File:** backend/pipeline/graph.py

Define the LangGraph graph with six nodes corresponding to the six agents. Edges: START goes to Agent 1, Agent 1 goes to Agent 2, Agent 2 fans out to both Agent 3 and Agent 4 in parallel, both Agent 3 and Agent 4 feed into Agent 5 (LangGraph waits for both to complete before starting Agent 5), Agent 5 goes to Agent 6, Agent 6 goes to END.

---

## 16. Error Handling Strategy

The core principle is: never let an exception from one agent crash the entire pipeline. Every agent catches its own exceptions and communicates failure through state flags.

Agent 1 failure: retry once, then fall back to using the raw query keywords. Pipeline always continues.

Agent 2 failure: skip individual failed articles. If all articles fail, set pipeline_error in state and stop with a user-facing message.

Agent 3 failure: set graph_ready to False. Pipeline continues. Agent 5 will use vector-only retrieval.

Agent 4 failure: set vector_ready to False. Pipeline continues. Agent 5 will use graph-only retrieval.

Agent 5 failure: if both databases are unavailable, return empty context. Generator will note the limitation in its answer.

Agent 6 failure: retry once after 2 seconds. If retry fails, return a message containing the raw retrieval context so the user still gets value.

User-facing error messages must always be friendly plain English. Never surface raw exception text or stack traces to the UI.

---

## 17. Known Issues to Fix During Implementation

These are specific bugs identified during planning that must be addressed when implementing the relevant component. They are not optional.

**Issue 1 — Pinecone namespace deletion race condition (fix in Agent 4):**
Do not delete the Pinecone namespace before upserting. Deletion is asynchronous and upserts can race against incomplete deletes, mixing old and new vectors. Instead, use a unique namespace per query_id. This is the correct approach.

**Issue 2 — Neo4j relationship creation silent failures (fix in Agent 3):**
Normalize all node names before writing — strip whitespace and apply consistent casing. When creating edges, use MERGE (not MATCH) for the node lookup so that minor name variations do not cause the relationship to silently fail.

**Issue 3 — Gemini embedding dimension verification (fix before creating Pinecone index):**
Verify the actual output dimension of models/embedding-001 before creating the Pinecone index. The index dimension cannot be changed after creation. Create the index only after confirming the dimension.

**Issue 4 — LangGraph parallel state reducer (fix in state.py on Day 1):**
The trace field and any other list field written by parallel agents must use a reducer annotation (operator.add) so parallel writes are merged instead of the second overwriting the first. Apply this when first writing state.py.

**Issue 5 — Wikipedia DisambiguationError (fix in Agent 2):**
The wikipedia library throws DisambiguationError as a separate exception class from standard not-found errors. Catch it explicitly. Either use the first option from the disambiguation list or skip that query. Do not let it crash Agent 2.

**Issue 6 — OpenRouter JSON parsing (fix in Agent 3 and Agent 6):**
OpenRouter free tier does not support the response_format JSON parameter. The LLM will frequently include preamble text before the JSON. Parse responses by finding the first opening brace and the last closing brace and extracting the content between them. This is the primary parsing approach, not a fallback.

**Issue 7 — Wikipedia fetch threading (fix in Agent 2):**
The wikipedia library is synchronous. Use ThreadPoolExecutor to run fetches in parallel. Do not use asyncio.gather directly on synchronous functions without first wrapping them in loop.run_in_executor, or they will run sequentially despite appearing parallel.

**Issue 8 — Neo4j AuraDB cold start (fix in Neo4j client):**
The free AuraDB instance pauses after inactivity and returns a connection error (not a slow response) when paused. Add a startup ping — execute a lightweight query immediately when the backend starts — to wake the instance before the first user query arrives.

---

## 18. Day by Day Build Plan

### Day 1 — Foundation and Agent 1

Create the complete folder structure as defined in Section 4. Set up a Python virtual environment and install all dependencies. Create .env from .env.example and fill in all API keys.

Write backend/pipeline/state.py with the full LangGraph state schema including the reducer annotation on the trace field (see Issue 4 above).

Write backend/utils/logger.py with JSON structured logging, RotatingFileHandler, and all the fields described in Section 14.

Write backend/steps/query_understanding.py (Agent 1). Test it in isolation with at least three different query types: a single-concept explanation query, a comparison query, and a broad overview query. Verify the output JSON is correct for each type.

Commit everything to GitHub. This is the first commit.

---

### Day 2 — Agent 2 and First Two-Agent Pipeline

Write backend/steps/fetch.py (Agent 2). Implement parallel fetching with ThreadPoolExecutor. Implement deduplication by article title. Implement explicit handling for both DisambiguationError and standard not-found errors (see Issues 5 and 7).

Test Agent 2 in isolation: verify parallel fetching works, verify deduplication works, verify error cases are handled gracefully.

Write backend/pipeline/graph.py with just the first two nodes and edge: Agent 1 to Agent 2. Run this two-agent pipeline end to end and inspect the output.

Commit to GitHub.

---

### Day 3 — Neo4j and Agent 3

Create the Neo4j AuraDB instance. Get the connection credentials and add them to .env.

Write backend/graph/neo4j_client.py with: connection creation (with startup ping for cold start — see Issue 8), clear-all operation, node write operation (with normalization — see Issue 2), edge write operation (using MERGE for node lookup — see Issue 2), fetch-all-edges operation, and keyword-filtered edge fetch operation.

Write backend/steps/graph_builder.py (Agent 3). Implement section-based chunking for Wikipedia articles. Implement the Nemotron prompt with the JSON extraction rules. Implement JSON parsing by extracting between first and last braces (see Issue 6). Implement Neo4j writes using the client.

Test Agent 3 in isolation with a sample Wikipedia article. Verify the extracted graph looks sensible. Test Cypher reads and confirm the data is in Neo4j.

Add Agent 3 to the LangGraph pipeline (sequential for now, not parallel yet). Run the three-agent pipeline and inspect output.

Commit to GitHub.

---

### Day 4 — Pinecone, Agent 4, Agent 5, and Parallel Execution

Create the Pinecone index. Verify the Gemini embedding dimension before creating (see Issue 3). Add Pinecone credentials to .env.

Write backend/vector/pinecone_client.py with: connection creation, upsert with metadata, and similarity search filtered by namespace.

Write backend/steps/embedder.py (Agent 4). Implement chunking with RecursiveCharacterTextSplitter. Implement the embedding cache. Implement namespace-per-query-id strategy (see Issue 1). Implement Pinecone upserts.

Test Agent 4 in isolation. Verify embeddings are stored and retrievable.

Write backend/steps/retrieval.py (Agent 5). Implement parallel Neo4j and Pinecone queries. Implement graph-fact formatting as plain English sentences. Implement graceful degradation for unavailable databases.

Update backend/pipeline/graph.py to run Agents 3 and 4 in parallel. Add Agent 5 after the parallel join. Run the five-agent pipeline and inspect the combined retrieval context.

Commit to GitHub.

---

### Day 5 — Agent 6, Full Pipeline, and FastAPI

Write backend/steps/generator.py (Agent 6). Implement the prompt with the target audience and source constraint instructions. Implement the retry with 2-second wait on failure.

Connect Agent 6 to the pipeline. Run the full six-agent pipeline on at least five different queries. Inspect output quality — check that the answer uses both graph facts and vector chunks, that citations are present, and that sources are correct.

Write backend/main.py. Set up the FastAPI app with the /query and /health endpoints. Add CORS middleware. Add per-agent timing and build the trace list. Add the startup ping for Neo4j in the lifespan event.

Test FastAPI locally using curl or a tool like Postman. Verify the full response structure including trace data.

Commit to GitHub.

---

### Day 6 — Docker and AWS

Write backend/Dockerfile, frontend/Dockerfile, docker-compose.yml, and nginx/nginx.conf following the specifications in Section 11.

Test Docker Compose locally: verify all three containers start, verify Streamlit can reach FastAPI, verify the full query flow works through Docker.

Launch an EC2 t3.micro instance on AWS with Ubuntu 22.04. Configure the security group. Generate a key pair.

SSH into the instance. Install Docker, Docker Compose, and Git. Clone the repository. Manually create the .env file with real values. Run docker-compose up -d --build. Verify all containers are running and the health endpoint responds.

Write .github/workflows/deploy.yml following Section 13. Add the three GitHub Secrets (EC2_HOST, EC2_USERNAME, EC2_PRIVATE_KEY).

Push a small change to main and verify GitHub Actions runs successfully and the health check passes after deployment.

Commit to GitHub.

---

### Day 7 — React UI, Polish, and README

Write the Vite React app with the three main sections (Hero, AnswerPanel/KnowledgeGraph, PipelineTrace). Implement the React Flow graph visualization.

Test the full flow from the React UI through FastAPI and back. Run at least ten different queries covering different query types. Fix any bugs found.

Write a comprehensive README.md covering: what the project is, the architecture with a text diagram, why GraphRAG (explain dual retrieval), tech stack table, local setup instructions, environment variables guide, how to run with Docker, screenshots of the UI, link to the live AWS demo, and an architecture decisions section.

Record a 2-3 minute demo video showing a full query end to end.

Final commit and push. Verify auto-deploy via GitHub Actions works.