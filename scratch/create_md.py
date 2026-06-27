import json
with open("scratch/graph_output.json", "r") as f:
    edges = json.load(f)
with open("/Users/rudhrakoul/.gemini/antigravity-ide/brain/c7fb70a9-2adf-4d1c-a317-38ed031c50a6/nemotron_graph_facts.md", "w") as f:
    f.write("# Nemotron Graph Facts\n\n")
    f.write("Here are the 57 semantic relationships (facts) extracted by `nvidia/llama-3.3-nemotron-super-49b-v1.5` during the latest run for the query: **How does the Transformer model relate to Self-Attention?**\n\n")
    f.write("| Source Node | Relation | Target Node |\n")
    f.write("|-------------|----------|-------------|\n")
    for edge in edges:
        f.write(f"| {edge['source']} | {edge['relation']} | {edge['target']} |\n")
