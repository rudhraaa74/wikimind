import os
import json
from dotenv import load_dotenv

load_dotenv("/Users/rudhrakoul/Desktop/wikimind/.env")

from backend.graph.neo4j_client import neo4j_client
if neo4j_client.driver:
    with neo4j_client.driver.session() as session:
        result = session.run("MATCH (a:Entity)-[r]->(b:Entity) WHERE a.name = 'general relativity' OR b.name = 'general relativity' RETURN a.name, type(r), r.type, b.name")
        for record in result:
            print(f"({record['a.name']}) -[{record['r.type']}]-> ({record['b.name']})")
