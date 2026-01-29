"""
Academic Replay Results Tab

Displays all iterations from the Word document validation:
- ACS iterations (per cluster)
- RVND inter-route iterations
- RVND intra-route iterations
- Final validation results
"""

from __future__ import annotations

import json
import streamlit as st
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List


DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "processed"
ACADEMIC_OUTPUT_PATH = DATA_DIR / "academic_replay_results.json"


def _format_number(value: float) -> str:
    """Format number with 2 decimals."""
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _load_academic_results() -> Dict[str, Any]:
    """Load academic replay results if available."""
    if ACADEMIC_OUTPUT_PATH.exists():
        with ACADEMIC_OUTPUT_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    return None


def _display_sweep_iterations(logs: List[Dict]) -> None:
    """Display SWEEP algorithm iterations."""
    st.markdown("### 📐 SWEEP Algorithm - Polar Angles & Clustering")
    
    # Polar angles
    angle_logs = [l for l in logs if l.get("phase") == "SWEEP" and l.get("step") == "polar_angle"]
    if angle_logs:
        st.markdown("**Step 1: Polar Angle Computation**")
        df_angles = pd.DataFrame([{
            "Customer": l["customer_id"],
            "Angle (°)": l["angle"],
            "Formula": l["formula"]
        } for l in angle_logs])
        st.dataframe(df_angles, use_container_width=True, hide_index=True)
    
    # Sorted order
    sorted_logs = [l for l in logs if l.get("phase") == "SWEEP" and l.get("step") == "sorted_order"]
    if sorted_logs:
        st.markdown("**Step 2: Sorted Customer Order**")
        st.info(f"Order: {sorted_logs[0]['order']}")
    
    # Clusters formed
    cluster_logs = [l for l in logs if l.get("phase") == "SWEEP" and l.get("step") == "cluster_formed"]
    if cluster_logs:
        st.markdown("**Step 3: Clusters Formed**")
        df_clusters = pd.DataFrame([{
            "Cluster": l["cluster_id"],
            "Customers": str(l["customer_ids"]),
            "Total Demand": l["total_demand"],
            "Vehicle": l["vehicle_type"]
        } for l in cluster_logs])
        st.dataframe(df_clusters, use_container_width=True, hide_index=True)


def _display_nn_iterations(logs: List[Dict]) -> None:
    """Display Nearest Neighbor iterations."""
    st.markdown("### 🔗 Nearest Neighbor - Initial Routes")
    
    nn_logs = [l for l in logs if l.get("phase") == "NN"]
    
    if nn_logs:
        # Group by cluster
        clusters = set(l["cluster_id"] for l in nn_logs)
        
        for cluster_id in sorted(clusters):
            with st.expander(f"Cluster {cluster_id}", expanded=True):
                cluster_logs = [l for l in nn_logs if l["cluster_id"] == cluster_id]
                df = pd.DataFrame([{
                    "Step": l["step"],
                    "From": l["from_node"],
                    "To": l["to_node"],
                    "Distance": l["distance"],
                    "Description": l["description"]
                } for l in cluster_logs])
                st.dataframe(df, use_container_width=True, hide_index=True)


