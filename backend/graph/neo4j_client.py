import os
from neo4j import GraphDatabase
from backend.utils.logger import log_info, log_error, log_warning

class Neo4jClient:
    def __init__(self):
        uri = os.getenv("NEO4J_URI")
        user = os.getenv("NEO4J_USERNAME")
        password = os.getenv("NEO4J_PASSWORD")
        
        self.driver = None
        if not uri or not user or not password:
            log_warning("SYSTEM", "Neo4jClient", "Missing Neo4j credentials in .env. Graph operations will be skipped.")
            return
            
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            self._ping()
        except Exception as e:
            log_error("SYSTEM", "Neo4jClient", f"Failed to connect to Neo4j: {str(e)}")

    def _ping(self):
        """Startup ping to wake up free AuraDB instances from cold start."""
        if not self.driver: return
        try:
            with self.driver.session() as session:
                session.run("RETURN 1")
            log_info("SYSTEM", "Neo4jClient", "Successfully connected and pinged Neo4j AuraDB")
        except Exception as e:
            log_error("SYSTEM", "Neo4jClient", f"Failed to ping Neo4j: {str(e)}")

    def close(self):
        if self.driver:
            self.driver.close()

    def clear_graph(self):
        """Clears all nodes and edges (fresh graph per query as per PLAN.md)."""
        if not self.driver: return
        try:
            with self.driver.session() as session:
                session.run("MATCH (n) DETACH DELETE n")
        except Exception as e:
            log_error("SYSTEM", "Neo4jClient", f"Failed to clear graph: {str(e)}")
            raise e

    def _normalize(self, name: str) -> str:
        return name.strip().lower()

    def merge_relationships(self, relationships: list[dict]):
        """
        Merges relationships. Expects dicts with 'source', 'relation', 'target'.
        Uses MERGE to look up nodes so minor name variations don't cause silent failures.
        """
        if not self.driver or not relationships: return
        query = """
        UNWIND $rels AS rel
        MERGE (a:Entity {name: rel.source})
        MERGE (b:Entity {name: rel.target})
        MERGE (a)-[r:RELATES_TO {type: rel.relation}]->(b)
        """
        # Normalize node names
        normalized_rels = []
        for r in relationships:
            normalized_rels.append({
                "source": self._normalize(r.get("source", "")),
                "relation": r.get("relation", "").strip().lower(),
                "target": self._normalize(r.get("target", ""))
            })
            
        try:
            with self.driver.session() as session:
                session.run(query, rels=normalized_rels)
        except Exception as e:
            log_error("SYSTEM", "Neo4jClient", f"Failed to merge relationships: {str(e)}")
            raise e

    def fetch_all_facts(self) -> list[dict]:
        """Fetches all edges formatted as dictionaries."""
        if not self.driver: return []
        query = """
        MATCH (a:Entity)-[r:RELATES_TO]->(b:Entity)
        RETURN a.name AS source, r.type AS relation, b.name AS target
        LIMIT 50
        """
        facts = []
        try:
            with self.driver.session() as session:
                result = session.run(query)
                for record in result:
                    facts.append({
                        "source": record['source'],
                        "relation": record['relation'],
                        "target": record['target']
                    })
        except Exception as e:
            log_error("SYSTEM", "Neo4jClient", f"Failed to fetch facts: {str(e)}")
            
        return facts

    def fetch_facts_by_keywords(self, keywords: list[str]) -> list[dict]:
        """Finds nodes whose names contain keywords and returns their relationships as dictionaries."""
        if not self.driver or not keywords: return []
        
        normalized_kws = [self._normalize(k) for k in keywords]
        query = """
        UNWIND $keywords AS kw
        MATCH (a:Entity)-[r:RELATES_TO]->(b:Entity)
        WHERE a.name CONTAINS kw OR b.name CONTAINS kw
        RETURN DISTINCT a.name AS source, r.type AS relation, b.name AS target
        LIMIT 50
        """
        facts = []
        try:
            with self.driver.session() as session:
                result = session.run(query, keywords=normalized_kws)
                for record in result:
                    facts.append({
                        "source": record['source'],
                        "relation": record['relation'],
                        "target": record['target']
                    })
        except Exception as e:
            log_error("SYSTEM", "Neo4jClient", f"Failed to fetch facts by keywords: {str(e)}")
            
        return facts
        
    def check_concepts_exist(self, concepts: list[str]) -> dict[str, bool]:
        """
        Checks which of the given concepts exist as nodes in the graph.
        Returns a dictionary mapping concept to a boolean indicating existence.
        """
        if not self.driver or not concepts: 
            return {c: False for c in concepts}
            
        normalized_concepts = [self._normalize(c) for c in concepts]
        query = """
        UNWIND $concepts AS c
        OPTIONAL MATCH (n:Entity)
        WHERE n.name CONTAINS c
        RETURN c AS concept, count(n) > 0 AS exists
        """
        
        result_map = {c: False for c in concepts}
        
        try:
            with self.driver.session() as session:
                result = session.run(query, concepts=normalized_concepts)
                for record in result:
                    # Map normalized concept back if needed, but it's easier to just match them up
                    # Since we UNWIND the normalized list, the 'concept' column holds the normalized name
                    norm_c = record['concept']
                    exists = record['exists']
                    
                    # Find original concept
                    for orig_c in concepts:
                        if self._normalize(orig_c) == norm_c:
                            result_map[orig_c] = exists
                            break
        except Exception as e:
            log_error("SYSTEM", "Neo4jClient", f"Failed to check concept existence: {str(e)}")
            
        return result_map

# Global singleton instance created on startup
neo4j_client = Neo4jClient()

if __name__ == "__main__":
    # Test script
    from dotenv import load_dotenv
    import sys
    load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))
    
    client = Neo4jClient()
    if not client.driver:
        print("Neo4j not configured.")
        sys.exit(0)
        
    print("Clearing graph...")
    client.clear_graph()
    
    print("Merging test relationships...")
    test_rels = [
        {"source": "Transformer", "relation": "is a", "target": "deep learning architecture"},
        {"source": "Transformer", "relation": "developed by", "target": "Google"}
    ]
    client.merge_relationships(test_rels)
    
    print("Fetching facts...")
    facts = client.fetch_all_facts()
    for f in facts:
        print(f" - {f}")
        
    client.close()
