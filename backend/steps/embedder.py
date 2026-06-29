import os
import time
import hashlib
from typing import Any
from langchain_text_splitters import RecursiveCharacterTextSplitter

from backend.pipeline.state import GraphState
from backend.utils.logger import log_info, log_error, log_warning
from backend.vector.pinecone_client import pinecone_client

# In-memory embedding cache keyed by hash of chunk text
EMBEDDING_CACHE = {}

def embedder_node(state: GraphState) -> dict[str, Any]:
    """
    Step 4: Vector Embedder.
    Chunks and embeds Wikipedia articles, and stores them in Pinecone.
    Runs in parallel with Graph Builder.
    """
    query_id = state["query_id"]
    articles = state.get("articles", [])
    
    if not articles:
        log_warning(query_id, "Step4_Embedder", "No articles provided in state. Skipping embedding.")
        return {"trace": [{"step": "Vector Embedder", "duration_ms": 0, "detail": "Skipped. No articles."}], "vector_ready": False}
        
    log_info(query_id, "Step4_Embedder", f"Starting embedding for {len(articles)} articles")
    start_time = time.time()
    
    # Text splitter (approx 500 words, 50 word overlap)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        length_function=lambda x: len(x.split())
    )
    
    vectors_to_upsert_by_namespace = {}
    chunk_count = 0
    chunk_counts = {}
    
    for article in articles:
        title = article["title"]
        content = article.get("content", "")
        url = article.get("url", "")
        
        if not content:
            continue
            
        namespace = title.lower().replace(' ', '_')
        print(f"DEBUG: Article '{title}' will use namespace '{namespace}'")
        
        is_skipped = False
        vector_count = 0
        try:
            stats = pinecone_client.index.describe_index_stats()
            namespaces_dict = stats.get('namespaces', {})
            if namespace in namespaces_dict and namespaces_dict[namespace].vector_count > 0:
                vector_count = namespaces_dict[namespace].vector_count
                is_skipped = True
        except Exception:
            pass
            
        if is_skipped:
            log_info(query_id, "Step4_Embedder", f"Namespace already exists with {vector_count} vectors, skipping embedding for article '{title}'")
            print(f"DEBUG: Article '{title}' skipped (Cache hit: {vector_count} vectors in namespace '{namespace}')")
            continue
            
        print(f"DEBUG: Article '{title}' freshly embedded (Namespace '{namespace}' not found or empty)")
            
        chunks = splitter.split_text(content)
        chunk_counts[title] = len(chunks)
        print(f"DEBUG: Created {len(chunks)} chunks for article '{title}'")
        log_info(query_id, "Step4_Embedder", f"Split '{title}' into {len(chunks)} chunks")
        
        for idx, chunk_text in enumerate(chunks):
            chunk_count += 1
            text_hash = hashlib.sha256(chunk_text.encode('utf-8')).hexdigest()
            
            # Check cache
            if text_hash in EMBEDDING_CACHE:
                embedding = EMBEDDING_CACHE[text_hash]
            else:
                try:
                    # Format as recommended for llama-text-embed-v2 passage
                    # No manual prefix needed, just pass the chunk text and input_type='passage'
                    # We can optionally prepend title if useful for the context
                    formatted_content = f"Title: {title if title else 'none'}\n\n{chunk_text}"
                    embedding = pinecone_client.embed_text(formatted_content, input_type="passage")
                    if not embedding:
                        raise Exception("Pinecone returned empty embedding")
                    EMBEDDING_CACHE[text_hash] = embedding
                except Exception as e:
                    log_error(query_id, "Step4_Embedder", f"Failed to embed chunk {idx} of '{title}': {str(e)}")
                    continue
                    
            # Prepare vector for Pinecone
            if namespace not in vectors_to_upsert_by_namespace:
                vectors_to_upsert_by_namespace[namespace] = []
                
            vectors_to_upsert_by_namespace[namespace].append({
                "id": f"{namespace}-{text_hash[:16]}",
                "values": embedding,
                "metadata": {
                    "text": chunk_text,
                    "title": title,
                    "url": url,
                    "chunk_index": idx
                }
            })
            
    # Upsert to Pinecone
    try:
        total_upserted = 0
        for namespace, vectors in vectors_to_upsert_by_namespace.items():
            if vectors:
                print(f"DEBUG: Upserting {len(vectors)} chunks for namespace '{namespace}' in batches")
                upsert_start = time.time()
                pinecone_client.upsert_vectors(namespace, vectors)
                upsert_dur = time.time() - upsert_start
                print(f"DEBUG: Upsert call for '{namespace}' took {upsert_dur:.3f} seconds")
                total_upserted += len(vectors)
                
        if total_upserted > 0:
            log_info(query_id, "Step4_Embedder", f"Successfully upserted {total_upserted} vectors across namespaces")
        vector_ready = True
    except Exception as e:
        log_error(query_id, "Step4_Embedder", f"Failed to upsert to Pinecone: {str(e)}")
        vector_ready = False
        
    duration_ms = int((time.time() - start_time) * 1000)
    
    print(f"\n[METRICS - Vector Embedder]")
    print(f"- Total time taken: {duration_ms / 1000:.2f}s")
    for title, count in chunk_counts.items():
        print(f"  * '{title}': {count} chunks created")
        
    avg_len = 0
    total_vectors = sum(len(v) for v in vectors_to_upsert_by_namespace.values())
    if total_vectors > 0:
        avg_len = sum([sum(len(vec["metadata"]["text"]) for vec in vecs) for vecs in vectors_to_upsert_by_namespace.values()]) / total_vectors
        
    print(f"- Average chunk character length: {avg_len:.0f}")
    print(f"- Total chunks embedded: {total_vectors}")
    
    return {
        "chunks_embedded": total_vectors,
        "vector_ready": vector_ready,
        "trace": [{
            "step": "Vector Embedder",
            "duration_ms": duration_ms,
            "detail": f"Embedded {total_vectors} chunks from {len(articles)} articles."
        }]
    }

if __name__ == "__main__":
    from dotenv import load_dotenv
    import uuid
    import json
    
    load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))
    
    test_state = {
        "query_id": str(uuid.uuid4()),
        "articles": [
            {
                "title": "Transformer (machine learning model)",
                "content": "A transformer is a deep learning architecture developed by Google and based on the multi-head attention mechanism. " * 30, # dummy long content
                "url": "http://example.com/transformer"
            }
        ]
    }
    
    print("Testing Vector Embedder...")
    result = embedder_node(test_state) # type: ignore
    
    print(f"\nResult:")
    print(json.dumps(result, indent=2))