def _display_acs_iterations(logs: List[Dict]) -> None:
    """Display ACS iterations with full detail."""
    st.markdown("### 🐜 Ant Colony System - Iterations")
    
    acs_logs = [l for l in logs if l.get("phase") == "ACS"]
    
    if not acs_logs:
        st.info("No ACS iteration logs available.")
        return
    
    # Group by cluster
    clusters = set(l["cluster_id"] for l in acs_logs)
    
    for cluster_id in sorted(clusters):
        st.markdown(f"#### Cluster {cluster_id}")
        
        cluster_logs = [l for l in acs_logs if l["cluster_id"] == cluster_id]
        
        # Pheromone initialization
        init_logs = [l for l in cluster_logs if l.get("step") == "init_pheromone"]
        if init_logs:
            init = init_logs[0]
            st.markdown(f"**Pheromone Init:** τ₀ = {init['tau0']} ({init['formula']})")
        
        # Iteration details
        iterations = set(l.get("iteration") for l in cluster_logs if l.get("iteration"))
        
        for iteration in sorted(iterations):
            with st.expander(f"Iteration {iteration}", expanded=False):
                iter_logs = [l for l in cluster_logs if l.get("iteration") == iteration]
                
                # Predefined route (new format)
                predefined_logs = [l for l in iter_logs if l.get("step") == "route_predefined"]
                if predefined_logs:
                    st.markdown("**Predefined Route (ACADEMIC REPLAY):**")
                    for l in predefined_logs:
                        st.info(f"Ant {l.get('ant', '?')}: {l.get('route', [])} - {l.get('description', '')}")
                
                # Route evaluation (new format - distance only)
                eval_logs = [l for l in iter_logs if l.get("step") == "route_evaluation"]
                if eval_logs:
                    st.markdown("**Route Evaluation (DISTANCE ONLY):**")
                    df = pd.DataFrame([{
                        "Ant": l.get("ant", "?"),
                        "Route": str(l.get("route", [])),
                        "Distance": l.get("distance", 0),
                        "Service Time": l.get("service_time", 0),
                        "TW Violation": l.get("tw_violation", 0),
                        "Wait Time": l.get("wait_time", 0)
                    } for l in eval_logs])
                    st.dataframe(df, use_container_width=True, hide_index=True)
                
                # Ant route construction (old format compatibility)
                ant_logs = [l for l in iter_logs if "ant" in l and "step" in l and "probabilities" in l]
                if ant_logs:
                    st.markdown("**Route Construction:**")
                    df = pd.DataFrame([{
                        "Ant": l["ant"],
                        "Step": l["step"],
                        "From": l["from_node"],
                        "q": l.get("random_q", "N/A"),
                        "Decision": l.get("decision", "N/A"),
                        "Selected": l["selected"],
                        "Probabilities": str(l["probabilities"])[:50] + "..."
                    } for l in ant_logs])
                    st.dataframe(df, use_container_width=True, hide_index=True)
                
                # Route evaluation (old format compatibility)
                route_logs = [l for l in iter_logs if "route" in l and "objective" in l]
                if route_logs:
                    st.markdown("**Route Evaluation:**")
                    df = pd.DataFrame([{
                        "Ant": l["ant"],
                        "Route": str(l["route"]),
                        "Distance": l["distance"],
                        "Service Time": l["service_time"],
                        "TW Violation": l["tw_violation"],
                        "Objective": l["objective"]
                    } for l in route_logs])
                    st.dataframe(df, use_container_width=True, hide_index=True)
                
                # Iteration summary (handle both old and new formats)
                summary_logs = [l for l in iter_logs if l.get("step") == "iteration_summary"]
                if summary_logs:
                    s = summary_logs[0]
                    best_route = s.get('best_route', [])
                    best_distance = s.get('best_distance', 0)
                    # Handle both old (objective) and new (distance-only) formats
                    if 'best_objective' in s:
                        st.success(f"**Best Route:** {best_route} | Distance: {best_distance} | Objective: {s['best_objective']}")
                    else:
                        tw_viol = s.get('best_tw_violation', 0)
                        st.success(f"**Best Route:** {best_route} | Distance: {best_distance} | TW Violation: {tw_viol}")


