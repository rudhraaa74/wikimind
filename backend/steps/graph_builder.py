import os
import json
import time
import concurrent.futures
from typing import Any
from openai import OpenAI

from backend.pipeline.state import GraphState
from backend.utils.logger import log_info, log_error, log_warning
from backend.graph.neo4j_client import neo4j_client

SYSTEM_PROMPT = """
You are an expert knowledge extraction agent specializing in space and astronomy.
Your task is to read a section of text from Wikipedia and extract as many highly detailed factual relationships as possible to build a comprehensive space and astronomy knowledge graph.
Extract at least 15 to 30 relationships per section if possible. Capture both high-level concepts and granular, specific details to ensure the resulting LLM response is extremely well-informed.

ENTITY NORMALIZATION RULES:
- Use the shortest canonical name for every entity. "black hole" not "black hole object"
- Never create two nodes for the same concept even if it appears under different names
- Remove all parenthetical clarifications. "event horizon" not "event horizon (boundary)"
- Lowercase all node names except proper nouns and acronyms like NASA, ESA, ISRO, SpaceX, JWST, Hubble
- Never use years, numbers or dates as nodes
- Never create nodes for generic terms that have no specific astronomical meaning such as "system", "process", "method", "event", or "object"
- Always use singular forms. "star" not "stars", "black hole" not "black holes", "galaxy" not "galaxies"
- Never create a more specific version of a node that already exists. If "accretion disk" exists do not create "accretion disk around black hole"
- Always prefer the shortest unambiguous name. "general relativity" not "theory of general relativity", "gravitational collapse" not "process of gravitational collapse"
- Never create nodes for vague descriptive words that carry no specific astronomical meaning such as "surroundings", "matter", "temperature", "compression", "researchers", "astronomers", "light", "radiation" unless they refer to a specific named phenomenon like "hawking radiation" or "cosmic microwave background"

EXTRACTION RULES:
- Relation names must be specific and directional. Use "orbits", "discovered", "launched by", "observes", "emits", "contains", "classified as" rather than vague relations like "related to", "associated with", or "part of"
- When the same entity appears as both source and target across different relationships that is good — it means the node is well connected in the graph which improves traversal quality
- Extract relationships between entities even when they are implicitly stated in the text, not just explicitly stated facts
- Never create a relationship where the source and target are the same node
- If two entity names refer to the same concept always merge them into one canonical name before creating any relationship

DOMAIN CONTEXT (SPACE AND ASTRONOMY):
You are building a permanent space and astronomy knowledge graph that will be queried by space enthusiasts and astronomers.
Prioritize extracting these specific entity types:
- Celestial bodies (planets, stars, galaxies, nebulae, black holes)
- Space missions (crewed and uncrewed)
- Spacecraft and rockets
- Space agencies (NASA, ESA, ISRO, SpaceX, etc.)
- Telescopes and observatories (ground-based and space-based)
- Astronomical phenomena (supernovae, gravitational waves, cosmic microwave background)
- Named scientists and astronomers only — never generic "researchers" or "astronomers" as nodes
- Key discoveries referenced by name
- Scientific instruments referenced by name

The goal is a clean precise graph of interconnected space knowledge where every node is a meaningful named astronomical entity with no duplicates and no generic filler nodes.

Output ONLY valid JSON matching this structure exactly:
{
  "relationships": [
    {
      "source": "James Webb Space Telescope",
      "relation": "observes",
      "target": "exoplanet atmospheres"
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
        
    core_concepts = state.get("core_concepts", [])
    
    if core_concepts:
        concept_existence = neo4j_client.check_concepts_exist(core_concepts)
        existing_concepts = [c for c, exists in concept_existence.items() if exists]
        
        if len(core_concepts) > 0 and (len(existing_concepts) / len(core_concepts)) >= 0.7:
            log_info(query_id, "Step3_GraphBuilder", f"Reusing existing graph data for concepts {', '.join(existing_concepts)} — skipping graph build")
            return {"trace": [{"step": "Graph Builder", "duration_ms": 0, "detail": f"Skipped graph build. Concepts {', '.join(existing_concepts)} already exist."}], "graph_ready": True}
            
        # Filter articles to only process those we don't already have in the graph
        article_titles = [a["title"] for a in articles]
        title_existence = neo4j_client.check_concepts_exist(article_titles)
        
        articles = [a for a in articles if not title_existence.get(a["title"], False)]
        if not articles:
            log_info(query_id, "Step3_GraphBuilder", "All articles already exist in graph — skipping graph build")
            return {"trace": [{"step": "Graph Builder", "duration_ms": 0, "detail": "Skipped. All articles already in graph."}], "graph_ready": True}
            
    log_info(query_id, "Step3_GraphBuilder", f"Starting extraction on {len(articles)} articles")
    start_time = time.time()
    
    

    client = OpenAI(
        base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        api_key=os.getenv("OPENROUTER_API_KEY"),
        timeout=90.0,
    )
    all_extracted_facts = []
    
    call_metrics = []
    
    def process_article(article):
        title = article["title"]
        content_to_process = article.get("summary", "")
        
        if not content_to_process:
            return []
            
        log_info(query_id, "Step3_GraphBuilder", f"Extracting graph from article: '{title}'")
        prompt = f"Extract the key relationships from this text about '{title}':\n\n{content_to_process}"
        
        call_start = time.time()
        response = None
        for attempt in range(2):
            try:
                response = client.chat.completions.create(
                    model="nemotron-3-super-120b-a12b:free",
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.0
                )
                break
            except Exception as e:
                log_warning(query_id, "Step3_GraphBuilder", f"Attempt {attempt + 1} failed for '{title}': {str(e)}")
                if attempt == 0:
                    time.sleep(3)
                    
        try:
            if not response:
                raise Exception("Max retries reached")
            
            # Safely parse JSON even if wrapped in markdown blocks
            text = response.choices[0].message.content.strip("` \n")
            if text.startswith("json"): text = text[4:]
            
            # Robust JSON extraction
            start_idx = text.find('{')
            end_idx = text.rfind('}')
            if start_idx != -1 and end_idx != -1:
                text = text[start_idx:end_idx+1]
                
            result_json = json.loads(text.strip())
            
            extracted = result_json.get("relationships", [])
            
            # Write to Neo4j
            if extracted:
                neo4j_client.merge_relationships(extracted)
            
            facts = []
            for rel in extracted:
                fact_str = f"({rel['source']}) -[{rel['relation']}]-> ({rel['target']})"
                facts.append(fact_str)
                
            call_dur = time.time() - call_start
            call_metrics.append({
                "duration": call_dur,
                "facts": len(extracted),
                "prompt_len": len(prompt)
            })
            
            log_info(query_id, "Step3_GraphBuilder", f"Extracted {len(extracted)} facts from '{title}'")
            return facts
            
        except Exception as e:
            log_error(query_id, "Step3_GraphBuilder", f"Failed to extract from '{title}': {str(e)}")
            return []

    # Execute with ThreadPoolExecutor (max 2 concurrent API calls)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(process_article, articles))
        
    for res in results:
        all_extracted_facts.extend(res)

    duration_ms = int((time.time() - start_time) * 1000)
    
    print(f"\n[METRICS - Graph Builder]")
    print(f"- Total time taken: {duration_ms / 1000:.2f}s")
    print(f"- Articles processed: {len(articles)}")
    print(f"- Total Nemotron API calls made: {len(call_metrics)}")
    for i, m in enumerate(call_metrics):
        print(f"  * Call {i+1}: Duration={m['duration']:.2f}s, Facts extracted={m['facts']}, Text sent length={m['prompt_len']} chars")
        
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
