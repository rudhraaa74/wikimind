import os
from dotenv import load_dotenv

load_dotenv("/Users/rudhrakoul/Desktop/wikimind/.env")

# Clear Neo4j
from backend.graph.neo4j_client import neo4j_client
print("Clearing Neo4j...")
neo4j_client.clear_graph()
print("Neo4j cleared.")

# Clear Pinecone
from backend.vector.pinecone_client import pinecone_client
print("Clearing Pinecone...")
if pinecone_client.index:
    stats = pinecone_client.index.describe_index_stats()
    namespaces = stats.get("namespaces", {}).keys()
    for ns in namespaces:
        print(f"Deleting namespace: {ns}")
        pinecone_client.index.delete(delete_all=True, namespace=ns)
    print("Pinecone cleared.")
