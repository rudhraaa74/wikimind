# 🧠 WikiMind

WikiMind is a sophisticated AI-powered search engine and research assistant. It doesn't just return links; it actively reads Wikipedia in real-time, builds an internal knowledge graph, vectorizes text, and synthesizes comprehensive answers using a **Dual-Retrieval (Graph + Vector) RAG pipeline**.

## ✨ Features

- **Live Wikipedia Fetching:** Reads the latest, most up-to-date information directly from Wikipedia.
- **Autonomous Agent Pipeline:** Uses LangGraph to orchestrate a 6-step multi-agent pipeline.
- **Dual-Retrieval RAG:** Combines the semantic search of a Vector Database (Pinecone) with the factual, structural precision of a Knowledge Graph (Neo4j).
- **Graceful Degradation:** If either database fails, the pipeline safely relies on the surviving one.
- **Streaming UI:** Beautiful, dark-mode React interface with real-time streaming tokens and a live pipeline trace.

---

## 🏗 Architecture & The 6-Step Pipeline

The core of WikiMind is built on **LangGraph**, which routes the user's query through the following autonomous steps:

1. **Query Understanding (Agent):** Analyzes the user's prompt, extracts core concepts, and generates optimal search queries.
2. **Fetch:** Hits the Wikipedia API in parallel to download the full text of the necessary articles.
3. **Graph Builder (Agent):** Reads the articles and extracts relationships (e.g., `(Star) -[emits]-> (Light)`) into a **Neo4j AuraDB** Knowledge Graph.
4. **Vector Embedder:** Chunks the articles, creates embeddings, and stores them in a **Pinecone** Vector Database using article titles as namespaces.
5. **Retrieval:** Queries both Neo4j and Pinecone simultaneously to gather factual graph paths and dense text chunks.
6. **Generator (Agent):** Synthesizes all retrieved context into a highly detailed, cited, and streaming response to the user.

---

## 🛠 Tech Stack

**Frontend:**
- React (Vite)
- Tailwind CSS
- Lucide Icons
- Framer Motion

**Backend:**
- Python 3.11
- FastAPI (Uvicorn)
- LangGraph & LangChain
- OpenAI SDK (routing via OpenRouter for Nemotron)
- Google Generative AI (Gemini)

**Databases:**
- **Neo4j** (AuraDB) - Knowledge Graph
- **Pinecone** - Vector Database

**Infrastructure:**
- Docker & Docker Compose
- Nginx Reverse Proxy
- AWS EC2

---

## 🚀 Running Locally (Development)

### 1. Environment Variables
Create a `.env` file in the root directory:

```env
# Neo4j
NEO4J_URI=neo4j+s://<your-db-id>.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password

# Pinecone
PINECONE_API_KEY=your_pinecone_key

# LLMs
GEMINI_API_KEY=your_gemini_key
OPENROUTER_API_KEY=your_openrouter_key
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
```

### 2. Backend Setup
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

---

## 🐳 Running in Production (Docker)

WikiMind is fully containerized. You can deploy it to any server (like an AWS EC2 instance) using Docker Compose.

```bash
# Clone the repository
git clone https://github.com/yourusername/wikimind.git
cd wikimind

# Add your .env file
nano .env 

# Build and start the containers
docker compose up -d --build
```

The application will be served automatically on port `80` via the Nginx reverse proxy. 

> **Note for Small Servers:** The Graph Extraction process is memory-intensive. If running on a 1GB RAM server (like AWS `t3.micro`), you **must** configure a Swap file (e.g., 2GB) to prevent Linux OOM kills during processing.

---

## 📜 License

MIT License
