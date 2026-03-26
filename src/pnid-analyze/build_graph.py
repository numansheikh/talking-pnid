"""
P&ID Graph Builder
Step B: Clean unified JSON → Step A: Build + visualize NetworkX graph
"""

import json
import networkx as nx
from pyvis.network import Network

# ── Load ──────────────────────────────────────────────────────────────────────
with open("unified_pid_graph.json") as f:
    data = json.load(f)

components = data["components"]
pipes      = data["pipes"]

# ── Step B: Clean & Enrich ────────────────────────────────────────────────────

# B1. Add missing HV0032
#     Context: HV0030 (2" valve with IG marker on N10A) -> HV0032 -> LIT-0003
#     It is the lower instrument isolation on the LIT-0003 bridle (matching HV0030 upper)
components.append({
    "tag": "HV0032",
    "type": "valve",
    "symbol_description": "Hand valve 2\" - LIT-0003 lower instrument isolation",
    "connects_to": ["HV0030", "LIT-0003"],
    "_added": "inferred from HV0030 reference and LIT-0003 bridle pattern"
})

# B2. Boundary nodes — Utility Connection header
components.append({
    "tag": "UC",
    "type": "boundary_node",
    "symbol_description": "Utility Connection header (external supply)",
    "connects_to": ["SPHN-0030"],
    "_source_drawing": None
})

# B3. Boundary nodes — named pipe lines that cross drawing boundaries
BOUNDARY_PIPES = {
    "14\"-PP01-362-GF0001-B01E9-PP": {
        "description": "PSV inlet header (vessel N1 to PSV trains)",
        "spec": "B01E9", "size": "14\""
    },
    "16\"-PP01-361-GF0014-B03F9-PP": {
        "description": "Fuel gas inlet from DS-1 Scrapper Receiver (PID-0005)",
        "spec": "B03F9", "size": "16\"", "source_drawing": "N-PG-PP01-PR-PID-0005-001"
    },
    "16\"-PP01-361-GF0031-B03F9-PP": {
        "description": "Fuel gas inlet from DS-3 Scrapper Receiver (PID-0007)",
        "spec": "B03F9", "size": "16\"", "source_drawing": "N-PG-PP01-PR-PID-0007-001"
    },
    "16\"-PP01-362-GF0002-B01E9-PP": {
        "description": "Main fuel gas outlet to Fuel Gas Treatment Package (PID-0009)",
        "spec": "B01E9", "size": "16\"", "dest_drawing": "N-PG-PP01-PR-PID-0009-001"
    },
    "16\"-PP01-500-VK0066-B01B8": {
        "description": "PSV-0001 discharge to HP Flare Header (PID-0021), slope 1:500",
        "spec": "B01B8", "size": "16\"", "dest_drawing": "N-PG-PP01-PR-PID-0021-001"
    },
    "16\"-PP01-500-VK0008-B01B8": {
        "description": "PSV-0002 discharge to HP Flare Header (PID-0021), slope 1:500",
        "spec": "B01B8", "size": "16\"", "dest_drawing": "N-PG-PP01-PR-PID-0021-001"
    },
    "2\"-PP01-567-GF0002-B03F9": {
        "description": "Utility connection supply line",
        "spec": "B03F9", "size": "2\""
    },
    "4\"-PP01-512-PK0005-C01N8-PP": {
        "description": "Condensate drain header to Condensate Storage Vessel (PID-0024)",
        "spec": "C01N8", "size": "4\"", "dest_drawing": "N-PG-PP01-PR-PID-0024-001"
    },
    "N-PG-PP01-PR-PID-0021-001": {
        "description": "HP Flare Header drawing (all relief/blowdown destination)",
        "spec": None, "size": None
    },
}

existing_tags = {c["tag"] for c in components}
for tag, meta in BOUNDARY_PIPES.items():
    if tag not in existing_tags:
        components.append({
            "tag": tag,
            "type": "boundary_node",
            "symbol_description": meta["description"],
            "connects_to": [],
            **{k: v for k, v in meta.items() if k != "description"}
        })

# B4. Wire up the 3 isolated sub-clusters with inferred connections
#     (marked _inferred=True — should be verified against the drawing)

INFERRED_EDGES = [
    # CC2: HV0041-LZT → LZT-0002C (completes the A→B→C GWR chain)
    ("HV0041-LZT", "LZT-0002C"),
    # CC3: CIT-0001 → condensate drain line (conductivity on 4" drain)
    ("CIT-0001", "4\"-PP01-512-PK0005-C01N8-PP"),
    # CC4: HV0052 → LV-0001 (IG purge pair on LV-0001 drain outlet)
    ("HV0052", "LV-0001"),
]

tag_map = {c["tag"]: c for c in components}
for src, dst in INFERRED_EDGES:
    if src in tag_map:
        existing = tag_map[src].setdefault("connects_to", [])
        if dst not in existing:
            existing.append(dst)
            tag_map[src]["_inferred_connections"] = tag_map[src].get("_inferred_connections", []) + [dst]

