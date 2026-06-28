from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid
import time

from backend.pipeline.orchestrator import run_pipeline
from backend.utils.logger import log_info, log_error

app = FastAPI(title="WikiMind API")

# Allow all origins for the React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    query: str

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/query")
def query_endpoint(request: QueryRequest):
    query_id = str(uuid.uuid4())
    log_info("SYSTEM", "API", f"Received query: '{request.query}'", {"query_id": query_id})
    
    start_time = time.time()
    
    try:
        # Run the orchestrator pipeline
        final_state = run_pipeline(request.query, query_id)
        
        # Calculate total duration from trace
        trace = final_state.get("trace", [])
        total_duration_ms = sum(step.get("duration_ms", 0) for step in trace)
        
        # Format the response exactly as expected by the React frontend
        response_data = {
            "answer": final_state.get("answer", ""),
            "sources": [{"title": article.get("title"), "url": article.get("url")} for article in final_state.get("articles", [])],
            "retrieval_sources": final_state.get("retrieval_sources", []),
            "graph_data": {
                "nodes": final_state.get("graph_nodes", []),
                "edges": final_state.get("graph_edges", [])
            },
            "trace": trace,
            "total_duration_ms": total_duration_ms
        }
        
        log_info("SYSTEM", "API", f"Query completed successfully", {
            "query_id": query_id, 
            "total_duration_ms": total_duration_ms
        })
        
        return response_data
        
    except Exception as e:
        log_error("SYSTEM", "API", f"Pipeline failed: {str(e)}", {"query_id": query_id})
        return {
            "error": "Internal Server Error",
            "message": str(e)
        }
