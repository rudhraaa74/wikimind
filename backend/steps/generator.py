import os
import time
from typing import Any
from openai import OpenAI

from backend.pipeline.state import GraphState
from backend.utils.logger import log_info, log_error

SYSTEM_PROMPT = """
You are WikiMind, a highly intelligent and factual AI assistant.
Your task is to answer the user's query using ONLY the provided context.

The context is provided in two forms:
1. GRAPH FACTS: Structured semantic relationships extracted from Wikipedia.
2. TEXT CHUNKS: Unstructured text snippets from Wikipedia articles.

Rules:
1. Answer the user's query directly and comprehensively.
2. You MUST cite your sources inline using the exact format: [Source: Article Title].
   For example: "The Transformer was introduced in 2017 [Source: Attention Is All You Need]."
3. If the provided context does not contain enough information to answer the query, clearly state that you do not have enough information. Do NOT hallucinate.
4. Keep the tone professional, objective, and analytical.
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
    
    log_info(query_id, "Step6_Generator", f"Starting generation. Context: {len(graph_facts)} facts, {len(vector_chunks)} chunks")
    start_time = time.time()
    
    # 1. Build context string
    context_str = "--- GRAPH FACTS ---\n"
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
    client = OpenAI(
        base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        api_key=os.getenv("OPENROUTER_GENERATOR_API_KEY", os.getenv("OPENROUTER_API_KEY")),
    )
    
    answer = ""
    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b:free",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0
        )
        answer = response.choices[0].message.content.strip()
    except Exception as e:
        log_error(query_id, "Step6_Generator", f"Failed to generate answer: {str(e)}")
        answer = "I'm sorry, I encountered an error while generating the response."
        
    duration_ms = int((time.time() - start_time) * 1000)
    
    log_info(query_id, "Step6_Generator", "Successfully generated final answer", data={
        "duration_ms": duration_ms,
        "answer_length": len(answer)
    })
    
    return {
        "answer": answer,
        "sources": sources_list,
        "trace": [{"step": "Generator", "duration_ms": duration_ms, "detail": "Generated final answer"}]
    }
