import os
import json
import time
from typing import Any
from openai import OpenAI

from backend.pipeline.state import GraphState
from backend.utils.logger import log_info, log_error, log_warning
from backend.graph.neo4j_client import neo4j_client

SYSTEM_PROMPT = """
You are an expert knowledge extraction agent.
Your task is to read a section of text from Wikipedia and extract as many highly detailed factual relationships as possible to build a comprehensive knowledge graph.
Extract at least 15 to 30 relationships per section if possible. Capture both high-level concepts and granular, specific details to ensure the resulting LLM response is extremely well-informed.

Output ONLY valid JSON matching this structure exactly:
{
  "relationships": [
    {
      "source": "The source entity (e.g., 'Transformer')",
      "relation": "The relationship (e.g., 'introduced in')",
      "target": "The target entity (e.g., '2017')"
    }
  ]
}
"""

def graph_builder_node(state: GraphState) -> dict[str, Any]:
    """
    Step 3 (Agent): Graph Builder.
    Processes Wikipedia articles to extract entities and relationships.
    Handles per-article failures autonomously.
    """
    query_id = state["query_id"]
    articles = state.get("articles", [])
    
    if not articles:
        log_warning(query_id, "Step3_GraphBuilder", "No articles provided in state. Skipping extraction.")
        return {"trace": [{"step": "Graph Builder", "duration_ms": 0, "detail": "Skipped. No articles."}], "graph_ready": False}
        
    log_info(query_id, "Step3_GraphBuilder", f"Starting extraction on {len(articles)} articles")
    start_time = time.time()
    
    # Clear existing graph for this new query
    try:
        neo4j_client.clear_graph()
    except Exception as e:
        log_error(query_id, "Step3_GraphBuilder", f"Failed to clear graph: {str(e)}")
        # If we can't clear, we can't build a clean graph. Degrade gracefully.
        return {"trace": [{"step": "Graph Builder", "duration_ms": int((time.time() - start_time) * 1000), "detail": "Failed to access Neo4j."}], "graph_ready": False}
    
    client = OpenAI(
        base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        api_key=os.getenv("OPENROUTER_API_KEY"),
    )
    all_extracted_facts = []
    
    for article in articles:
        title = article["title"]
        content_to_process = article.get("summary", "")
        
        if not content_to_process:
            continue
            
        log_info(query_id, "Step3_GraphBuilder", f"Extracting graph from article: '{title}'")
        prompt = f"Extract the key relationships from this text about '{title}':\n\n{content_to_process}"
        
        try:
            response = client.chat.completions.create(
                model="nvidia/llama-3.3-nemotron-super-49b-v1.5",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0
            )
            
            # Safely parse JSON even if wrapped in markdown blocks
            text = response.choices[0].message.content.strip("` \n")
            if text.startswith("json"): text = text[4:]
            result_json = json.loads(text.strip())
            
            extracted = result_json.get("relationships", [])
            
            # Write to Neo4j
            if extracted:
                neo4j_client.merge_relationships(extracted)
            
            for rel in extracted:
                fact_str = f"({rel['source']}) -[{rel['relation']}]-> ({rel['target']})"
                all_extracted_facts.append(fact_str)
                
            log_info(query_id, "Step3_GraphBuilder", f"Extracted {len(extracted)} facts from '{title}'")
            
        except Exception as e:
            log_error(query_id, "Step3_GraphBuilder", f"Failed to extract from '{title}': {str(e)}")
            continue

    duration_ms = int((time.time() - start_time) * 1000)
    
    log_info(query_id, "Step3_GraphBuilder", f"Total facts extracted: {len(all_extracted_facts)}", data={"duration_ms": duration_ms})
    
    return {
        "graph_facts": all_extracted_facts,
        "graph_node_count": len(all_extracted_facts) * 2, # Approximation for UI if needed
        "graph_edge_count": len(all_extracted_facts),
        "graph_ready": True,
        "trace": [{
            "step": "Graph Builder",
            "duration_ms": duration_ms,
            "detail": f"Agent extracted {len(all_extracted_facts)} relationships from {len(articles)} articles."
        }]
    }

if __name__ == "__main__":
    from dotenv import load_dotenv
    import uuid
    
    load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))
    
    test_state = {
        "query_id": str(uuid.uuid4()),
        "articles": [
            {
                "title": "Transformer (machine learning model)",
                "summary": "A transformer is a deep learning architecture developed by Google and based on the multi-head attention mechanism, proposed in a 2017 paper 'Attention Is All You Need'. It is widely used in natural language processing."
            },
            {
                "title": "Recurrent neural network",
                "summary": "A recurrent neural network (RNN) is a class of artificial neural networks where connections between nodes can create a cycle, allowing output from some nodes to affect subsequent input to the same nodes."
            }
        ]
    }
    
    print("Testing Graph Builder Agent...")
    result = graph_builder_node(test_state) # type: ignore
    
    print(f"\nExtracted Facts ({len(result.get('graph_facts', []))}):")
    for fact in result.get("graph_facts", []):
        print(f" - {fact}")
        
    print(f"\nTrace: {json.dumps(result['trace'], indent=2)}")
