import os
from dotenv import load_dotenv
load_dotenv()
from backend.vector.pinecone_client import pinecone_client

stats = pinecone_client.index.describe_index_stats()
namespaces = stats.get('namespaces', {})
print("Namespaces:", namespaces)