def _display_rvnd_inter_iterations(logs: List[Dict]) -> None:
    """Display RVND inter-route iterations - ALL iterations including non-improvements."""
    st.markdown("### 🔄 RVND Inter-Route Iterations")
    
    inter_logs = [l for l in logs if l.get("phase") == "RVND-INTER"]
    
    if not inter_logs:
        st.info("No RVND inter-route iterations (single route or no moves attempted).")
        return
    
    st.info(f"📊 Total iterations: {len(inter_logs)} (shows ALL iterations, not just improvements)")
    
    df = pd.DataFrame([{
        "Iteration": l.get("iteration_id", l.get("iteration", "?")),
        "Neighborhood": l.get("neighborhood", "none") or "none",
        "Improved": "✅" if l.get("improved", l.get("accepted", False)) else "❌",
        "Distance": l.get("total_distance", l.get("distance_after", 0)),
        "Routes": str(l.get("routes_snapshot", []))[:60] + "..."
    } for l in inter_logs])
    st.dataframe(df, use_container_width=True, hide_index=True)


def _display_rvnd_intra_iterations(logs: List[Dict]) -> None:
    """Display RVND intra-route iterations - ALL iterations including non-improvements."""
    st.markdown("### 🔁 RVND Intra-Route Iterations")
    
    intra_logs = [l for l in logs if l.get("phase") == "RVND-INTRA"]
    
    if not intra_logs:
        st.info("No RVND intra-route iterations.")
        return
    
    st.info(f"📊 Total iterations: {len(intra_logs)} (shows ALL iterations, not just improvements)")
    
    # Group by cluster
    clusters = set(l.get("cluster_id", 0) for l in intra_logs if "cluster_id" in l)
    
    for cluster_id in sorted(clusters):
        with st.expander(f"Cluster {cluster_id}", expanded=True):
            cluster_logs = [l for l in intra_logs if l.get("cluster_id") == cluster_id]
            
            st.caption(f"Iterations for this cluster: {len(cluster_logs)}")
            
            df = pd.DataFrame([{
                "Iteration": l.get("iteration_id", l.get("iteration", "?")),
                "Neighborhood": l.get("neighborhood", "none") or "none",
                "Improved": "✅" if l.get("improved", l.get("accepted", False)) else "❌",
                "Distance": l.get("total_distance", l.get("distance_after", 0)),
                "Route": str(l.get("routes_snapshot", l.get("sequence_after", [])))[:50] + "..."
            } for l in cluster_logs])
            st.dataframe(df, use_container_width=True, hide_index=True)


def _minutes_to_time(minutes: float) -> str:
    """Convert minutes from midnight to HH:MM format."""
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    return f"{hours:02d}:{mins:02d}"


