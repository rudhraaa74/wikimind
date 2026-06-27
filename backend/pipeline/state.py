import operator
from typing import TypedDict, Annotated, Any, Optional

class GraphState(TypedDict):
    """
    The LangGraph state schema for the WikiMind pipeline.
    All nodes read from and write to this shared state.
    """
    
    # --- Input Fields ---
    query: str
    query_id: str
    
    # --- Step 1 (Query Understanding) Output Fields ---
    core_concepts: list[str]
    wikipedia_queries: list[str]
    query_type: str  # 'explanation', 'comparison', or 'broad'
    num_articles: int
    
    # --- Step 2 (Wikipedia Fetch) Output Fields ---
    articles: list[dict[str, Any]]
    fetch_errors: list[str]
    
    # --- Step 3 (Graph Builder) Output Fields ---
    graph_node_count: int
    graph_edge_count: int
    graph_node_names: list[str]
    graph_nodes: list[dict[str, Any]]  # For UI visualization
    graph_edges: list[dict[str, Any]]  # For UI visualization
    graph_ready: bool
    
    # --- Step 4 (Vector Embedder) Output Fields ---
    chunks_embedded: int
    vector_ready: bool
    
    # --- Step 5 (Dual Retrieval) Output Fields ---
    graph_facts: list[str]
    vector_chunks: list[dict[str, Any]]
    retrieval_sources: list[str]
    
    # --- Step 6 (Generator) Output Fields ---
    answer: str
    sources: list[dict[str, Any]]
    
    # --- Orchestrator & Error Fields ---
    # Annotated with operator.add so additions from parallel nodes (Step 3 & 4) 
    # are merged into a single list rather than overwriting each other.
    trace: Annotated[list[dict[str, Any]], operator.add]
    total_duration_ms: int
    pipeline_error: Optional[str]
