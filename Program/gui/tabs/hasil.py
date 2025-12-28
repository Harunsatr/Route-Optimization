from __future__ import annotations

import streamlit as st
from typing import Dict, Any, List


def _format_number(value: float) -> str:
    # Format with two decimals and comma as decimal separator
    s = f"{value:,.2f}"
    return s.replace(".", ",")


def _build_depot_summary_from_result(points: Dict[str, Any], result: Dict[str, Any]) -> Dict[int, Dict]:
    # points: {"depots": [...], "customers": [...]} entries have id,name,x,y
    depots = points.get("depots", [])
    customers = points.get("customers", [])
    depot_ids = [int(d.get("id", idx)) for idx, d in enumerate(depots)]
    depot_map = {int(d.get("id", i)): d.get("name", "") for i, d in enumerate(depots)}

    per_depot = {did: {"name": depot_map.get(did, ""), "distance": 0.0, "customers": []} for did in depot_ids}

    if not result:
        return per_depot

    routes = result.get("routes", [])
    for route in routes:
        # prefer explicit total_distance if present
        dist = float(route.get("total_distance", 0.0) or 0.0)
        seq = route.get("sequence") or []
        stops = route.get("stops") or []
        # determine depot id: try first stop node_id mapping to depot ids, else fallback to first depot
        depot_id = None
        if stops and isinstance(stops, list) and len(stops) > 0:
            first_node = stops[0].get("node_id")
            # If first_node equals 0 and depot ids include 0, use 0; else if first_node matches a depot id, use it
            if first_node in per_depot:
                depot_id = first_node
            else:
                # try to map 0 -> any depot id if only one depot exists
                if len(per_depot) == 1:
                    depot_id = next(iter(per_depot.keys()))
        if depot_id is None:
            depot_id = next(iter(per_depot.keys())) if per_depot else 0

        per_depot.setdefault(depot_id, {"name": depot_map.get(depot_id, ""), "distance": 0.0, "customers": []})
        per_depot[depot_id]["distance"] += dist
        # add customers from sequence (exclude zeros)
        for node in seq:
            try:
                nid = int(node)
            except Exception:
                continue
            if nid == 0:
                continue
            per_depot[depot_id]["customers"].append(nid)

    return per_depot


def render_hasil() -> None:
    st.header("Hasil")

    data_validated = st.session_state.get("data_validated", False)
    result = st.session_state.get("result") or st.session_state.get("last_pipeline_result")

    if not data_validated or not result:
        st.info("Belum ada hasil. Tekan 'Hasil' di menu 'Input Data' untuk menjalankan komputasi terlebih dahulu.")
        return

    points = st.session_state.get("points", {"depots": [], "customers": []})
    per_depot = _build_depot_summary_from_result(points, result)

    total_all = 0.0
    # Present in order of depot index (0..)
    for idx, (depot_id, info) in enumerate(sorted(per_depot.items(), key=lambda x: int(x[0]))):
        dist = info.get("distance", 0.0) or 0.0
        total_all += float(dist)
        if info.get("customers"):
            # list customer ids as comma separated
            custs = ", ".join(str(c) for c in info.get("customers", []))
            st.write(f"Total jarak untuk depot {depot_id} adalah {_format_number(dist)}")
            st.write(f"Dilayani customer: {custs}")
        else:
            st.write(f"Depot {depot_id}:")
            st.write(f"Tidak ada customer yang dilayani oleh depot \"{info.get('name','')}\"")

    st.write(f"Jadi, total jarak untuk semua depot adalah \"{_format_number(total_all)}\"")