def _display_time_window_analysis(result: Dict[str, Any]) -> None:
    """Display detailed time window analysis for each cluster/vehicle."""
    st.markdown("### ⏰ Vehicle Time Window Analysis")
    st.markdown("*Customer availability windows and compliance status*")
    
    routes = result.get("routes", [])
    dataset = result.get("dataset", {})
    
    if not routes:
        st.info("No routes available for time window analysis.")
        return
    
    # Get customer data for names
    customers = {c["id"]: c for c in dataset.get("customers", [])}
    depot = dataset.get("depot", {})
    depot_tw_start = depot.get("time_window", {}).get("start", "08:00")
    depot_tw_end = depot.get("time_window", {}).get("end", "17:00")
    
    for route in routes:
        cluster_id = route.get("cluster_id", "?")
        vehicle_type = route.get("vehicle_type", "?")
        stops = route.get("stops", [])
        
        with st.expander(f"🚛 Cluster {cluster_id} - Vehicle {vehicle_type}", expanded=True):
            # Depot start info
            if stops:
                depot_stop = stops[0]
                depot_start_time = depot_stop.get("departure", depot_stop.get("arrival", 480))
                st.info(f"**Depot Start Time:** {_minutes_to_time(depot_start_time)} | "
                       f"Depot Window: {depot_tw_start} - {depot_tw_end}")
            
            # Build table for customer stops
            customer_rows = []
            total_wait = 0
            total_violation = 0
            
            for stop in stops:
                node_id = stop.get("node_id", 0)
                
                # Skip depot entries (node_id == 0)
                if node_id == 0:
                    continue
                
                customer = customers.get(node_id, {})
                customer_name = customer.get("name", f"Customer {node_id}")
                
                raw_arrival = stop.get("raw_arrival", stop.get("arrival", 0))
                service_start = stop.get("arrival", raw_arrival)
                service_time = stop.get("service_time", 0)
                service_end = stop.get("departure", service_start + service_time)
                tw_start = stop.get("tw_start", 0)
                tw_end = stop.get("tw_end", 0)
                wait = stop.get("wait", 0)
                violation = stop.get("violation", 0)
                
                total_wait += wait
                total_violation += violation
                
                # Determine compliance status
                if violation > 0:
                    status = f"❌ LATE by {violation:.1f} min"
                elif wait > 0:
                    status = f"⏳ WAIT {wait:.1f} min"
                else:
                    status = "✅ OK"
                
                customer_rows.append({
                    "Customer": customer_name,
                    "Arrival Time": _minutes_to_time(raw_arrival),
                    "Service Start": _minutes_to_time(service_start),
                    "Service End": _minutes_to_time(service_end),
                    "TW Start": _minutes_to_time(tw_start),
                    "TW End": _minutes_to_time(tw_end),
                    "Status": status
                })
            
            if customer_rows:
                df = pd.DataFrame(customer_rows)
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                # Summary metrics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Wait Time", f"{total_wait:.1f} min")
                with col2:
                    if total_violation > 0:
                        st.metric("TW Violations", f"{total_violation:.1f} min", delta="⚠️", delta_color="inverse")
                    else:
                        st.metric("TW Violations", "0 min ✅")
                with col3:
                    compliant = sum(1 for r in customer_rows if "OK" in r["Status"] or "WAIT" in r["Status"])
                    st.metric("Compliance", f"{compliant}/{len(customer_rows)} customers")
            else:
                st.warning("No customer stops in this route.")
    
    # Overall summary
    st.markdown("---")
    st.markdown("#### 📊 Overall Time Window Summary")
    
    total_routes_compliant = sum(1 for r in routes if r.get("total_tw_violation", 0) == 0)
    total_tw_violation = sum(r.get("total_tw_violation", 0) for r in routes)
    total_wait_time = sum(r.get("total_wait_time", 0) for r in routes)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Routes Compliant", f"{total_routes_compliant}/{len(routes)}")
    with col2:
        st.metric("Total Wait Time", f"{total_wait_time:.1f} min")
    with col3:
        if total_tw_violation > 0:
            st.metric("Total TW Violations", f"{total_tw_violation:.1f} min", delta="⚠️", delta_color="inverse")
        else:
            st.metric("Total TW Violations", "0 min ✅")
    with col4:
        if total_tw_violation == 0:
            st.success("All customers served within time windows!")
        else:
            st.warning("Some time window violations detected")


def _display_vehicle_assignment(logs: List[Dict]) -> None:
    """Display vehicle reassignment."""
    st.markdown("### 🚛 Vehicle Reassignment")
    
    vehicle_logs = [l for l in logs if l.get("phase") == "VEHICLE_REASSIGN"]
    
    if vehicle_logs:
        df = pd.DataFrame([{
            "Cluster": l["cluster_id"],
            "Demand": l["demand"],
            "Old Vehicle": l["old_vehicle"],
            "New Vehicle": l["new_vehicle"],
            "Status": l.get("status", "✅"),
            "Reason": l["reason"]
        } for l in vehicle_logs])
        st.dataframe(df, use_container_width=True, hide_index=True)


