from langgraph.graph import StateGraph, START, END
from typing import Dict, Any

import os
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

from backend.pipeline.state import GraphState
from backend.steps.query_understanding import query_understanding_node
from backend.steps.fetch import fetch_node
from backend.steps.graph_builder import graph_builder_node
from backend.steps.embedder import embedder_node
from backend.steps.retrieval import retrieval_node
from backend.steps.generator import generator_node

def create_pipeline():
    """
    Creates the main LangGraph pipeline connecting all 6 steps.
    """
    # Initialize the graph
    workflow = StateGraph(GraphState)
    
    # Add nodes
    workflow.add_node("query_understanding", query_understanding_node)
    workflow.add_node("fetch", fetch_node)
    workflow.add_node("graph_builder", graph_builder_node)
    workflow.add_node("vector_embedder", embedder_node)
    workflow.add_node("retrieval", retrieval_node)
    workflow.add_node("generator", generator_node)
    
    # Add edges
    workflow.add_edge(START, "query_understanding")
    workflow.add_edge("query_understanding", "fetch")
    
    # Step 2 -> (Step 3, Step 4) in parallel
    workflow.add_edge("fetch", "graph_builder")
    workflow.add_edge("fetch", "vector_embedder")
    
    # (Step 3, Step 4) -> Step 5
    # Since retrieval needs both to finish, we can add edges from both to retrieval
    # LangGraph will automatically wait for both upstream parallel branches to complete 
    # before executing the downstream node if they both point to it.
    workflow.add_edge("graph_builder", "retrieval")
    workflow.add_edge("vector_embedder", "retrieval")
    
    # Step 5 -> Step 6 -> END
    workflow.add_edge("retrieval", "generator")
    workflow.add_edge("generator", END)
    
    # Compile
    return workflow.compile()

app_graph = create_pipeline()

def run_pipeline(query: str, query_id: str) -> Dict[str, Any]:
    """
    Entrypoint for the FastAPI backend to run the graph.
    """
    initial_state = {
        "query": query,
        "query_id": query_id,
        "core_concepts": [],
        "wikipedia_queries": [],
        "query_type": "explanation",
        "num_articles": 2,
        "articles": [],
        "fetch_errors": [],
        "graph_node_count": 0,
        "graph_edge_count": 0,
        "graph_node_names": [],
        "graph_nodes": [],
        "graph_edges": [],
        "graph_ready": False,
        "embedded_chunks": 0,
        "vector_ready": False,
        "graph_facts": [],
        "vector_chunks": [],
        "retrieval_sources": [],
        "answer": "",
        "sources": [],
        "trace": []
    }
    
    # Execute the graph
    final_state = app_graph.invoke(initial_state)
    
    return final_state

if __name__ == "__main__":
    import uuid
    import os
    
    query = "How do supermassive black holes form and what is their relationship to quasars?"
    query_id = str(uuid.uuid4())
    
    print(f"Running full pipeline for query: '{query}'")
    
    result = run_pipeline(query, query_id)
    
    print("\n--- FINAL ANSWER ---")
    print(result.get("answer"))
    
    print("\n--- TIMING TRACE ---")
    trace = result.get("trace", [])
    for step in trace:
        print(f"[{step['step']}] {step.get('duration_ms', 0)}ms: {step.get('detail', '')}")
        
    print("\n--- BOTTLENECK SUMMARY (Slowest to Fastest) ---")
    sorted_steps = sorted(trace, key=lambda x: x.get('duration_ms', 0), reverse=True)
    for step in sorted_steps:
        print(f"[{step['step']}] {step.get('duration_ms', 0) / 1000:.2f}s")
