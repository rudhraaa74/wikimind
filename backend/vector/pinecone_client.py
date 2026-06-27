import os
from pinecone import Pinecone
from backend.utils.logger import log_info, log_error, log_warning

class PineconeClient:
    def __init__(self):
        self.api_key = os.getenv("PINECONE_API_KEY")
        self.index_name = os.getenv("PINECONE_INDEX_NAME", "wikimind")
        
        self.pc = None
        self.index = None
        
        if not self.api_key:
            log_warning("SYSTEM", "PineconeClient", "Missing PINECONE_API_KEY in .env. Vector operations will be skipped.")
            return
            
        try:
            self.pc = Pinecone(api_key=self.api_key)
            pinecone_host = os.getenv("PINECONE_HOST")
            if pinecone_host:
                self.index = self.pc.Index(name=self.index_name, host=pinecone_host)
            else:
                self.index = self.pc.Index(self.index_name)
            log_info("SYSTEM", "PineconeClient", f"Connected to Pinecone index: {self.index_name}")
        except Exception as e:
            log_error("SYSTEM", "PineconeClient", f"Failed to connect to Pinecone: {str(e)}")

    def upsert_vectors(self, query_id: str, vectors: list[dict]):
        """
        Upserts a list of vectors to Pinecone. 
        Expects vectors format: [{"id": "...", "values": [...], "metadata": {...}}]
        Uses namespace = query_id.
        """
        if not self.index or not vectors:
            return 0
            
        try:
            # Pinecone has a limit on upsert batch size, safe batch size is 100
            batch_size = 100
            for i in range(0, len(vectors), batch_size):
                batch = vectors[i:i + batch_size]
                self.index.upsert(vectors=batch, namespace=query_id)
                
            return len(vectors)
        except Exception as e:
            log_error(query_id, "PineconeClient", f"Failed to upsert vectors: {str(e)}")
            raise e

    def search_vectors(self, query_id: str, query_embedding: list[float], top_k: int = 5) -> list[dict]:
        """
        Searches Pinecone for similar vectors.
        Always searches within the specific query_id namespace.
        """
        if not self.index:
            return []
            
        try:
            response = self.index.query(
                namespace=query_id,
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True
            )
            
            matches = []
            for match in response.matches:
                matches.append({
                    "id": match.id,
                    "score": match.score,
                    "metadata": match.metadata
                })
            return matches
        except Exception as e:
            log_error(query_id, "PineconeClient", f"Failed to search vectors: {str(e)}")
            return []

    def embed_text(self, text: str, input_type: str = "passage") -> list[float]:
        """
        Embeds text using Pinecone's hosted llama-text-embed-v2.
        input_type should be 'passage' for documents and 'query' for search queries.
        """
        if not self.pc:
            return []
        try:
            res = self.pc.inference.embed(
                model="llama-text-embed-v2",
                inputs=[text],
                parameters={"input_type": input_type, "truncate": "END"}
            )
            return res.data[0].values
        except Exception as e:
            log_error("SYSTEM", "PineconeClient", f"Failed to embed text: {str(e)}")
            return []

    def clear_index(self):
        pass

# Global singleton
pinecone_client = PineconeClient()

if __name__ == "__main__":
    # Test script
    from dotenv import load_dotenv
    import uuid
    import sys
    load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))
    
    client = PineconeClient()
    if not client.index:
        print("Pinecone not configured.")
        sys.exit(0)
        
    test_q_id = str(uuid.uuid4())
    print(f"Upserting test vectors to namespace {test_q_id}...")
    
    test_vectors = [
        {
            "id": "vec1",
            "values": [0.1] * 768, # Dummy embedding
            "metadata": {"text": "Test chunk 1", "title": "Title 1", "url": "http://1"}
        },
        {
            "id": "vec2",
            "values": [0.2] * 768,
            "metadata": {"text": "Test chunk 2", "title": "Title 2", "url": "http://2"}
        }
    ]
    
    client.upsert_vectors(test_q_id, test_vectors)
    
    print("Searching vectors...")
    res = client.search_vectors(test_q_id, [0.15] * 768, top_k=2)
    for r in res:
        print(f" - {r['title']} (score: {r['score']}): {r['text']}")