def _display_vehicle_availability(result: Dict[str, Any]) -> None:
    """Display vehicle availability schedule and status."""
    st.markdown("### 🕐 Vehicle Availability Schedule")
    st.markdown("*Waktu Ketersediaan Jenis Kendaraan pada Hari Itu*")
    
    availability = result.get("vehicle_availability", [])
    available_vehicles = result.get("available_vehicles", [])
    
    if not availability:
        # Fallback: extract from logs
        logs = result.get("iteration_logs", [])
        availability = [l for l in logs if l.get("phase") == "VEHICLE_AVAILABILITY"]
    
    if not availability:
        st.info("Tidak ada data ketersediaan kendaraan.")
        return
    
    # Display availability table
    df = pd.DataFrame([{
        "Kendaraan": a.get("vehicle_id", "?"),
        "Kapasitas": a.get("capacity", 0),
        "Unit": a.get("units", 1),
        "Waktu Tersedia": a.get("time_window", "-"),
        "Status": a.get("status", "?")
    } for a in availability])
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    # Summary metrics
    total_vehicles = len(availability)
    available_count = sum(1 for a in availability if a.get("available", False))
    unavailable_count = total_vehicles - available_count
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Jenis Kendaraan", total_vehicles)
    with col2:
        st.metric("Tersedia untuk Routing", available_count, delta=None)
    with col3:
        if unavailable_count > 0:
            st.metric("Tidak Tersedia", unavailable_count, delta="⚠️", delta_color="inverse")
        else:
            st.metric("Tidak Tersedia", 0)
    
    # Availability explanation
    st.markdown("---")
    st.markdown("#### 📋 Penjelasan Ketersediaan")
    
    for a in availability:
        vehicle_id = a.get("vehicle_id", "?")
        available = a.get("available", False)
        time_window = a.get("time_window", "Tidak diset")
        capacity = a.get("capacity", 0)
        units = a.get("units", 1)
        
        if available:
            st.success(f"**Kendaraan {vehicle_id}** (kapasitas ≤ {capacity}, {units} unit): "
                      f"✅ TERSEDIA pada {time_window}. "
                      f"Kendaraan ini dapat digunakan untuk routing.")
        else:
            st.warning(f"**Kendaraan {vehicle_id}** (kapasitas ≤ {capacity}, {units} unit): "
                      f"❌ TIDAK TERSEDIA - {time_window}. "
                      f"Kendaraan ini TIDAK akan digunakan dalam routing.")
    
    # Used vehicles summary
    if available_vehicles:
        st.markdown("---")
        st.info(f"**Kendaraan yang Digunakan:** {', '.join(available_vehicles)}")
    else:
        st.error("**⚠️ Tidak ada kendaraan yang tersedia untuk routing!**")


def _display_final_results(result: Dict[str, Any]) -> None:
    """Display final routes and costs."""
    st.markdown("### 📊 Final Results")
    
    routes = result.get("routes", [])
    costs = result.get("costs", {})
    
    # Routes summary
    if routes:
        st.markdown("**Final Routes:**")
        df = pd.DataFrame([{
            "Cluster": r["cluster_id"],
            "Vehicle": r["vehicle_type"],
            "Route": str(r["sequence"]),
            "Distance": r["total_distance"],
            "Service Time": r["total_service_time"],
            "TW Violation": r["total_tw_violation"],
            "Wait Time": r.get("total_wait_time", 0),
            "Demand": r["total_demand"]
        } for r in routes])
        st.dataframe(df, use_container_width=True, hide_index=True)
    
    # TIME WINDOW ANALYSIS (NEW)
    st.markdown("---")
    _display_time_window_analysis(result)
    
    # Costs
    st.markdown("---")
    if costs:
        st.markdown("**Cost Breakdown:**")
        
        breakdown = costs.get("breakdown", [])
        if breakdown:
            df = pd.DataFrame([{
                "Cluster": c["cluster_id"],
                "Vehicle": c["vehicle_type"],
                "Fixed Cost": f"Rp {c['fixed_cost']:,.0f}",
                "Variable Cost": f"Rp {c['variable_cost']:,.0f}",
                "Total Cost": f"Rp {c['total_cost']:,.0f}"
            } for c in breakdown])
            st.dataframe(df, use_container_width=True, hide_index=True)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Fixed Cost", f"Rp {costs.get('total_fixed_cost', 0):,.0f}")
        with col2:
            st.metric("Total Variable Cost", f"Rp {costs.get('total_variable_cost', 0):,.0f}")
        with col3:
            st.metric("TOTAL COST", f"Rp {costs.get('total_cost', 0):,.0f}")


