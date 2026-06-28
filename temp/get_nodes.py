import os
import json
from dotenv import load_dotenv

load_dotenv("/Users/rudhrakoul/Desktop/wikimind/.env")

from backend.graph.neo4j_client import neo4j_client
if neo4j_client.driver:
    with neo4j_client.driver.session() as session:
        result = session.run("MATCH (n:Entity) RETURN n.name as name")
        nodes = sorted(list(set([record["name"] for record in result])))
        print(json.dumps(nodes, indent=2))
        print(f"\nTotal nodes: {len(nodes)}")
