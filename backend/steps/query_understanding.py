import os
import json
import time
import google.generativeai as genai
from typing import Any

from backend.pipeline.state import GraphState
from backend.utils.logger import log_info, log_error, log_warning

SYSTEM_PROMPT = """
You are an expert space and astronomy research planner. Your job is to analyze a user's query about space and astronomy and produce a structured search plan for Wikipedia.

Follow these strict rules:
1. Expand abbreviations and acronyms relevant to space and astronomy. For example "JWST" becomes "James Webb Space Telescope", "CMB" becomes "cosmic microwave background", "ISS" becomes "International Space Station".
2. Generate search queries that match likely Wikipedia article titles as closely as possible.
   - Prefer short, precise queries over long descriptive ones.
   - Wikipedia search is extremely sensitive to exact phrasing — a wrong word returns the wrong article.
   - For example: use "Black hole" not "black hole astronomy phenomenon space".
   - Do NOT add extra words unless they are part of the actual Wikipedia article title.
   - Only append domain context when the term is genuinely ambiguous. For example "corona" is ambiguous so use "corona (astronomy)". But "neutron star" is already unambiguous — do not add extra words.
   - Always prefer the most specific Wikipedia article title. For example for a query about the James Webb Space Telescope use "James Webb Space Telescope" not just "space telescope".
3. Identify core concepts which are the key astronomical entities, phenomena, missions or objects the user is asking about.
4. Determine the query type:
   - 'explanation': user is asking about one specific concept such as a single celestial body, phenomenon or mission. Set num_articles to 2.
   - 'comparison': user is comparing multiple astronomical concepts or missions. Set num_articles to 3.
   - 'broad': user is asking for an overview of a broad topic like the history of space exploration or the life cycle of stars. Set num_articles to 3 or 4.
5. Output ONLY valid JSON matching this structure exactly. No markdown, no backticks, no explanation text:
{
  "core_concepts": ["black hole", "event horizon"],
  "wikipedia_queries": ["Black hole", "Event horizon"],
  "query_type": "explanation",
  "num_articles": 2
}
"""

def query_understanding_node(state: GraphState) -> dict[str, Any]:
    """
    Step 1: Analyzes the user query and produces a search plan.
    Reads 'query' from state and returns 'core_concepts', 'wikipedia_queries', 
    'query_type', 'num_articles', and 'trace'.
    """
    query = state["query"]
    query_id = state["query_id"]
    
    log_info(query_id, "Step1_QueryUnderstanding", f"Starting query understanding for: {query}")
    start_time = time.time()
    
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
    model = genai.GenerativeModel(
        model_name="gemma-4-31b-it",
        system_instruction=SYSTEM_PROMPT,
    )
    
    # Retry logic: retry once on failure
    for attempt in range(2):
        try:
            response = model.generate_content(f"User Query: {query}")
            
            import re
            text = response.text
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                text = match.group(0)
            else:
                log_warning(query_id, "Step1_QueryUnderstanding", f"No JSON block found in response: {text}")
                
            result = json.loads(text.strip())
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            log_info(query_id, "Step1_QueryUnderstanding", "Successfully generated search plan", data={
                "duration_ms": duration_ms,
                "plan": result
            })
            
            print(f"\n[METRICS - Query Understanding]")
            print(f"- Total time taken: {duration_ms / 1000:.2f}s")
            print(f"- Number of Wikipedia queries generated: {len(result['wikipedia_queries'])}")
            print(f"- Query type detected: {result['query_type']}")
            
            return {
                "core_concepts": result["core_concepts"],
                "wikipedia_queries": result["wikipedia_queries"],
                "query_type": result["query_type"],
                "num_articles": result["num_articles"],
                "trace": [{
                    "step": "Query Understanding",
                    "duration_ms": duration_ms,
                    "detail": f"Generated '{result['query_type']}' search plan with {len(result['wikipedia_queries'])} queries."
                }]
            }
            
        except Exception as e:
            log_error(query_id, "Step1_QueryUnderstanding", f"Attempt {attempt + 1} failed: {str(e)}", exc_info=True)
            time.sleep(1)
            
    # Fallback
    log_warning(query_id, "Step1_QueryUnderstanding", "Both Gemini attempts failed. Using fallback keywords.")
    fallback_queries = [word.strip() for word in query.split() if len(word) > 3]
    if not fallback_queries:
        fallback_queries = [query]
        
    duration_ms = int((time.time() - start_time) * 1000)
    
    print(f"\n[METRICS - Query Understanding]")
    print(f"- Total time taken: {duration_ms / 1000:.2f}s")
    print(f"- Number of Wikipedia queries generated: {len(fallback_queries)}")
    print(f"- Query type detected: broad")
    
    return {
        "core_concepts": fallback_queries,
        "wikipedia_queries": fallback_queries,
        "query_type": "broad",
        "num_articles": 2,
        "trace": [{
            "step": "Query Understanding",
            "duration_ms": duration_ms,
            "detail": "Failed to contact LLM. Used simple keyword split fallback."
        }]
    }

if __name__ == "__main__":
    from dotenv import load_dotenv
    import uuid
    
    load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))
    
    test_queries = [
        "Explain backpropagation",
        "Difference between RNN and LSTM",
        "History of artificial intelligence"
    ]
    
    for q in test_queries:
        print(f"\n--- Testing Query: '{q}' ---")
        dummy_state = {"query": q, "query_id": str(uuid.uuid4())}
        result_state = query_understanding_node(dummy_state)
        print(json.dumps(result_state, indent=2))