# B6. Note duplicate-suffix tags in a dedicated field (for documentation)
KNOWN_SUFFIX_DISAMBIGUATIONS = {
    "HV0028": ["HV0028-INST", "HV0028-DRAIN"],
    "HV0040": ["HV0040-PSV",  "HV0040-LZT"],
    "HV0041": ["HV0041-PSV",  "HV0041-LZT"],
    "HV0031": ["HV0031-INST"],
}

# Save cleaned JSON
data["components"] = components
data["_cleaning_notes"] = {
    "added_components": ["HV0032", "UC"] + list(BOUNDARY_PIPES.keys()),
    "suffix_disambiguations": KNOWN_SUFFIX_DISAMBIGUATIONS,  # noqa
    "description": (
        "HV0028/HV0040/HV0041 each appear twice on the drawing with same tag. "
        "Disambiguated with -INST/-DRAIN/-PSV/-LZT suffixes. "
        "HV0032 inferred from HV0030 reference pattern. "
        "Boundary nodes added for all cross-drawing pipe connections."
    )
}

with open("unified_pid_graph_clean.json", "w") as f:
    json.dump(data, f, indent=2)

print(f"Cleaned JSON saved → unified_pid_graph_clean.json")
print(f"  Components: {len(components)}")

# ── Step A: Build NetworkX Graph ──────────────────────────────────────────────

G = nx.Graph()

# Node color/shape scheme by type
STYLE = {
    "vessel":               {"color": "#FF6B35", "size": 40, "shape": "box"},
    "valve":                {"color": "#4ECDC4", "size": 18, "shape": "dot"},
    "pressure_safety_valve":{"color": "#FF4444", "size": 22, "shape": "diamond"},
    "instrument":           {"color": "#45B7D1", "size": 18, "shape": "dot"},
    "nozzle":               {"color": "#96CEB4", "size": 14, "shape": "dot"},
    "reducer":              {"color": "#FFEAA7", "size": 14, "shape": "square"},
    "logic_block":          {"color": "#A29BFE", "size": 22, "shape": "triangle"},
    "boundary_node":        {"color": "#DFE6E9", "size": 16, "shape": "ellipse"},
}
DEFAULT_STYLE = {"color": "#B2BEC3", "size": 14, "shape": "dot"}

# Add nodes
for c in components:
    style = STYLE.get(c["type"], DEFAULT_STYLE)
    label = c["tag"]
    title = f"<b>{c['tag']}</b><br>Type: {c['type']}<br>{c.get('symbol_description','')}"
    if "specifications" in c:
        for k, v in c["specifications"].items():
            title += f"<br>{k}: {v}"
    G.add_node(c["tag"], label=label, title=title, **style)

# Add edges from connects_to (deduplicated — undirected)
seen_edges = set()
all_tags = {c["tag"] for c in components}

for c in components:
    for target in c.get("connects_to", []):
        if target not in all_tags:
            continue  # skip still-unresolved refs
        key = tuple(sorted([c["tag"], target]))
        if key not in seen_edges:
            G.add_edge(c["tag"], target)
            seen_edges.add(key)

# Add pipe edges
for p in pipes:
    src, dst = p["from"], p["to"]
    if src in all_tags and dst in all_tags:
        key = tuple(sorted([src, dst]))
        if key not in seen_edges:
            G.add_edge(src, dst, label=p.get("line_spec", ""), title=p.get("description", ""))
            seen_edges.add(key)

print(f"\nGraph stats:")
print(f"  Nodes: {G.number_of_nodes()}")
print(f"  Edges: {G.number_of_edges()}")
print(f"  Connected components: {nx.number_connected_components(G)}")

# Degree centrality — top 10 most connected nodes
centrality = nx.degree_centrality(G)
top = sorted(centrality.items(), key=lambda x: -x[1])[:10]
print(f"\nTop 10 by degree centrality:")
for tag, score in top:
    deg = G.degree(tag)
    print(f"  {tag:30s}  degree={deg:3d}  centrality={score:.3f}")

# ── Step A: Visualize with PyVis ──────────────────────────────────────────────

net = Network(
    height="900px", width="100%",
    bgcolor="#1a1a2e", font_color="white",
    notebook=False, directed=False
)
net.from_nx(G)

# Physics layout tuning
net.set_options("""{
  "physics": {
    "enabled": true,
    "solver": "forceAtlas2Based",
    "forceAtlas2Based": {
      "gravitationalConstant": -80,
      "centralGravity": 0.01,
      "springLength": 120,
      "springConstant": 0.06,
      "damping": 0.4
    },
    "stabilization": { "iterations": 200 }
  },
  "edges": {
    "color": { "color": "#555577" },
    "smooth": { "type": "continuous" },
    "width": 1.2
  },
  "nodes": {
    "borderWidth": 1.5,
    "font": { "size": 11 }
  },
  "interaction": {
    "hover": true,
    "tooltipDelay": 100,
    "navigationButtons": true,
    "keyboard": true
  }
}""")

output = "pid_graph.html"
net.save_graph(output)
print(f"\nInteractive graph saved → {output}")
print("Open in browser to explore.")
