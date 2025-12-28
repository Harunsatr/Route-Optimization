from __future__ import annotations

import streamlit as st
import plotly.graph_objects as go
from typing import Dict, Any


def render_graph_hasil() -> None:
    st.header("Graph Hasil")
    data_validated = st.session_state.get("data_validated", False)
    result = st.session_state.get("result") or st.session_state.get("last_pipeline_result")
    if not data_validated or not result:
        st.info("Belum ada hasil untuk divisualisasikan. Tekan 'Hasil' di menu 'Input Data' terlebih dahulu.")
        return

    points = st.session_state.get("points", {"depots": [], "customers": []})
    node_map = {}
    for d in points.get("depots", []):
        node_map[int(d.get("id", 0))] = (float(d.get("x", 0)), float(d.get("y", 0)), d.get("name", ""))
    for c in points.get("customers", []):
        node_map[int(c.get("id", 0))] = (float(c.get("x", 0)), float(c.get("y", 0)), c.get("name", ""))

    fig = go.Figure()

    # draw routes
    for route in result.get("routes", []):
        seq = route.get("sequence") or []
        xs = []
        ys = []
        for nid in seq:
            if nid in node_map:
                x, y, _ = node_map[nid]
            else:
                # skip unknown nodes
                continue
            xs.append(x)
            ys.append(y)
        if xs and ys and len(xs) >= 2:
            fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines+markers", line=dict(color="green"), marker=dict(size=6, color="green"), showlegend=False))

    # draw depots as yellow star
    depot_x = [node_map[d.get("id")][0] for d in points.get("depots", []) if int(d.get("id", 0)) in node_map]
    depot_y = [node_map[d.get("id")][1] for d in points.get("depots", []) if int(d.get("id", 0)) in node_map]
    depot_names = [d.get("name", "") for d in points.get("depots", [])]
    if depot_x and depot_y:
        fig.add_trace(go.Scatter(x=depot_x, y=depot_y, mode="markers+text", marker_symbol="star", marker=dict(size=16, color="yellow", line=dict(color="black", width=1)), text=depot_names, textposition="top center", name="Depots"))

    # draw customers as red circles
    cust_x = [node_map[c.get("id")][0] for c in points.get("customers", []) if int(c.get("id", 0)) in node_map]
    cust_y = [node_map[c.get("id")][1] for c in points.get("customers", []) if int(c.get("id", 0)) in node_map]
    cust_names = [c.get("name", "") for c in points.get("customers", [])]
    if cust_x and cust_y:
        fig.add_trace(go.Scatter(x=cust_x, y=cust_y, mode="markers+text", marker=dict(size=8, color="red"), text=cust_names, textposition="bottom center", name="Customers"))

    fig.update_layout(height=600, xaxis_title="X", yaxis_title="Y", showlegend=False)

    st.plotly_chart(fig, width='stretch')
