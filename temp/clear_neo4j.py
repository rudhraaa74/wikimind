import os
from dotenv import load_dotenv

load_dotenv("/Users/rudhrakoul/Desktop/wikimind/.env")

from backend.graph.neo4j_client import neo4j_client
neo4j_client.clear_graph()
print("Graph cleared properly!")