def _display_validation(result: Dict[str, Any]) -> None:
    """Display validation against Word document."""
    st.markdown("### ✅ Validation Against Word Document")
    
    validation = result.get("validation", [])
    all_valid = result.get("all_valid", False)
    
    if all_valid:
        st.success("🎉 ALL ROUTES MATCH THE WORD DOCUMENT!")
    else:
        st.error("⚠️ SOME ROUTES DO NOT MATCH - SEE DETAILS BELOW")
    
    if validation:
        df = pd.DataFrame([{
            "Cluster": v["cluster_id"],
            "Expected Sequence": str(v["sequence_expected"]),
            "Actual Sequence": str(v["sequence_actual"]),
            "Seq Match": "✅" if v["sequence_match"] else "❌",
            "Expected Dist": v["distance_expected"],
            "Actual Dist": v["distance_actual"],
            "Dist Match": "✅" if v["distance_match"] else "❌",
            "Valid": "✅" if v["valid"] else "❌"
        } for v in validation])
        st.dataframe(df, use_container_width=True, hide_index=True)
    
    # Route Structure Validation
    st.markdown("### 🏗️ Route Structure Validation")
    
    structure_validation = result.get("structure_validation", [])
    structure_valid = result.get("structure_valid", True)
    
    if structure_valid:
        st.success("✅ All routes have correct MFVRP structure [DEPOT → Customers → DEPOT]")
    else:
        st.error("❌ CRITICAL: Some routes have invalid structure!")
    
    if structure_validation:
        df_struct = pd.DataFrame([{
            "Cluster": v["cluster_id"],
            "Sequence": str(v["sequence"]),
            "Valid": "✅" if v["valid"] else "❌",
            "Issues": ", ".join(v["issues"]) if v["issues"] else "None"
        } for v in structure_validation])
        st.dataframe(df_struct, use_container_width=True, hide_index=True)


def render_academic_replay() -> None:
    """Main render function for Academic Replay tab."""
    st.header("📚 Academic Replay Mode")
    st.markdown("*Validasi terhadap dokumen 'Hitung Manual MFVRPTE RVND'*")
    
    st.divider()
    
    # Run button
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("🚀 Run Academic Replay", type="primary"):
            with st.spinner("Running academic replay..."):
                try:
                    # Import and run
                    import sys
                    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
                    from academic_replay import run_academic_replay
                    
                    result = run_academic_replay()
                    st.session_state["academic_result"] = result
                    st.success("Academic replay completed!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
    
    with col2:
        st.info("Klik untuk menjalankan validasi akademik sesuai dokumen Word.")
    
    st.divider()
    
    # Load and display results
    result = st.session_state.get("academic_result") or _load_academic_results()
    
    if not result:
        st.warning("Belum ada hasil. Klik 'Run Academic Replay' untuk memulai.")
        return
    
    logs = result.get("iteration_logs", [])
    
    # Create tabs for each phase
    tab0, tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "🕐 Availability",
        "📐 Sweep", 
        "🔗 NN", 
        "🐜 ACS", 
        "🔄 RVND-Inter",
        "🔁 RVND-Intra",
        "📊 Final Results",
        "✅ Validation"
    ])
    
    with tab0:
        _display_vehicle_availability(result)
    
    with tab1:
        _display_sweep_iterations(logs)
    
    with tab2:
        _display_nn_iterations(logs)
    
    with tab3:
        _display_acs_iterations(logs)
    
    with tab4:
        _display_rvnd_inter_iterations(logs)
    
    with tab5:
        _display_rvnd_intra_iterations(logs)
    
    with tab6:
        _display_vehicle_assignment(logs)
        _display_final_results(result)
    
    with tab7:
        _display_validation(result)
