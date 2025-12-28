from __future__ import annotations

import streamlit as st
import plotly.graph_objects as go
from typing import Dict, Any


def _get_next_depot_id(depots: list) -> int:
    """Get the next available depot ID based on max existing ID."""
    if not depots:
        return 0
    return max(int(d.get("id", 0)) for d in depots) + 1


def _get_next_customer_id(customers: list) -> int:
    """Get the next available customer ID based on max existing ID."""
    if not customers:
        return 1
    return max(int(c.get("id", 1)) for c in customers) + 1


def render_input_titik() -> None:
    st.header("Input Titik")
    
    # Initialize session state
    if "points" not in st.session_state:
        st.session_state["points"] = {"depots": [], "customers": []}
    
    if "point_type" not in st.session_state:
        st.session_state["point_type"] = "Depot"

    points = st.session_state["points"]
    
    # Sidebar for point type selection
    st.sidebar.write("### Pilih Tipe Titik")
    point_type = st.sidebar.radio("Tipe:", ("Depot", "Customer"), key="point_type_radio")
    st.session_state["point_type"] = point_type
    
    # Canvas with Plotly
    st.subheader("Canvas Penempatan Titik")
    st.write(f"**Mode: {point_type}** - Klik pada canvas untuk menambah titik")
    
    # Create interactive figure
    fig = go.Figure()
    
    # Add grid
    fig.update_xaxes(
        showgrid=True, gridwidth=1, gridcolor='lightgray',
        zeroline=False, range=[0, 100]
    )
    fig.update_yaxes(
        showgrid=True, gridwidth=1, gridcolor='lightgray',
        zeroline=False, range=[0, 100]
    )
    
    # Plot depots
    depot_x = [d["x"] for d in points["depots"]]
    depot_y = [d["y"] for d in points["depots"]]
    depot_names = [d["name"] for d in points["depots"]]
    
    if depot_x:
        fig.add_trace(go.Scatter(
            x=depot_x, y=depot_y,
            mode='markers+text',
            marker=dict(size=15, color='gold', symbol='star', line=dict(width=2, color='orange')),
            text=depot_names,
            textposition='top center',
            name='Depot',
            hovertemplate='<b>%{text}</b><br>X: %{x}<br>Y: %{y}<extra></extra>'
        ))
    
    # Plot customers
    cust_x = [c["x"] for c in points["customers"]]
    cust_y = [c["y"] for c in points["customers"]]
    cust_names = [c["name"] for c in points["customers"]]
    
    if cust_x:
        fig.add_trace(go.Scatter(
            x=cust_x, y=cust_y,
            mode='markers+text',
            marker=dict(size=12, color='red', symbol='circle', line=dict(width=2, color='darkred')),
            text=cust_names,
            textposition='top center',
            name='Customer',
            hovertemplate='<b>%{text}</b><br>X: %{x}<br>Y: %{y}<extra></extra>'
        ))
    
    fig.update_layout(
        height=500,
        hovermode='closest',
        title="Canvas untuk melihat titik yang telah ditambahkan",
        xaxis_title="X",
        yaxis_title="Y"
    )
    
    # Display canvas with click detection
    st.plotly_chart(fig, width='stretch', key="canvas_plot")
    
    # Manual input section
    st.subheader("Input Koordinat")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        x_coord = st.number_input("Koordinat X:", min_value=0.0, max_value=100.0, value=50.0, step=1.0, key="manual_x")
    with col2:
        y_coord = st.number_input("Koordinat Y:", min_value=0.0, max_value=100.0, value=50.0, step=1.0, key="manual_y")
    with col3:
        if st.button("Tambah Titik", key="btn_add_manual", width='stretch'):
            if st.session_state["point_type"] == "Depot":
                depot_id = _get_next_depot_id(points["depots"])
                points["depots"].append({
                    "id": depot_id,
                    "name": f"Depot {depot_id}",
                    "x": x_coord,
                    "y": y_coord,
                    "time_window": {"start": "08:30", "end": "17:00"},
                    "service_time": 0
                })
            else:
                customer_id = _get_next_customer_id(points["customers"])
                points["customers"].append({
                    "id": customer_id,
                    "name": f"Customer {customer_id}",
                    "x": x_coord,
                    "y": y_coord,
                    "demand": 0.0,
                    "time_window": {"start": "08:30", "end": "17:00"},
                    "service_time": 0
                })
            st.session_state["points"] = points
            st.rerun()
    
    # Reset button
    if st.button("🔄 Reset Semua Titik", key="btn_reset_canvas", width='stretch'):
        st.session_state["points"] = {"depots": [], "customers": []}
        st.rerun()
    
    # Display list of added points
    st.subheader("Daftar Titik yang Ditambahkan")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**🟨 Depot (Kuning)**")
        if points["depots"]:
            for i, depot in enumerate(points["depots"]):
                depot_name = depot.get("name", f"Depot {i}")
                col_a, col_b, col_c = st.columns([3, 1, 1])
                with col_a:
                    st.write(f"{depot_name}")
                with col_b:
                    new_name = st.text_input("Edit nama", value=depot_name, label_visibility="collapsed", key=f"edit_depot_name_{i}")
                    if new_name != depot_name:
                        depot["name"] = new_name
                with col_c:
                    if st.button("✕", key=f"del_depot_{i}"):
                        points["depots"].pop(i)
                        st.session_state["points"] = points
                        st.rerun()
        else:
            st.write("*(belum ada)*")
    
    with col2:
        st.write("**🔴 Customer (Merah)**")
        if points["customers"]:
            for i, customer in enumerate(points["customers"]):
                cust_name = customer.get("name", f"Customer {i+1}")
                col_a, col_b, col_c = st.columns([3, 1, 1])
                with col_a:
                    st.write(f"{cust_name}")
                with col_b:
                    new_name = st.text_input("Edit nama", value=cust_name, label_visibility="collapsed", key=f"edit_customer_name_{i}")
                    if new_name != cust_name:
                        customer["name"] = new_name
                with col_c:
                    if st.button("✕", key=f"del_customer_{i}"):
                        points["customers"].pop(i)
                        st.session_state["points"] = points
                        st.rerun()
        else:
            st.write("*(belum ada)*")
        
        st.session_state["points"] = points

    st.session_state["data_validated"] = False
