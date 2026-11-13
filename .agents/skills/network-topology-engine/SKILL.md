---
name: network-topology-engine
description: Rules and algorithms for L2/L3 network topology calculation, manual overrides, FDB subtree minimization, LLDP/CDP resolution, and Cytoscape.js formatting.
---

# Lan7 Network Topology Engine Skill

This skill guides topology calculations, graph manipulation, and Cytoscape.js integrations in Lan7.

## 1. Link Priority Hierarchy
When constructing the network graph, link discovery follows a strict 3-tier hierarchy:
1. **Level 1: Manual Overrides (`manual_overrides`)**:
   - Highest priority (`weight = 1`, `is_manual: true`, badge 📌).
   - Fixed by operator. Spanning Tree or loop eliminator must **never** break or prune manual links.
   - Endpoint: `POST /api/topology/manual-links` with validation `A != B` and bidirectional deduplication `(A, B) == (B, A)`.
2. **Level 2: Neighbor Protocols (LLDP / CDP)**:
   - High priority (`weight = 2`, `link_type: "LLDP"` / `"CDP"`).
   - Deterministic 1:1 hardware link detection from MIB tables.
3. **Level 3: FDB Subtree Fallback**:
   - Algorithmic inference (`weight = 5`, `link_type: "FDB"`).
   - Uses minimal set cover to find the closest uplink switch and prunes transit MAC echoes.

## 2. Graph & Loop Elimination
- Graph builder uses `networkx.DiGraph` / `networkx.Graph`.
- Tree construction starts from `root_switch` (user-selected core or highest-uptime/lowest-IP root).
- Cytoscape output payload schema:
  - `nodes`: `[{ data: { id, label, ip, vendor, model, status, is_root } }]`
  - `edges`: `[{ data: { id, source, target, source_port, target_port, is_manual, link_type } }]`

## 3. Cytoscape.js Frontend Guidelines
- Canvas Drag & Drop has a 6px drag threshold to prevent accidental clicks.
- Drag ghost styling: `.switch-drag-ghost` with `backdrop-filter: blur(8px)`.
- Interactive drop targets: `.drag-over` and `.drop-success` animations.
- Click-to-Pick fills empty slots (A or B) without dragging.
- Natural port sort (`compareNatural`) when querying `/api/switches/{ip}/ports-summary`.
