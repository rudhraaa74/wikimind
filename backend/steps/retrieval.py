import os
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from backend.pipeline.state import GraphState
from backend.utils.logger import log_info, log_error, log_warning
from backend.graph.neo4j_client import neo4j_client
from backend.vector.pinecone_client import pinecone_client

def retrieve_from_graph(query_id: str, core_concepts: list[str]) -> dict:
    """Retrieves facts from Neo4j."""
    raw_facts = []
    

    # 2. Fetch facts specifically related to core concepts
    concept_facts = neo4j_client.fetch_facts_by_keywords(core_concepts)
    raw_facts.extend(concept_facts)
        
    # Deduplicate facts
    unique_facts = {f"{f['source']}|{f['relation']}|{f['target']}": f for f in raw_facts}.values()
    
    facts_str = []
    nodes_set = set()
    edges_list = []
    
    for f in unique_facts:
        facts_str.append(f"{f['source']} {f['relation']} {f['target']}")
        nodes_set.add(f['source'])
        nodes_set.add(f['target'])
        edges_list.append({"source": f['source'], "target": f['target'], "type": f['relation']})
        
    return {
        "graph_facts": facts_str,
        "graph_nodes": list(nodes_set),
        "graph_edges": edges_list
    }

def retrieve_from_vector(query_id: str, query_text: str, articles: list[dict]) -> list[dict]:
    """Embeds the query and searches Pinecone."""
    try:
        # We pass the query text and input_type='query' for llama-text-embed-v2
        query_embedding = pinecone_client.embed_text(query_text, input_type="query")
        if not query_embedding:
            raise Exception("Pinecone returned empty embedding")
    except Exception as e:
        log_error(query_id, "Step5_Retrieval", f"Failed to embed search query: {str(e)}")
        return []
        
    all_results = []
    
    for article in articles:
        title = article.get("title")
        if not title:
            continue
        namespace = title.lower().replace(' ', '_')
        results = pinecone_client.search_vectors(namespace, query_embedding, top_k=15)
        all_results.extend(results)
        
    # Sort all results by score descending and return top 15 overall
    all_results.sort(key=lambda x: x.get("score", 0), reverse=True)
    return all_results[:15]

def retrieval_node(state: GraphState) -> dict[str, Any]:
    """
    Step 5: Dual Retrieval.
    Retrieves context from Neo4j and Pinecone in parallel.
    """
    query_id = state["query_id"]
    query_text = state["query"]
    core_concepts = state.get("core_concepts", [])
    articles = state.get("articles", [])
    
    graph_ready = state.get("graph_ready", False)
    vector_ready = state.get("vector_ready", False)
    
    log_info(query_id, "Step5_Retrieval", f"Starting retrieval. Graph ready: {graph_ready}, Vector ready: {vector_ready}")
    start_time = time.time()
    
    graph_facts = []
    graph_nodes = []
    graph_edges = []
    vector_chunks = []
    retrieval_sources = []
    
    # Run in parallel
    with ThreadPoolExecutor(max_workers=2) as executor:
        graph_future = None
        vector_future = None
        
        if graph_ready:
            graph_future = executor.submit(retrieve_from_graph, query_id, core_concepts)
            retrieval_sources.append("Neo4j")
        else:
            retrieval_sources.append("Graph unavailable")
            
        if vector_ready:
            vector_future = executor.submit(retrieve_from_vector, query_id, query_text, articles)
            retrieval_sources.append("Pinecone")
        else:
            retrieval_sources.append("Vector unavailable")
            
        # Collect results
        if graph_future:
            try:
                graph_res = graph_future.result()
                graph_facts = graph_res.get("graph_facts", [])
                graph_nodes = graph_res.get("graph_nodes", [])
                graph_edges = graph_res.get("graph_edges", [])
            except Exception as e:
                log_error(query_id, "Step5_Retrieval", f"Graph retrieval failed: {str(e)}")
                
        if vector_future:
            try:
                vector_chunks = vector_future.result()
            except Exception as e:
                log_error(query_id, "Step5_Retrieval", f"Vector retrieval failed: {str(e)}")
                
    duration_ms = int((time.time() - start_time) * 1000)
    
    log_info(query_id, "Step5_Retrieval", "Retrieval complete", data={
        "duration_ms": duration_ms,
        "graph_facts_count": len(graph_facts),
        "vector_chunks_count": len(vector_chunks),
        "sources": retrieval_sources
    })
    
    print(f"\n[METRICS - Dual Retrieval]")
    print(f"- Total time taken: {duration_ms / 1000:.2f}s")
    print(f"- Graph facts retrieved: {len(graph_facts)}")
    print(f"- Vector chunks retrieved: {len(vector_chunks)}")
    print(f"- Retrieval sources used: {', '.join(retrieval_sources)}")
    
    return {
        "graph_facts": graph_facts,
        "graph_nodes": graph_nodes,
        "graph_edges": graph_edges,
        "vector_chunks": vector_chunks,
        "retrieval_sources": retrieval_sources,
        "trace": [{
            "step": "Dual Retrieval",
            "duration_ms": duration_ms,
            "detail": f"Retrieved {len(graph_facts)} graph facts and {len(vector_chunks)} vector chunks."
        }]
    }

if __name__ == "__main__":
    from dotenv import load_dotenv
    import uuid
    import json
    
    load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))
    
    test_state = {
        "query_id": str(uuid.uuid4()),
        "query": "What is a Transformer?",
        "core_concepts": ["Transformer"],
        "graph_ready": True,
        "vector_ready": True
    }
    
    print("Testing Dual Retrieval...")
    result = retrieval_node(test_state) # type: ignore
    
    print(f"\nResult:")
    print(json.dumps(result, indent=2))
