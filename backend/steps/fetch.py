import time
import wikipedia
wikipedia.set_user_agent("WikiMind/1.0 (https://github.com/rudhraaa74/wikimind)")
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Optional

from backend.pipeline.state import GraphState
from backend.utils.logger import log_info, log_error, log_warning

def fetch_single_article(query: str, query_id: str) -> dict[str, Any]:
    """
    Fetches a single Wikipedia article for a given query.
    Returns a dict with article data or an 'error' key if failed.
    """
    try:
        # Get the top search result
        search_results = wikipedia.search(query, results=1)
        if not search_results:
            log_warning(query_id, "Step2_Fetch", f"No Wikipedia results found for query: '{query}'")
            return {"error": f"No results found for '{query}'"}
            
        title = search_results[0]
        
        try:
            page = wikipedia.page(title, auto_suggest=False)
        except wikipedia.exceptions.DisambiguationError as e:
            # Handle Disambiguation by taking the first option (Issue 5)
            log_warning(query_id, "Step2_Fetch", f"Disambiguation for '{title}'. Taking first option: '{e.options[0]}'")
            page = wikipedia.page(e.options[0], auto_suggest=False)
            
        return {
            "title": page.title,
            "summary": page.summary,
            "content": page.content,
            "url": page.url,
            "query": query
        }
        
    except wikipedia.exceptions.PageError:
        log_warning(query_id, "Step2_Fetch", f"PageError: Could not fetch article for '{query}'")
        return {"error": f"Page not found for '{query}'"}
    except Exception as e:
        log_error(query_id, "Step2_Fetch", f"Unexpected error fetching '{query}': {str(e)}", exc_info=True)
        return {"error": f"Unexpected error for '{query}': {str(e)}"}

def fetch_node(state: GraphState) -> dict[str, Any]:
    """
    Step 2: Fetches Wikipedia articles based on the search queries.
    Runs in parallel using ThreadPoolExecutor (Issue 7).
    """
    queries = state.get("wikipedia_queries", [])
    query_id = state["query_id"]
    num_to_fetch = state.get("num_articles", len(queries))
    
    # Do not fetch more than requested
    queries = queries[:num_to_fetch]
    
    log_info(query_id, "Step2_Fetch", f"Starting parallel fetch for {len(queries)} queries", data={"queries": queries})
    start_time = time.time()
    
    articles = []
    fetch_errors = []
    seen_titles = set()
    
    # Execute synchronous Wikipedia API calls in parallel threads
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_query = {executor.submit(fetch_single_article, q, query_id): q for q in queries}
        
        for future in as_completed(future_to_query):
            result = future.result()
            
            if "error" in result:
                fetch_errors.append(result["error"])
            else:
                title = result["title"]
                # Deduplicate by article title
                if title not in seen_titles:
                    seen_titles.add(title)
                    articles.append(result)
                else:
                    log_info(query_id, "Step2_Fetch", f"Skipping duplicate article: '{title}'")
                    
    duration_ms = int((time.time() - start_time) * 1000)
    
    log_info(query_id, "Step2_Fetch", f"Fetched {len(articles)} articles", data={
        "duration_ms": duration_ms,
        "errors": len(fetch_errors)
    })
    
    if len(articles) == 0:
        # If zero articles fetched, record pipeline error. Graph conditional edge will stop execution.
        pipeline_error = "Failed to fetch any Wikipedia articles for the given queries."
        log_error(query_id, "Step2_Fetch", pipeline_error)
        return {
            "articles": [],
            "fetch_errors": fetch_errors,
            "pipeline_error": pipeline_error,
            "trace": [{
                "step": "Wikipedia Fetch",
                "duration_ms": duration_ms,
                "detail": f"Failed to fetch any articles. Errors: {len(fetch_errors)}"
            }]
        }
        
    print(f"\n[METRICS - Wikipedia Fetch]")
    print(f"- Total time taken: {duration_ms / 1000:.2f}s")
    print(f"- Articles successfully fetched: {len(articles)}")
    for a in articles:
        print(f"  * '{a['title']}' summary length: {len(a.get('summary', ''))} chars")
        
    return {
        "articles": articles,
        "fetch_errors": fetch_errors,
        "trace": [{
            "step": "Wikipedia Fetch",
            "duration_ms": duration_ms,
            "detail": f"Successfully fetched {len(articles)} unique articles."
        }]
    }

if __name__ == "__main__":
    # --- Isolated Testing Block (Day 2 Plan) ---
    import uuid
    import json
    
    test_state = {
        "query_id": str(uuid.uuid4()),
        "wikipedia_queries": [
            "Transformer deep learning",
            "Attention machine learning",
            "Transformer deep learning", # Intentional duplicate to test deduplication
            "kljdfsakljdfsaklj"          # Intentional garbage query to test error handling
        ],
        "num_articles": 4
    }
    
    print("Testing Wikipedia Fetch (Parallel)...")
    result = fetch_node(test_state) # type: ignore
    
    print(f"\nFetched {len(result['articles'])} articles.")
    for a in result['articles']:
        print(f" - {a['title']} ({len(a['content'])} bytes from URL: {a['url']})")
    
    if result.get("fetch_errors"):
        print(f"\nErrors: {result['fetch_errors']}")
        
    print(f"\nTrace: {json.dumps(result['trace'], indent=2)}")
