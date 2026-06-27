import os
import json
from dotenv import load_dotenv, find_dotenv
from neo4j import GraphDatabase

# Load environment variables
load_dotenv(find_dotenv())

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

def fetch_graph():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
    
    with driver.session() as session:
        # Fetch the most recent edges added to the graph (limiting to 100 for readability)
        result = session.run("""
            MATCH (n)-[r]->(m)
            RETURN n.name AS source, r.type AS relation, m.name AS target
            LIMIT 100
        """)
        
        edges = []
        for record in result:
            edges.append({
                "source": record["source"],
                "relation": record["relation"],
                "target": record["target"]
            })
            
    driver.close()
    
    with open("scratch/graph_output.json", "w") as f:
        json.dump(edges, f, indent=2)
        
    print(f"Extracted {len(edges)} relationships from Neo4j and saved to scratch/graph_output.json")
    for edge in edges[:15]:
        print(f"{edge['source']} -[{edge['relation']}]-> {edge['target']}")
    if len(edges) > 15:
        print(f"... and {len(edges) - 15} more")

if __name__ == "__main__":
    fetch_graph()
