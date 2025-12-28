from __future__ import annotations

import streamlit as st
import pandas as pd
import json
import sys
from pathlib import Path
from typing import Dict, Any

# Add parent gui directory to path for agents import
_gui_dir = Path(__file__).resolve().parent.parent
if str(_gui_dir) not in sys.path:
    sys.path.insert(0, str(_gui_dir))

import agents


def render_input_data() -> None:
    """Render Input Data tab with structured sections for vehicle capacity, iterations, demands, and distance matrix."""
    
    st.header("📋 Input Data")
    
    # Initialize session state
    if "inputData" not in st.session_state:
        st.session_state["inputData"] = {}
    if "kapasitas_kendaraan" not in st.session_state:
        st.session_state["kapasitas_kendaraan"] = 100
    if "iterasi" not in st.session_state:
        st.session_state["iterasi"] = 2
    if "last_loaded_file" not in st.session_state:
        st.session_state["last_loaded_file"] = None
    if "distanceMatrix_size" not in st.session_state:
        st.session_state["distanceMatrix_size"] = 0
    
    inputData = st.session_state["inputData"]
    
    # ===== SECTION 1: Kapasitas Kendaraan =====
    with st.container():
        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader("1️⃣ Kapasitas Kendaraan")
        with col2:
            st.write("")  # spacing
        
        kapasitas = st.number_input(
            "Kapasitas (integer > 0):",
            min_value=1,
            value=st.session_state.get("kapasitas_kendaraan", 100),
            key="input_kapasitas",
            help="Kapasitas maksimal kendaraan untuk membawa permintaan"
        )
        st.session_state["kapasitas_kendaraan"] = kapasitas
    
    st.divider()
    
    # ===== SECTION 2: Iterasi =====
    with st.container():
        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader("2️⃣ Jumlah Iterasi")
        with col2:
            st.write("")  # spacing
        
        iterasi = st.number_input(
            "Jumlah iterasi (integer ≥ 1):",
            min_value=1,
            value=st.session_state.get("iterasi", 2),
            key="input_iterasi",
            help="Jumlah iterasi untuk algoritma optimasi"
        )
        st.session_state["iterasi"] = iterasi
    
    st.divider()
    
    # ===== SECTION 3: Permintaan Customer =====
    st.subheader("3️⃣ Permintaan Customer")
    
    if "points" not in st.session_state or not st.session_state.points.get("customers"):
        st.info("ℹ️ Tambahkan customer di tab 'Input Titik' terlebih dahulu.")
    else:
        customers = st.session_state.points["customers"]
        n = len(customers)
        
        # Initialize demands if needed
        demands = inputData.get("customerDemand", [])
        if not demands or len(demands) != n:
            demands = [c.get("demand", 0) for c in customers]
        
        # Create demand table
        demand_data = []
        for i, cust in enumerate(customers):
            demand_data.append({
                "Customer": cust.get("name", f"Customer {i+1}"),
                "Permintaan": float(demands[i]) if i < len(demands) else 0.0
            })
        
        df_dem = pd.DataFrame(demand_data)
        edited_dem = st.data_editor(
            df_dem,
            num_rows="fixed",
            key="demands_editor",
            width='stretch',
            column_config={
                "Customer": st.column_config.TextColumn("Customer", disabled=True),
                "Permintaan": st.column_config.NumberColumn("Permintaan", min_value=0, format="%d")
            }
        )
        
        # Extract demands back to inputData
        inputData["customerDemand"] = [float(r["Permintaan"]) for r in edited_dem.to_dict(orient="records")]
    
    st.divider()
    
    # ===== SECTION 4: Tabel Jarak (Distance Matrix) =====
    st.subheader("4️⃣ Tabel Jarak Antar Titik")
    
    nodes = []
    nodes_map = {}
    
    if "points" in st.session_state:
        pts = st.session_state.points
        # Depot first, then customers
        for i, d in enumerate(pts.get("depots", [])):
            node_id = int(d.get("id", i))
            nodes.append(node_id)
            nodes_map[node_id] = d.get("name", f"Depot {i}")
        for i, c in enumerate(pts.get("customers", [])):
            node_id = int(c.get("id", i + 1))
            nodes.append(node_id)
            nodes_map[node_id] = c.get("name", f"Customer {i+1}")
    
    size = len(nodes)
    
    if size == 0:
        st.info("ℹ️ Tambahkan depot dan customer di tab 'Input Titik' terlebih dahulu.")
    else:
        # Initialize distance matrix if needed (all zeros)
        if not inputData.get("distanceMatrix") or len(inputData.get("distanceMatrix", [])) != size:
            inputData["distanceMatrix"] = [[0.0 for _ in range(size)] for _ in range(size)]
        
        st.write("**Masukkan jarak antar titik secara manual.**")
        st.write("*Diagonal (jarak ke diri sendiri) otomatis diatur 0 dan tidak dapat diedit*")
        
        # Show node mapping for reference
        with st.expander("📋 Pemetaan Node"):
            for idx, nid in enumerate(nodes):
                st.write(f"**Node {idx}**: {nodes_map.get(nid, str(nid))}")
        
        # Create column config with diagonal cells disabled
        col_config = {}
        for i in range(size):
            for j in range(size):
                col_key = f"col_{j}"
                if i == j:
                    # Diagonal: disabled, always 0
                    col_config[col_key] = st.column_config.NumberColumn(
                        f"{j}",
                        disabled=True,
                        help="Diagonal - tidak dapat diedit (selalu 0)"
                    )
                else:
                    # Non-diagonal: editable
                    col_config[col_key] = st.column_config.NumberColumn(
                        f"{j}",
                        min_value=0,
                        step=0.1,
                        format="%.2f"
                    )
        
        # Create dataframe with row index labeled as node names for readability
        # But use numeric columns to avoid duplicate column name errors
        df_data = {}
        for j in range(size):
            col_key = f"col_{j}"
            df_data[col_key] = [inputData["distanceMatrix"][i][j] for i in range(size)]
        
        df = pd.DataFrame(df_data, index=list(range(size)))
        df.index.name = "From\\To"
        
        # Use st.data_editor with column config to disable diagonal
        edited = st.data_editor(
            df,
            key="distance_matrix_editor",
            width='stretch',
            num_rows="fixed",
            column_config=col_config
        )
        
        # Convert back to matrix format and enforce symmetric + diagonal zero
        if edited is not None:
            mat = []
            for i in range(size):
                row = []
                for j in range(size):
                    col_key = f"col_{j}"
                    val = edited[col_key].iloc[i] if col_key in edited.columns else 0.0
                    # Force diagonal to 0
                    if i == j:
                        row.append(0.0)
                    else:
                        try:
                            val_float = float(val) if val is not None else 0.0
                            row.append(val_float)
                        except (ValueError, TypeError):
                            row.append(0.0)
                mat.append(row)
            
            # Enforce symmetry: ensure mat[i][j] == mat[j][i]
            # For any change, use the newer value (from upper triangle to lower, or vice versa)
            for i in range(size):
                for j in range(i + 1, size):
                    # Take the maximum of the two values (assumes user entered one, other is old)
                    # OR we can prefer the cell that was just edited
                    val_ij = mat[i][j]
                    val_ji = mat[j][i]
                    
                    # If they differ, sync them - prefer non-zero value, else use upper triangle
                    if val_ij != val_ji:
                        if val_ij != 0 or val_ji == 0:
                            mat[j][i] = val_ij
                        else:
                            mat[i][j] = val_ji
            
            inputData["distanceMatrix"] = mat
    
    st.session_state["inputData"] = inputData
    
    st.divider()
    
    # ===== ACTION BUTTONS: Save, Load, Process =====
    st.subheader("⚙️ Aksi")
    
    button_cols = st.columns(3)
    
    with button_cols[0]:
        if st.button("💾 Simpan Progres", width='stretch', key="btn_save_progress"):
            progress_data = {
                "points": st.session_state.get("points", {}),
                "inputData": st.session_state.get("inputData", {}),
                "kapasitas_kendaraan": st.session_state.get("kapasitas_kendaraan", 100),
                "iterasi": st.session_state.get("iterasi", 2)
            }
            st.session_state["saved_progress"] = progress_data
            
            # Also offer download
            json_str = json.dumps(progress_data, indent=2)
            st.download_button(
                label="📥 Download JSON",
                data=json_str,
                file_name="progress.json",
                mime="application/json",
                key="btn_download_progress"
            )
    
    with button_cols[1]:
        uploaded_file = st.file_uploader(
            "📤 Muat Progres",
            type=["json"],
            key="upload_progress_file",
            help="Upload file JSON hasil simpan sebelumnya"
        )
        if uploaded_file is not None:
            # Check if we already processed this file in this session
            file_id = f"{uploaded_file.name}_{uploaded_file.size}"
            if st.session_state.get("last_loaded_file") != file_id:
                try:
                    loaded_data = json.load(uploaded_file)
                    st.session_state["points"] = loaded_data.get("points", {})
                    st.session_state["inputData"] = loaded_data.get("inputData", {})
                    st.session_state["kapasitas_kendaraan"] = loaded_data.get("kapasitas_kendaraan", 100)
                    st.session_state["iterasi"] = loaded_data.get("iterasi", 2)
                    st.session_state["last_loaded_file"] = file_id
                    st.session_state["distanceMatrix_size"] = len(loaded_data.get("inputData", {}).get("distanceMatrix", []))
                    st.success("✅ Progres dimuat! Data siap untuk diproses.")
                    # Don't rerun - let user see the loaded data
                except Exception as e:
                    st.error(f"❌ Gagal memuat file: {e}")
    
    with button_cols[2]:
        if st.button("🚀 Lanjutkan Proses", width='stretch', key="btn_process"):
            st.session_state["data_validated"] = False
            
            # Build state
            state = {
                "points": st.session_state.get("points", {}),
                "inputData": st.session_state.get("inputData", {})
            }
            
            # Validate
            valid, errors = agents.validate_state(state)
            if not valid:
                error_msg = "❌ Validasi gagal:\n" + "\n".join([f"• {e}" for e in errors])
                st.error(error_msg)
            else:
                with st.spinner("⏳ Menjalankan komputasi... harap tunggu"):
                    try:
                        result = agents.run_pipeline(state)
                        st.session_state["result"] = result
                        st.session_state["data_validated"] = True
                        st.success("✅ Komputasi selesai! Lihat hasil di tab 'Hasil' dan visualisasi di tab 'Graph Hasil'.")
                    except Exception as e:
                        st.error(f"❌ Komputasi gagal: {str(e)}")
                        st.session_state["data_validated"] = False

