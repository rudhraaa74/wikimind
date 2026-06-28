import os
import time
from typing import Any
import google.generativeai as genai

from backend.pipeline.state import GraphState
from backend.utils.logger import log_info, log_error

SYSTEM_PROMPT = """
You are WikiMind, an expert space and astronomy assistant with deep knowledge of astrophysics, planetary science, space exploration history, and cosmology. Your target audience is space enthusiasts and astronomers with technical interest — they understand concepts like orbital mechanics, spectroscopy, and stellar evolution so do not over-explain basics. Provide technically rich and precise answers using proper astronomical terminology.

Your task is to answer the user's query using ONLY the provided context. The context is provided in two forms:
1. GRAPH FACTS: Structured semantic relationships extracted from Wikipedia
2. TEXT CHUNKS: Unstructured text snippets from Wikipedia articles

Rules:
1. Answer the query directly, comprehensively and with technical depth appropriate for an informed space enthusiast
2. Cite sources inline using numbers in brackets like [1] [2]. At the end of your response include a References section listing each source by number. Only cite sources listed under SOURCES in the context
3. When graph facts and text chunks agree on a point, treat that as high confidence information
4. When the context contains rich detail on a topic go deep — do not give a surface level answer when the data supports more
5. If the context does not contain enough information to answer the query fully, state clearly what you do and do not have information about. Do not hallucinate or fill gaps with general knowledge
6. Keep tone professional, precise and analytical — like a knowledgeable scientist explaining to a curious colleague
"""

def generator_node(state: GraphState) -> dict[str, Any]:
    """
    Step 6: Generator.
    Synthesizes the final answer using retrieved graph facts and vector chunks.
    """
    query_id = state["query_id"]
    query = state["query"]
    
    graph_facts = state.get("graph_facts", [])
    vector_chunks = state.get("vector_chunks", [])
    articles = state.get("articles", [])
    
    log_info(query_id, "Step6_Generator", f"Starting generation. Context: {len(graph_facts)} facts, {len(vector_chunks)} chunks")
    start_time = time.time()
    
    # 1. Build context string
    context_str = "SOURCES (use ONLY these numbers for inline citations [1], [2], etc):\n"
    for idx, article in enumerate(articles, start=1):
        context_str += f"{idx}. {article.get('title', 'Unknown')}\n"
        
    context_str += "\nGRAPH FACTS:\n"
    if graph_facts:
        for fact in graph_facts:
            context_str += f"- {fact}\n"
    else:
        context_str += "(No graph facts retrieved)\n"
        
    context_str += "\n--- TEXT CHUNKS ---\n"
    sources_set = set()
    sources_list = []
    
    if vector_chunks:
        for chunk in vector_chunks:
            title = chunk.get("title", "Unknown Source")
            text = chunk.get("text", "")
            context_str += f"Title: {title}\nContent: {text}\n\n"
            
            # Deduplicate sources for the final output
            if title not in sources_set:
                sources_set.add(title)
                sources_list.append({"title": title, "url": chunk.get("url", "")})
    else:
        context_str += "(No text chunks retrieved)\n"
        
    prompt = f"USER QUERY: {query}\n\n{context_str}"
    
    # 2. Call LLM
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
    model = genai.GenerativeModel(
        model_name="gemini-3.1-flash-lite",
        system_instruction=SYSTEM_PROMPT,
        generation_config={"temperature": 0.0, "max_output_tokens": 2000}
    )
    
    answer = ""
    for attempt in range(2):
        try:
            response = model.generate_content(prompt)
            answer = response.text.strip()
            break
        except Exception as e:
            if attempt == 0:
                time.sleep(2)
            else:
                log_error(query_id, "Step6_Generator", f"Failed to generate answer: {str(e)}")
                answer = "I'm sorry, I encountered an error while generating the response."
        
    duration_ms = int((time.time() - start_time) * 1000)
    
    log_info(query_id, "Step6_Generator", "Successfully generated final answer", data={
        "duration_ms": duration_ms,
        "answer_length": len(answer)
    })
    
    print(f"\n[METRICS - Generator]")
    print(f"- Total time taken: {duration_ms / 1000:.2f}s")
    print(f"- Total graph facts sent: {len(graph_facts)}")
    print(f"- Total vector chunks sent: {len(vector_chunks)}")
    print(f"- Full prompt char length: {len(SYSTEM_PROMPT) + len(prompt)}")
    
    return {
        "answer": answer,
        "sources": sources_list,
        "trace": [{"step": "Generator", "duration_ms": duration_ms, "detail": "Generated final answer"}]
    }
