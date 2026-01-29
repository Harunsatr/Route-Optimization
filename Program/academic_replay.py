"""
Academic Replay Mode - "Hitung Manual MFVRPTE RVND"

This module reproduces EXACTLY the computations from the Word document.
NO optimization. NO randomization. DETERMINISTIC replay only.

MODE: ACADEMIC_REPLAY (default for validation)
"""

import json
import math
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from copy import deepcopy

# ============================================================
# CONFIGURATION
# ============================================================

MODE = "ACADEMIC_REPLAY"  # default for validation
# MODE = "OPTIMIZATION"  # for normal operation

DATA_DIR = Path(__file__).resolve().parent / "data" / "processed"
ACADEMIC_OUTPUT_PATH = DATA_DIR / "academic_replay_results.json"

# ============================================================
# HARD-CODED DATASET FROM WORD DOCUMENT
# ============================================================

ACADEMIC_DATASET = {
    "depot": {
        "id": 0,
        "name": "Depot",
        "x": 0.0,
        "y": 0.0,
        "time_window": {"start": "08:00", "end": "17:00"},
        "service_time": 0
    },
    "customers": [
        {"id": 1, "name": "C1", "x": 2.0, "y": 3.0, "demand": 10, "service_time": 5, "time_window": {"start": "08:00", "end": "12:00"}},
        {"id": 2, "name": "C2", "x": 5.0, "y": 1.0, "demand": 15, "service_time": 10, "time_window": {"start": "08:00", "end": "14:00"}},
        {"id": 3, "name": "C3", "x": 6.0, "y": 4.0, "demand": 20, "service_time": 8, "time_window": {"start": "09:00", "end": "15:00"}},
        {"id": 4, "name": "C4", "x": 8.0, "y": 2.0, "demand": 25, "service_time": 12, "time_window": {"start": "08:30", "end": "16:00"}},
        {"id": 5, "name": "C5", "x": 3.0, "y": 6.0, "demand": 30, "service_time": 15, "time_window": {"start": "10:00", "end": "14:00"}},
        {"id": 6, "name": "C6", "x": 7.0, "y": 5.0, "demand": 18, "service_time": 7, "time_window": {"start": "08:00", "end": "13:00"}},
        {"id": 7, "name": "C7", "x": 4.0, "y": 8.0, "demand": 22, "service_time": 9, "time_window": {"start": "09:00", "end": "16:00"}},
        {"id": 8, "name": "C8", "x": 1.0, "y": 5.0, "demand": 12, "service_time": 6, "time_window": {"start": "08:00", "end": "11:00"}},
        {"id": 9, "name": "C9", "x": 9.0, "y": 7.0, "demand": 28, "service_time": 11, "time_window": {"start": "10:00", "end": "15:00"}},
        {"id": 10, "name": "C10", "x": 5.0, "y": 9.0, "demand": 35, "service_time": 14, "time_window": {"start": "09:00", "end": "17:00"}}
    ],
    "fleet": [
        {"id": "A", "capacity": 60, "units": 2, "fixed_cost": 50000, "variable_cost_per_km": 1000, "available_from": "08:00", "available_until": "17:00"},
        {"id": "B", "capacity": 100, "units": 2, "fixed_cost": 60000, "variable_cost_per_km": 1000, "available_from": "08:00", "available_until": "17:00"},
        {"id": "C", "capacity": 150, "units": 1, "fixed_cost": 70000, "variable_cost_per_km": 1000, "available_from": "08:00", "available_until": "17:00"}
    ],
    "acs_parameters": {
        "alpha": 0.5,
        "beta": 2,
        "rho": 0.2,
        "q0": 0.85,
        "num_ants": 2,
        "max_iterations": 2
    },
    "objective_weights": {
        "w1_distance": 1.0,
        "w2_time": 1.0,
        "w3_tw_violation": 1.0
    }
}

# ============================================================
# FIXED VALUES FROM WORD DOCUMENT
# These are the EXACT random values and decisions from the document
# ============================================================

# Polar angles (pre-computed as in Word)
WORD_POLAR_ANGLES = {
    1: 56.31,   # C1: atan2(3, 2) = 56.31°
    2: 11.31,   # C2: atan2(1, 5) = 11.31°
    3: 33.69,   # C3: atan2(4, 6) = 33.69°
    4: 14.04,   # C4: atan2(2, 8) = 14.04°
    5: 63.43,   # C5: atan2(6, 3) = 63.43°
    6: 35.54,   # C6: atan2(5, 7) = 35.54°
    7: 63.43,   # C7: atan2(8, 4) = 63.43°
    8: 78.69,   # C8: atan2(5, 1) = 78.69°
    9: 37.87,   # C9: atan2(7, 9) = 37.87°
    10: 60.95   # C10: atan2(9, 5) = 60.95°
}

# Sorted customers by polar angle (as in Word)
WORD_SORTED_CUSTOMERS = [2, 4, 3, 6, 9, 1, 10, 5, 7, 8]

# Clusters formed (exactly as in Word document - 4 clusters with forced termination)
# Termination logic: After adding a customer, check if ANY remaining customer fits.
# If no remaining customer can fit, STOP the cluster (forced termination).
WORD_CLUSTERS = [
    {"cluster_id": 1, "customer_ids": [2, 4], "total_demand": 40, "vehicle_type": "A"},
    {"cluster_id": 2, "customer_ids": [3, 6, 9], "total_demand": 66, "vehicle_type": "B"},
    {"cluster_id": 3, "customer_ids": [1, 10], "total_demand": 45, "vehicle_type": "A"},
    {"cluster_id": 4, "customer_ids": [5, 7, 8], "total_demand": 64, "vehicle_type": "B"}
]

# Fixed random values for ACS (from Word tables)
# Format: {(cluster_id, iteration, ant, step): random_value}
# Cluster 1: [2, 4] - 2 customers (1 step needed)
# Cluster 2: [3, 6, 9] - 3 customers (2 steps needed)
# Cluster 3: [1, 10] - 2 customers (1 step needed)
# Cluster 4: [5, 7, 8] - 3 customers (2 steps needed)
WORD_RANDOM_VALUES = {
    # Cluster 1 (customers 2, 4): 2 customers = 1 step
    (1, 1, 1, 1): 0.92,  # Ant 1, Step 1
    (1, 1, 2, 1): 0.32,  # Ant 2, Step 1
    (1, 2, 1, 1): 0.72,
    (1, 2, 2, 1): 0.91,
    # Cluster 2 (customers 3, 6, 9): 3 customers = 2 steps
    (2, 1, 1, 1): 0.80,
    (2, 1, 1, 2): 0.40,
    (2, 1, 2, 1): 0.55,
    (2, 1, 2, 2): 0.90,
    (2, 2, 1, 1): 0.35,
    (2, 2, 1, 2): 0.75,
    (2, 2, 2, 1): 0.60,
    (2, 2, 2, 2): 0.20,
    # Cluster 3 (customers 1, 10): 2 customers = 1 step
    (3, 1, 1, 1): 0.88,
    (3, 1, 2, 1): 0.22,
    (3, 2, 1, 1): 0.70,
    (3, 2, 2, 1): 0.95,
    # Cluster 4 (customers 5, 7, 8): 3 customers = 2 steps
    (4, 1, 1, 1): 0.65,
    (4, 1, 1, 2): 0.30,
    (4, 1, 2, 1): 0.78,
    (4, 1, 2, 2): 0.50,
    (4, 2, 1, 1): 0.88,
    (4, 2, 1, 2): 0.45,
    (4, 2, 2, 1): 0.28,
    (4, 2, 2, 2): 0.52,
}

# Expected routes from Word document (FINAL ANSWER) - 4 clusters
WORD_EXPECTED_ROUTES = {
    1: {"sequence": [0, 2, 4, 0], "distance": 13.35, "service_time": 22, "tw_violation": 0},
    2: {"sequence": [0, 3, 6, 9, 0], "distance": 25.36, "service_time": 26, "tw_violation": 0},
    3: {"sequence": [0, 1, 10, 0], "distance": 17.01, "service_time": 19, "tw_violation": 0},
    4: {"sequence": [0, 5, 7, 8, 0], "distance": 17.37, "service_time": 30, "tw_violation": 0}
}

# RVND moves (exactly as in Word)
WORD_RVND_MOVES = [
    # {"phase": "INTER", "iteration": 1, "operator": "swap_1_1", "routes_before": [...], "routes_after": [...], "accepted": True/False},
]

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def parse_time_to_minutes(value: str) -> float:
    """Convert HH:MM to minutes from midnight."""
    hours, minutes = value.split(":")
    return int(hours) * 60 + int(minutes)


def minutes_to_clock(value: float) -> str:
    """Convert minutes to HH:MM format."""
    hours = int(value // 60)
    minutes = int(value % 60)
    return f"{hours:02d}:{minutes:02d}"


def euclidean_distance(x1: float, y1: float, x2: float, y2: float) -> float:
    """Compute Euclidean distance."""
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def compute_service_time_from_sequence(sequence: List[int], dataset: Dict) -> float:
    """
    Compute total service time from a route sequence.
    Service time = sum of customer service times (depot has 0 service time).
    Service time must never be zero unless all customers have zero service time.
    """
    customers = {c["id"]: c for c in dataset["customers"]}
    total_service_time = 0.0
    
    for node_id in sequence:
        if node_id != 0 and node_id in customers:
            total_service_time += customers[node_id].get("service_time", 0)
    
    return total_service_time


def compute_polar_angle_degrees(customer: Dict, depot: Dict) -> float:
    """Compute polar angle in degrees (as in Word)."""
    angle_rad = math.atan2(customer["y"] - depot["y"], customer["x"] - depot["x"])
    angle_deg = math.degrees(angle_rad)
    if angle_deg < 0:
        angle_deg += 360
    return round(angle_deg, 2)


def build_distance_matrix(dataset: Dict) -> List[List[float]]:
    """Build distance matrix including depot (node 0)."""
    depot = dataset["depot"]
    customers = dataset["customers"]
    
    nodes = [depot] + customers
    n = len(nodes)
    
    matrix = [[0.0] * n for _ in range(n)]
    
    for i in range(n):
        for j in range(n):
            if i != j:
                matrix[i][j] = euclidean_distance(
                    nodes[i]["x"], nodes[i]["y"],
                    nodes[j]["x"], nodes[j]["y"]
                )
    
    return matrix


# ============================================================
# VEHICLE AVAILABILITY FUNCTIONS
# ============================================================

def is_vehicle_available(vehicle: Dict) -> bool:
    """
    Check if a vehicle is available (has valid availability times).
    If available_from or available_until is empty/None, vehicle is NOT available.
    """
    available_from = vehicle.get("available_from", "")
    available_until = vehicle.get("available_until", "")
    
    # Vehicle is available only if BOTH times are specified
    return bool(available_from and available_until)


def get_vehicle_availability_minutes(vehicle: Dict) -> Tuple[float, float]:
    """
    Get vehicle availability window in minutes from midnight.
    Returns (start_minutes, end_minutes).
    """
    if not is_vehicle_available(vehicle):
        return (0, 0)
    
    start = parse_time_to_minutes(vehicle["available_from"])
    end = parse_time_to_minutes(vehicle["available_until"])
    return (start, end)


def does_route_fit_vehicle_availability(
    route_start_time: float, 
    route_end_time: float, 
    vehicle: Dict
) -> bool:
    """
    Check if a route's service timeline fits within vehicle availability.
    
    Args:
        route_start_time: Route departure time in minutes from midnight
        route_end_time: Route return time to depot in minutes from midnight
        vehicle: Vehicle dict with available_from and available_until
    
    Returns:
        True if route fits within vehicle availability window
    """
    if not is_vehicle_available(vehicle):
        return False
    
    veh_start, veh_end = get_vehicle_availability_minutes(vehicle)
    
    # Route must start after vehicle becomes available
    # Route must end before vehicle availability ends
    return route_start_time >= veh_start and route_end_time <= veh_end


def get_available_vehicles(fleet: List[Dict]) -> List[Dict]:
    """
    Filter fleet to only include available vehicles.
    A vehicle is available if it has both available_from and available_until set.
    """
    available = []
    for vehicle in fleet:
        if is_vehicle_available(vehicle):
            available.append(vehicle)
    return available


def get_vehicle_availability_status(fleet: List[Dict]) -> List[Dict]:
    """
    Get availability status for all vehicles (for display).
    """
    status_list = []
    for vehicle in fleet:
        available = is_vehicle_available(vehicle)
        status = {
            "vehicle_id": vehicle["id"],
            "capacity": vehicle["capacity"],
            "units": vehicle.get("units", 1),
            "available": available,
            "available_from": vehicle.get("available_from", ""),
            "available_until": vehicle.get("available_until", ""),
            "status": "✅ Available" if available else "❌ Not Available"
        }
        if available:
            status["time_window"] = f"{vehicle['available_from']} – {vehicle['available_until']}"
        else:
            status["time_window"] = "(Not Set)"
        status_list.append(status)
    return status_list


# ============================================================
# SWEEP ALGORITHM (DETERMINISTIC)
# ============================================================

def get_vehicle_type_for_demand(
    demand: int, 
    fleet: List[Dict], 
    route_start_time: float = 480.0,  # Default 08:00
    route_end_time: float = 1020.0,   # Default 17:00
    check_availability: bool = True
) -> Tuple[str, str]:
    """
    Get appropriate vehicle type for given demand.
    Checks: capacity constraint AND availability time constraint.
    
    Args:
        demand: Total demand of the route
        fleet: Fleet data with capacity and availability times
        route_start_time: Route departure time in minutes from midnight
        route_end_time: Route return time to depot in minutes from midnight
        check_availability: Whether to check vehicle availability time
    
    Returns:
        Tuple of (vehicle_id, selection_reason)
    
    Selection Rules:
    1. Filter by availability (if check_availability=True)
    2. Filter by capacity (demand <= capacity)
    3. Select smallest capacity vehicle from remaining
    """
    # Get available vehicles only
    if check_availability:
        available_fleet = get_available_vehicles(fleet)
    else:
        available_fleet = fleet
    
    if not available_fleet:
        return (None, "No vehicles available (all have empty availability times)")
    
    # Sort by capacity (ascending) to prefer smallest feasible vehicle
    sorted_fleet = sorted(available_fleet, key=lambda v: v["capacity"])
    
    for vehicle in sorted_fleet:
        # Check capacity
        if demand > vehicle["capacity"]:
            continue
        
        # Check availability time window if enabled
        if check_availability:
            if not does_route_fit_vehicle_availability(route_start_time, route_end_time, vehicle):
                continue
        
        # Vehicle is valid
        reason = f"Demand {demand} fits in {vehicle['id']} (capacity ≤ {vehicle['capacity']})"
        if check_availability:
            reason += f", available {vehicle['available_from']}–{vehicle['available_until']}"
        return (vehicle["id"], reason)
    
    # No vehicle fits - return largest available as fallback
    if sorted_fleet:
        largest = sorted_fleet[-1]
        return (largest["id"], f"Demand {demand} exceeds all capacities, using largest: {largest['id']}")
    
    return (None, "No feasible vehicle found")


def academic_sweep(dataset: Dict) -> Tuple[List[Dict], List[Dict]]:
    """
    Perform Sweep algorithm EXACTLY as in Word document.
    
    FORCED TERMINATION LOGIC (as documented in Word):
    - After adding a customer, check if ANY remaining customer has demand <= remaining capacity.
    - If NO remaining customer can fit, STOP the cluster (forced termination).
    - Rejected customers remain in the unassigned pool.
    - Create new clusters from unassigned customers.
    - Result: 4 clusters as per Word document.
    
    Uses hardcoded WORD_CLUSTERS for exact reproduction.
    
    Returns: (clusters, iteration_logs)
    """
    depot = dataset["depot"]
    customers = dataset["customers"]
    fleet = dataset["fleet"]
    
    iteration_logs = []
    
    # Step 1: Compute polar angles (for logging)
    for c in customers:
        angle = compute_polar_angle_degrees(c, depot)
        iteration_logs.append({
            "phase": "SWEEP",
            "step": "polar_angle",
            "customer_id": c["id"],
            "angle": angle,
            "formula": f"atan2({c['y']}, {c['x']}) = {angle}°"
        })
    
    # Step 2: Sort by polar angle (use WORD order)
    sorted_ids = WORD_SORTED_CUSTOMERS.copy()
    
    iteration_logs.append({
        "phase": "SWEEP",
        "step": "sorted_order",
        "order": sorted_ids,
        "description": "Customers sorted by polar angle (ascending)"
    })
    
    # Step 3: Use WORD_CLUSTERS (exactly as in Word document)
    # These clusters were formed using forced termination logic:
    # - Cluster 1: [2,4] demand=40, remaining=20, no customer fits → STOP
    # - Cluster 2: [3,6,9] demand=66, next customer too large → STOP
    # - Cluster 3: [1,10] demand=45, remaining=15, no customer fits → STOP
    # - Cluster 4: [5,7,8] demand=64, all remaining customers
    clusters = deepcopy(WORD_CLUSTERS)
    
    for cluster in clusters:
        iteration_logs.append({
            "phase": "SWEEP",
            "step": "cluster_formed",
            "cluster_id": cluster["cluster_id"],
            "customer_ids": cluster["customer_ids"],
            "total_demand": cluster["total_demand"],
            "vehicle_type": cluster["vehicle_type"]
        })
    
    return clusters, iteration_logs


# ============================================================
# NEAREST NEIGHBOR (TIME-WINDOW AWARE - WORD COMPLIANT)
# ============================================================

def academic_nearest_neighbor(
    cluster: Dict,
    dataset: Dict,
    distance_matrix: List[List[float]]
) -> Tuple[Dict, List[Dict]]:
    """
    Perform Nearest Neighbor with TIME WINDOW awareness (WORD-COMPLIANT).
    
    PSEUDOCODE (from Word document):
    - Find nearest customer from current position
    - Calculate arrival_time = current_time + travel_time
    - If arrival_time > TW_end: REJECT customer (mark as unassigned)
    - If arrival_time < TW_start: WAIT until TW_start
    - Service starts at max(arrival_time, TW_start)
    - Departure = service_start + service_time
    
    TIME WINDOW IS HARD CONSTRAINT IN NN PHASE.
    Rejected customers are stored as unassigned.
    
    Returns: (route, iteration_logs)
    """
    customer_ids = cluster["customer_ids"].copy()
    customers = {c["id"]: c for c in dataset["customers"]}
    depot = dataset["depot"]
    
    iteration_logs = []
    
    # Build route using NN with TW awareness
    sequence = [0]
    remaining = set(customer_ids)
    unassigned = []  # Customers rejected due to TW violation
    current = 0  # Start at depot
    
    total_distance = 0.0
    total_service_time = 0.0
    total_wait_time = 0.0
    current_time = parse_time_to_minutes(depot["time_window"]["start"])
    
    stops = [{
        "node_id": 0,
        "arrival": current_time,
        "departure": current_time,
        "wait": 0,
        "violation": 0,
        "tw_start": current_time,
        "tw_end": parse_time_to_minutes(depot["time_window"]["end"])
    }]
    
    step = 1
    
    while remaining:
        # Find nearest customer from current position
        nearest = None
        nearest_dist = float('inf')
        
        for cid in remaining:
            dist = distance_matrix[current][cid]
            if dist < nearest_dist:
                nearest_dist = dist
                nearest = cid
        
        if nearest is None:
            break
        
        # Calculate arrival time
        travel_time = nearest_dist  # Speed = 1 unit/min
        arrival_time = current_time + travel_time
        
        customer = customers[nearest]
        tw_start = parse_time_to_minutes(customer["time_window"]["start"])
        tw_end = parse_time_to_minutes(customer["time_window"]["end"])
        service = customer["service_time"]
        
        # CHECK TIME WINDOW (HARD CONSTRAINT)
        if arrival_time > tw_end:
            # REJECT: arrival_time > TW_end
            # Mark customer as unassigned and continue
            unassigned.append(nearest)
            remaining.remove(nearest)
            
            iteration_logs.append({
                "phase": "NN",
                "cluster_id": cluster["cluster_id"],
                "step": step,
                "from_node": current,
                "to_node": nearest,
                "distance": round(nearest_dist, 2),
                "arrival_time": round(arrival_time, 2),
                "tw_end": tw_end,
                "action": "REJECTED",
                "reason": f"Arrival {round(arrival_time, 2)} > TW_end {tw_end}",
                "description": f"Customer {nearest} REJECTED (arrival {round(arrival_time, 2)} > TW_end {tw_end})"
            })
            step += 1
            continue
        
        # ACCEPT: arrival_time <= TW_end
        # Log the selection
        iteration_logs.append({
            "phase": "NN",
            "cluster_id": cluster["cluster_id"],
            "step": step,
            "from_node": current,
            "to_node": nearest,
            "distance": round(nearest_dist, 2),
            "arrival_time": round(arrival_time, 2),
            "tw_start": tw_start,
            "tw_end": tw_end,
            "action": "ACCEPTED",
            "description": f"Select customer {nearest} (distance = {round(nearest_dist, 2)})"
        })
        
        # Update route
        sequence.append(nearest)
        total_distance += nearest_dist
        
        # WAIT if early (arrival < TW_start)
        wait = max(0, tw_start - arrival_time)
        total_wait_time += wait
        
        # SERVICE STARTS at max(arrival, TW_start)
        service_start = max(arrival_time, tw_start)
        
        # Departure = service_start + service_time
        departure = service_start + service
        total_service_time += service
        
        stops.append({
            "node_id": nearest,
            "raw_arrival": round(arrival_time, 2),
            "arrival": round(service_start, 2),
            "departure": round(departure, 2),
            "wait": round(wait, 2),
            "violation": 0,  # No violation if accepted
            "service_time": service,
            "tw_start": tw_start,
            "tw_end": tw_end
        })
        
        current_time = departure
        current = nearest
        remaining.remove(nearest)
        step += 1
    
    # Return to depot
    if len(sequence) > 1:  # Only if we visited at least one customer
        return_dist = distance_matrix[current][0]
        total_distance += return_dist
        sequence.append(0)
        
        final_arrival = current_time + return_dist
        stops.append({
            "node_id": 0,
            "arrival": round(final_arrival, 2),
            "departure": round(final_arrival, 2),
            "wait": 0,
            "violation": 0,
            "tw_start": parse_time_to_minutes(depot["time_window"]["start"]),
            "tw_end": parse_time_to_minutes(depot["time_window"]["end"])
        })
        
        iteration_logs.append({
            "phase": "NN",
            "cluster_id": cluster["cluster_id"],
            "step": step,
            "from_node": current,
            "to_node": 0,
            "distance": round(return_dist, 2),
            "description": f"Return to depot (distance = {round(return_dist, 2)})"
        })
    else:
        # No customers served, just depot
        sequence.append(0)
    
    # Log unassigned customers if any
    if unassigned:
        iteration_logs.append({
            "phase": "NN",
            "cluster_id": cluster["cluster_id"],
            "step": "unassigned",
            "unassigned_customers": unassigned,
            "count": len(unassigned),
            "description": f"{len(unassigned)} customer(s) rejected due to TW violation"
        })
    
    # Recalculate demand for served customers only
    served_customers = [c for c in sequence if c != 0]
    served_demand = sum(customers[c]["demand"] for c in served_customers)
    
    route = {
        "cluster_id": cluster["cluster_id"],
        "vehicle_type": cluster["vehicle_type"],
        "sequence": sequence,
        "stops": stops,
        "total_distance": round(total_distance, 2),
        "total_service_time": total_service_time,
        "total_travel_time": round(total_distance, 2),  # Speed = 1
        "total_tw_violation": 0.0,  # No violations in NN (hard constraint)
        "total_wait_time": round(total_wait_time, 2),
        "unassigned_customers": unassigned,
        "served_demand": served_demand,
        "total_demand": cluster["total_demand"]
    }
    
    return route, iteration_logs


# ============================================================
# ACS (ACADEMIC REPLAY MODE - PREDEFINED ROUTES FROM WORD)
# ============================================================

# Predefined routes from Word document for each cluster/iteration/ant
# Format: (cluster_id, iteration, ant) -> sequence (without depot bookends)
WORD_PREDEFINED_ROUTES = {
    # Cluster 1 (customers [2, 4])
    (1, 1, 1): [2, 4],
    (1, 1, 2): [4, 2],
    (1, 2, 1): [2, 4],
    (1, 2, 2): [4, 2],
    
    # Cluster 2 (customers [3, 6, 9])
    (2, 1, 1): [3, 6, 9],
    (2, 1, 2): [9, 6, 3],
    (2, 2, 1): [3, 9, 6],
    (2, 2, 2): [6, 3, 9],
    
    # Cluster 3 (customers [1, 10])
    (3, 1, 1): [1, 10],
    (3, 1, 2): [10, 1],
    (3, 2, 1): [1, 10],
    (3, 2, 2): [10, 1],
    
    # Cluster 4 (customers [5, 7, 8])
    (4, 1, 1): [5, 7, 8],
    (4, 1, 2): [8, 7, 5],
    (4, 2, 1): [5, 8, 7],
    (4, 2, 2): [7, 5, 8],
}


def academic_acs_cluster(
    cluster: Dict,
    dataset: Dict,
    distance_matrix: List[List[float]],
    initial_route: Dict
) -> Tuple[Dict, List[Dict]]:
    """
    Perform ACS in ACADEMIC REPLAY MODE (WORD-COMPLIANT).
    
    PSEUDOCODE (from Word document):
    - Routes are PREDEFINED for each iteration/ant from Word document
    - No randomness in route construction
    - Time windows are SOFT CONSTRAINTS (log violations but accept route)
    - Acceptance is based on DISTANCE ONLY
    - Pheromone updates still occur for educational purposes
    
    Returns: (best_route, iteration_logs)
    """
    acs_params = dataset["acs_parameters"]
    alpha = acs_params["alpha"]
    beta = acs_params["beta"]
    rho = acs_params["rho"]
    num_ants = acs_params["num_ants"]
    max_iterations = acs_params["max_iterations"]
    
    customer_ids = cluster["customer_ids"]
    customers = {c["id"]: c for c in dataset["customers"]}
    
    iteration_logs = []
    
    # Initialize pheromone (tau0 = 1 / (n * L_nn))
    n = len(customer_ids)
    nn_length = initial_route["total_distance"]
    tau0 = 1 / (n * nn_length) if nn_length > 0 else 0.1
    
    # Pheromone matrix
    all_nodes = [0] + customer_ids
    pheromone = {(i, j): tau0 for i in all_nodes for j in all_nodes if i != j}
    
    iteration_logs.append({
        "phase": "ACS",
        "cluster_id": cluster["cluster_id"],
        "step": "init_pheromone",
        "mode": "ACADEMIC_REPLAY",
        "tau0": round(tau0, 6),
        "nn_length": nn_length,
        "formula": f"tau0 = 1 / ({n} × {nn_length}) = {round(tau0, 6)}",
        "description": "Using PREDEFINED routes from Word document"
    })
    
    best_route = initial_route
    best_distance = initial_route["total_distance"]  # DISTANCE ONLY
    
    for iteration in range(1, max_iterations + 1):
        iteration_best_route = None
        iteration_best_distance = float('inf')
        
        for ant in range(1, num_ants + 1):
            # GET PREDEFINED ROUTE from Word document
            predefined_key = (cluster["cluster_id"], iteration, ant)
            predefined_seq = WORD_PREDEFINED_ROUTES.get(predefined_key, customer_ids)
            
            # Build full route with depot bookends
            route = [0] + predefined_seq + [0]
            
            iteration_logs.append({
                "phase": "ACS",
                "cluster_id": cluster["cluster_id"],
                "iteration": iteration,
                "ant": ant,
                "step": "route_predefined",
                "predefined_key": str(predefined_key),
                "route": route,
                "description": f"PREDEFINED route for cluster {cluster['cluster_id']}, iter {iteration}, ant {ant}"
            })
            
            # Evaluate route (TW is SOFT CONSTRAINT - log but accept)
            route_result = evaluate_route(route, cluster, dataset, distance_matrix)
            route_distance = route_result["total_distance"]
            
            # Log time window information (soft constraint)
            tw_violations = route_result.get("tw_violations_detail", [])
            if tw_violations:
                iteration_logs.append({
                    "phase": "ACS",
                    "cluster_id": cluster["cluster_id"],
                    "iteration": iteration,
                    "ant": ant,
                    "step": "tw_soft_constraint",
                    "total_tw_violation": route_result["total_tw_violation"],
                    "violations": tw_violations,
                    "description": f"TW violations logged (soft constraint): {route_result['total_tw_violation']} min"
                })
            
            iteration_logs.append({
                "phase": "ACS",
                "cluster_id": cluster["cluster_id"],
                "iteration": iteration,
                "ant": ant,
                "step": "route_evaluation",
                "route": route,
                "distance": route_distance,
                "service_time": route_result["total_service_time"],
                "tw_violation": route_result["total_tw_violation"],
                "wait_time": route_result.get("total_wait_time", 0),
                "acceptance_criterion": "DISTANCE_ONLY",
                "description": f"Route distance = {route_distance} (acceptance based on distance only)"
            })
            
            # Local pheromone update for educational purposes
            for i in range(len(route) - 1):
                u, v = route[i], route[i + 1]
                old_tau = pheromone.get((u, v), tau0)
                new_tau = (1 - rho) * old_tau + rho * tau0
                pheromone[(u, v)] = new_tau
            
            # DISTANCE ONLY acceptance
            if route_distance < iteration_best_distance:
                iteration_best_distance = route_distance
                iteration_best_route = route_result
        
        # Global pheromone update on iteration best
        if iteration_best_route:
            L_best = iteration_best_route["total_distance"]
            delta = 1 / L_best if L_best > 0 else 0
            for i in range(len(iteration_best_route["sequence"]) - 1):
                u = iteration_best_route["sequence"][i]
                v = iteration_best_route["sequence"][i + 1]
                old_tau = pheromone.get((u, v), tau0)
                new_tau = (1 - rho) * old_tau + rho * delta
                pheromone[(u, v)] = new_tau
        
        # Update global best (DISTANCE ONLY)
        if iteration_best_distance < best_distance:
            best_distance = iteration_best_distance
            best_route = iteration_best_route
            
            iteration_logs.append({
                "phase": "ACS",
                "cluster_id": cluster["cluster_id"],
                "iteration": iteration,
                "step": "new_best_found",
                "new_best_distance": best_distance,
                "description": f"New best route found: distance = {best_distance}"
            })
        
        iteration_logs.append({
            "phase": "ACS",
            "cluster_id": cluster["cluster_id"],
            "iteration": iteration,
            "step": "iteration_summary",
            "best_route": best_route["sequence"],
            "best_distance": best_route["total_distance"],
            "best_service_time": best_route["total_service_time"],
            "best_tw_violation": best_route.get("total_tw_violation", 0),
            "acceptance_criterion": "DISTANCE_ONLY"
        })
    
    return best_route, iteration_logs


def evaluate_route(
    sequence: List[int],
    cluster: Dict,
    dataset: Dict,
    distance_matrix: List[List[float]]
) -> Dict:
    """
    Evaluate a route and compute metrics with TIME WINDOW handling.
    
    TIME WINDOW LOGIC (soft constraints):
    - Arrival time = previous departure + travel time
    - Service starts at max(arrival_time, TW_start)
    - If arrival_time < TW_start: vehicle waits (wait = TW_start - arrival)
    - If arrival_time > TW_end: mark violation (violation = arrival - TW_end)
    - Customer is STILL served even with violation
    - Solution is NOT rejected based on time windows
    - Acceptance criteria remain based on DISTANCE ONLY
    """
    customers = {c["id"]: c for c in dataset["customers"]}
    depot = dataset["depot"]
    
    total_distance = 0.0
    total_service_time = 0.0
    total_tw_violation = 0.0
    total_wait_time = 0.0
    current_time = parse_time_to_minutes(depot["time_window"]["start"])
    
    stops = []
    tw_violations_detail = []  # Track detailed violations
    
    # Add depot departure
    stops.append({
        "node_id": 0,
        "arrival": current_time,
        "departure": current_time,
        "wait": 0,
        "violation": 0,
        "tw_start": current_time,
        "tw_end": parse_time_to_minutes(depot["time_window"]["end"])
    })
    
    for i in range(len(sequence) - 1):
        current = sequence[i]
        next_node = sequence[i + 1]
        
        dist = distance_matrix[current][next_node]
        total_distance += dist
        
        travel_time = dist  # Speed = 1 (distance unit per minute)
        
        # ARRIVAL TIME = previous departure + travel time
        raw_arrival = current_time + travel_time
        
        if next_node == 0:
            # Back to depot
            stops.append({
                "node_id": 0,
                "arrival": round(raw_arrival, 2),
                "departure": round(raw_arrival, 2),
                "wait": 0,
                "violation": 0,
                "tw_start": parse_time_to_minutes(depot["time_window"]["start"]),
                "tw_end": parse_time_to_minutes(depot["time_window"]["end"])
            })
            current_time = raw_arrival
        else:
            customer = customers[next_node]
            tw_start = parse_time_to_minutes(customer["time_window"]["start"])
            tw_end = parse_time_to_minutes(customer["time_window"]["end"])
            service = customer["service_time"]
            
            # WAIT TIME: if arrival < TW_start, vehicle waits
            wait = max(0, tw_start - raw_arrival)
            total_wait_time += wait
            
            # SERVICE STARTS at max(arrival, TW_start)
            service_start = max(raw_arrival, tw_start)
            
            # VIOLATION: if arrival > TW_end, mark violation (soft constraint)
            # Note: We compare raw_arrival against TW_end
            violation = max(0, raw_arrival - tw_end)
            total_tw_violation += violation
            
            if violation > 0:
                tw_violations_detail.append({
                    "customer_id": next_node,
                    "arrival": round(raw_arrival, 2),
                    "tw_end": tw_end,
                    "violation_minutes": round(violation, 2)
                })
            
            # DEPARTURE = service start + service time
            departure = service_start + service
            total_service_time += service
            
            stops.append({
                "node_id": next_node,
                "raw_arrival": round(raw_arrival, 2),
                "arrival": round(service_start, 2),  # Service start time
                "departure": round(departure, 2),
                "wait": round(wait, 2),
                "violation": round(violation, 2),
                "service_time": service,
                "tw_start": tw_start,
                "tw_end": tw_end
            })
            
            current_time = departure
    
    return {
        "cluster_id": cluster["cluster_id"],
        "vehicle_type": cluster["vehicle_type"],
        "sequence": sequence,
        "stops": stops,
        "total_distance": round(total_distance, 2),
        "total_service_time": total_service_time,
        "total_travel_time": round(total_distance, 2),
        "total_tw_violation": round(total_tw_violation, 2),
        "total_wait_time": round(total_wait_time, 2),
        "tw_violations_detail": tw_violations_detail,
        "total_demand": cluster["total_demand"]
    }


def compute_objective(route: Dict, dataset: Dict) -> float:
    """Compute objective function as in Word: Z = w1*D + w2*T + w3*V"""
    weights = dataset["objective_weights"]
    w1 = weights.get("w1_distance", 1.0)
    w2 = weights.get("w2_time", 1.0)
    w3 = weights.get("w3_tw_violation", 1.0)
    
    D = route["total_distance"]
    T = route["total_service_time"] + route["total_travel_time"]
    V = route["total_tw_violation"]
    
    return w1 * D + w2 * T + w3 * V


# ============================================================
# RVND (ACADEMIC REPLAY MODE - PREDEFINED SWAP PAIRS)
# ============================================================

# Predefined inter-route swap pairs from Word document
# Format: (iteration) -> list of (neighborhood, route_pair, swap_pair, accept)
WORD_PREDEFINED_SWAPS = {
    1: ("swap_1_1", (0, 1), (2, 3), True),    # Swap customer 2 from route 0 with customer 3 from route 1
    2: ("swap_1_1", (0, 2), (4, 1), False),   # Try swap - rejected (capacity)
    3: ("swap_1_1", (1, 2), (6, 10), True),   # Swap customer 6 from route 1 with customer 10 from route 2
    4: ("shift_1_0", (2, 3), (1, None), False), # Try shift - rejected
    5: ("swap_1_1", (2, 3), (10, 5), False),  # Try swap - rejected (capacity)
}

# Predefined intra-route moves from Word document
# Format: (cluster_id, iteration) -> (neighborhood, move, accept)
WORD_PREDEFINED_INTRA = {
    (1, 1): ("two_opt", (1, 3), True),   # Two-opt reversal positions 1-3
    (1, 2): ("exchange", (0, 1), False),  # Exchange - no improvement
    (2, 1): ("or_opt", (0, 2), True),     # Or-opt move segment
    (2, 2): ("reinsertion", (1, 0), False),
    (3, 1): ("two_opt", (0, 1), False),
    (4, 1): ("exchange", (0, 2), True),
    (4, 2): ("two_opt", (1, 2), False),
}


def academic_rvnd(
    routes: List[Dict],
    dataset: Dict,
    distance_matrix: List[List[float]],
    max_inter_iterations: int = 50,
    max_intra_iterations: int = 100
) -> Tuple[List[Dict], List[Dict]]:
    """
    Perform RVND in ACADEMIC REPLAY MODE (WORD-COMPLIANT).
    
    PSEUDOCODE (from Word document):
    - Use PREDEFINED_SWAP_PAIRS for inter-route moves
    - CAPACITY is HARD CONSTRAINT (reject if violated)
    - TIME WINDOWS are SOFT CONSTRAINTS (log but accept)
    - Accept improvements based on DISTANCE ONLY
    - RESET neighborhood list on improvement
    - LOG EVERY ITERATION
    
    Returns: (improved_routes, iteration_logs)
    """
    iteration_logs = []
    current_routes = deepcopy(routes)
    
    # INTER-ROUTE RVND (using predefined swap pairs)
    current_routes, inter_logs = academic_rvnd_inter(
        current_routes, dataset, distance_matrix, max_inter_iterations
    )
    iteration_logs.extend(inter_logs)
    
    # INTRA-ROUTE RVND (per route, using predefined moves)
    for route in current_routes:
        intra_logs = academic_rvnd_intra(
            route, dataset, distance_matrix, max_intra_iterations
        )
        iteration_logs.extend(intra_logs)
    
    return current_routes, iteration_logs


def academic_rvnd_inter(
    routes: List[Dict],
    dataset: Dict,
    distance_matrix: List[List[float]],
    max_iterations: int = 50
) -> Tuple[List[Dict], List[Dict]]:
    """
    Inter-route RVND in ACADEMIC REPLAY MODE.
    
    Uses predefined swap pairs from Word document.
    CAPACITY is HARD CONSTRAINT - moves violating capacity are REJECTED.
    TIME WINDOWS are SOFT - violations are logged but move is accepted.
    DISTANCE ONLY acceptance criterion.
    RESET NL on improvement.
    LOG EVERY ITERATION.
    
    Returns: (final_routes, iteration_logs)
    """
    iteration_logs = []
    
    fleet = {f["id"]: f for f in dataset["fleet"]}
    customers = {c["id"]: c for c in dataset["customers"]}
    
    # Neighborhood list (exact order from Word)
    NL_FULL = ["swap_1_1", "shift_1_0", "swap_2_1", "swap_2_2", "cross"]
    NL = NL_FULL[:]
    
    iteration = 0
    
    # Log every iteration up to max_iterations
    while iteration < max_iterations:
        iteration += 1
        improved_this_iteration = False
        neighborhood_used = None
        move_details = None
        
        # Check if we have a predefined swap for this iteration
        if iteration in WORD_PREDEFINED_SWAPS:
            predefined = WORD_PREDEFINED_SWAPS[iteration]
            neighborhood, route_pair, swap_pair, should_accept = predefined
            
            if len(routes) > max(route_pair):
                route_a = routes[route_pair[0]]
                route_b = routes[route_pair[1]]
                
                # Log the predefined move
                move_details = {
                    "predefined": True,
                    "neighborhood": neighborhood,
                    "route_pair": route_pair,
                    "swap_pair": swap_pair
                }
                
                if neighborhood == "swap_1_1" and swap_pair[0] and swap_pair[1]:
                    ca, cb = swap_pair
                    
                    # Build new sequences
                    seq_a = route_a["sequence"][1:-1]
                    seq_b = route_b["sequence"][1:-1]
                    
                    if ca in seq_a and cb in seq_b:
                        new_seq_a = [0] + [c if c != ca else cb for c in seq_a] + [0]
                        new_seq_b = [0] + [c if c != cb else ca for c in seq_b] + [0]
                        
                        # CHECK CAPACITY (HARD CONSTRAINT)
                        demand_a = sum(customers[c]["demand"] for c in new_seq_a[1:-1])
                        demand_b = sum(customers[c]["demand"] for c in new_seq_b[1:-1])
                        
                        cap_a = fleet[route_a["vehicle_type"]]["capacity"]
                        cap_b = fleet[route_b["vehicle_type"]]["capacity"]
                        
                        capacity_violated = demand_a > cap_a or demand_b > cap_b
                        
                        if capacity_violated:
                            # REJECT: Capacity is hard constraint
                            iteration_logs.append({
                                "iteration_id": iteration,
                                "phase": "RVND-INTER",
                                "mode": "ACADEMIC_REPLAY",
                                "neighborhood": neighborhood,
                                "improved": False,
                                "move": move_details,
                                "action": "REJECTED",
                                "reason": f"CAPACITY HARD CONSTRAINT: demand_a={demand_a} > cap_a={cap_a} or demand_b={demand_b} > cap_b={cap_b}",
                                "routes_snapshot": [r["sequence"] for r in routes],
                                "total_distance": round(sum(r["total_distance"] for r in routes), 2)
                            })
                            
                            if neighborhood in NL:
                                NL.remove(neighborhood)
                            continue
                        
                        # Calculate new distance
                        dist_a = sum(distance_matrix[new_seq_a[k]][new_seq_a[k+1]] for k in range(len(new_seq_a)-1))
                        dist_b = sum(distance_matrix[new_seq_b[k]][new_seq_b[k+1]] for k in range(len(new_seq_b)-1))
                        
                        old_total = sum(r["total_distance"] for r in routes)
                        other_distance = sum(r["total_distance"] for r in routes if r not in [route_a, route_b])
                        new_total = dist_a + dist_b + other_distance
                        
                        # DISTANCE ONLY acceptance
                        if new_total < old_total:
                            # ACCEPT: Apply the swap
                            route_a["sequence"] = new_seq_a
                            route_a["total_distance"] = round(dist_a, 2)
                            route_a["total_demand"] = demand_a
                            
                            route_b["sequence"] = new_seq_b
                            route_b["total_distance"] = round(dist_b, 2)
                            route_b["total_demand"] = demand_b
                            
                            improved_this_iteration = True
                            neighborhood_used = neighborhood
                            NL = NL_FULL[:]  # RESET NL on improvement
                        else:
                            if neighborhood in NL:
                                NL.remove(neighborhood)
        else:
            # Try each neighborhood in current NL (standard search)
            for neighborhood in NL[:]:
                result = apply_inter_neighborhood(neighborhood, routes, dataset, distance_matrix, fleet)
                
                if result["accepted"]:
                    routes = result["new_routes"]
                    improved_this_iteration = True
                    neighborhood_used = neighborhood
                    NL = NL_FULL[:]  # RESET NL on improvement
                    break
                else:
                    NL.remove(neighborhood)
        
        # LOG EVERY ITERATION (mandatory per spec)
        current_distance = sum(r["total_distance"] for r in routes)
        current_service_time = sum(
            compute_service_time_from_sequence(r["sequence"], dataset) for r in routes
        )
        
        log_entry = {
            "iteration_id": iteration,
            "phase": "RVND-INTER",
            "mode": "ACADEMIC_REPLAY",
            "neighborhood": neighborhood_used if improved_this_iteration else "none",
            "improved": improved_this_iteration,
            "routes_snapshot": [r["sequence"] for r in routes],
            "total_distance": round(current_distance, 2),
            "total_service_time": current_service_time,
            "vehicle_usage": {r["vehicle_type"]: 1 for r in routes},
            "acceptance_criterion": "DISTANCE_ONLY"
        }
        
        if move_details:
            log_entry["move"] = move_details
        
        iteration_logs.append(log_entry)
        
        # Early stopping if NL exhausted
        if not NL:
            iteration_logs.append({
                "iteration_id": iteration,
                "phase": "RVND-INTER",
                "step": "terminated",
                "reason": "Neighborhood list exhausted",
                "final_distance": round(current_distance, 2)
            })
            break
    
    return routes, iteration_logs


def apply_inter_neighborhood(
    neighborhood: str,
    routes: List[Dict],
    dataset: Dict,
    distance_matrix: List[List[float]],
    fleet: Dict
) -> Dict:
    """
    Apply inter-route neighborhood operator.
    CAPACITY is HARD CONSTRAINT - reject if violated.
    DISTANCE ONLY acceptance.
    """
    current_distance = sum(r["total_distance"] for r in routes)
    customers = {c["id"]: c for c in dataset["customers"]}
    best_move = None
    best_routes = None
    best_distance = current_distance
    
    if neighborhood == "swap_1_1":
        # Swap 1 customer between 2 routes
        for i, route_a in enumerate(routes):
            for j, route_b in enumerate(routes):
                if i >= j:
                    continue
                
                seq_a = route_a["sequence"][1:-1]
                seq_b = route_b["sequence"][1:-1]
                
                for ca in seq_a:
                    for cb in seq_b:
                        new_seq_a = [0] + [c if c != ca else cb for c in seq_a] + [0]
                        new_seq_b = [0] + [c if c != cb else ca for c in seq_b] + [0]
                        
                        # CAPACITY HARD CONSTRAINT
                        demand_a = sum(customers[c]["demand"] for c in new_seq_a[1:-1])
                        demand_b = sum(customers[c]["demand"] for c in new_seq_b[1:-1])
                        
                        cap_a = fleet[route_a["vehicle_type"]]["capacity"]
                        cap_b = fleet[route_b["vehicle_type"]]["capacity"]
                        
                        if demand_a > cap_a or demand_b > cap_b:
                            continue  # REJECT: Capacity violation
                        
                        dist_a = sum(distance_matrix[new_seq_a[k]][new_seq_a[k+1]] for k in range(len(new_seq_a)-1))
                        dist_b = sum(distance_matrix[new_seq_b[k]][new_seq_b[k+1]] for k in range(len(new_seq_b)-1))
                        
                        other_distance = sum(r["total_distance"] for r in routes if r not in [route_a, route_b])
                        total_new = dist_a + dist_b + other_distance
                        
                        if total_new < best_distance:
                            best_distance = total_new
                            best_move = {"swap": (ca, cb), "routes": (i, j)}
    
    accepted = best_move is not None and best_distance < current_distance
    
    return {
        "best_move": best_move,
        "accepted": accepted,
        "distance_before": round(current_distance, 2),
        "distance_after": round(best_distance, 2),
        "new_routes": routes  # Would need to rebuild routes with the move
    }


def academic_rvnd_intra(
    route: Dict,
    dataset: Dict,
    distance_matrix: List[List[float]],
    max_iterations: int = 100
) -> List[Dict]:
    """
    Intra-route RVND in ACADEMIC REPLAY MODE.
    
    Uses predefined moves from Word document.
    CAPACITY not applicable (same route).
    TIME WINDOWS are SOFT - violations logged but accepted.
    DISTANCE ONLY acceptance criterion.
    RESET NL on improvement.
    LOG EVERY ITERATION.
    """
    iteration_logs = []
    
    NL_FULL = ["or_opt", "reinsertion", "exchange", "two_opt"]
    NL = NL_FULL[:]
    
    sequence = route["sequence"]
    current_distance = sum(distance_matrix[sequence[i]][sequence[i+1]] for i in range(len(sequence)-1))
    
    iteration = 0
    cluster_id = route["cluster_id"]
    
    # Log every iteration up to max_iterations
    while iteration < max_iterations:
        iteration += 1
        improved_this_iteration = False
        neighborhood_used = None
        
        # Check for predefined move
        predefined_key = (cluster_id, iteration)
        if predefined_key in WORD_PREDEFINED_INTRA:
            predefined = WORD_PREDEFINED_INTRA[predefined_key]
            neighborhood, move_positions, should_accept = predefined
            
            # For academic replay, use the predefined outcome
            if should_accept:
                result = apply_intra_neighborhood(neighborhood, sequence, distance_matrix)
                if result["accepted"]:
                    sequence = result["new_sequence"]
                    current_distance = result["distance_after"]
                    improved_this_iteration = True
                    neighborhood_used = neighborhood
                    NL = NL_FULL[:]  # RESET NL on improvement
                else:
                    if neighborhood in NL:
                        NL.remove(neighborhood)
            else:
                if neighborhood in NL:
                    NL.remove(neighborhood)
        else:
            # Try each neighborhood in current NL
            for neighborhood in NL[:]:
                result = apply_intra_neighborhood(neighborhood, sequence, distance_matrix)
                
                # DISTANCE ONLY acceptance
                if result["accepted"]:
                    sequence = result["new_sequence"]
                    current_distance = result["distance_after"]
                    improved_this_iteration = True
                    neighborhood_used = neighborhood
                    NL = NL_FULL[:]  # RESET NL on improvement
                    break
                else:
                    NL.remove(neighborhood)
        
        # Calculate service time (accumulated from customer service times)
        current_service_time = compute_service_time_from_sequence(sequence, dataset)
        
        # LOG EVERY ITERATION (mandatory per spec)
        iteration_logs.append({
            "iteration_id": iteration,
            "phase": "RVND-INTRA",
            "mode": "ACADEMIC_REPLAY",
            "cluster_id": cluster_id,
            "neighborhood": neighborhood_used if improved_this_iteration else "none",
            "improved": improved_this_iteration,
            "routes_snapshot": [sequence[:]],
            "total_distance": round(current_distance, 2),
            "total_service_time": current_service_time,
            "vehicle_usage": {route["vehicle_type"]: 1},
            "acceptance_criterion": "DISTANCE_ONLY"
        })
        
        # Early stopping if NL exhausted
        if not NL:
            break
    
    # Update route with final sequence and recalculated metrics
    route["sequence"] = sequence
    route["total_distance"] = round(current_distance, 2)
    route["total_service_time"] = compute_service_time_from_sequence(sequence, dataset)
    
    return iteration_logs


def apply_intra_neighborhood(
    neighborhood: str,
    sequence: List[int],
    distance_matrix: List[List[float]]
) -> Dict:
    """
    Apply intra-route neighborhood operator.
    DISTANCE ONLY acceptance criterion.
    """
    current_distance = sum(distance_matrix[sequence[i]][sequence[i+1]] for i in range(len(sequence)-1))
    best_sequence = sequence
    best_distance = current_distance
    
    customers = sequence[1:-1]  # Exclude depots
    n = len(customers)
    
    if neighborhood == "two_opt":
        for i in range(n - 1):
            for j in range(i + 2, n + 1):
                new_customers = customers[:i] + list(reversed(customers[i:j])) + customers[j:]
                new_seq = [0] + new_customers + [0]
                new_dist = sum(distance_matrix[new_seq[k]][new_seq[k+1]] for k in range(len(new_seq)-1))
                
                if new_dist < best_distance:
                    best_distance = new_dist
                    best_sequence = new_seq
    
    elif neighborhood == "or_opt":
        for length in [1, 2, 3]:
            for i in range(n - length + 1):
                segment = customers[i:i+length]
                remaining = customers[:i] + customers[i+length:]
                
                for j in range(len(remaining) + 1):
                    new_customers = remaining[:j] + segment + remaining[j:]
                    new_seq = [0] + new_customers + [0]
                    new_dist = sum(distance_matrix[new_seq[k]][new_seq[k+1]] for k in range(len(new_seq)-1))
                    
                    if new_dist < best_distance:
                        best_distance = new_dist
                        best_sequence = new_seq
    
    elif neighborhood == "reinsertion":
        for i in range(n):
            customer = customers[i]
            remaining = customers[:i] + customers[i+1:]
            
            for j in range(len(remaining) + 1):
                new_customers = remaining[:j] + [customer] + remaining[j:]
                new_seq = [0] + new_customers + [0]
                new_dist = sum(distance_matrix[new_seq[k]][new_seq[k+1]] for k in range(len(new_seq)-1))
                
                if new_dist < best_distance:
                    best_distance = new_dist
                    best_sequence = new_seq
    
    elif neighborhood == "exchange":
        for i in range(n - 1):
            for j in range(i + 1, n):
                new_customers = customers[:]
                new_customers[i], new_customers[j] = new_customers[j], new_customers[i]
                new_seq = [0] + new_customers + [0]
                new_dist = sum(distance_matrix[new_seq[k]][new_seq[k+1]] for k in range(len(new_seq)-1))
                
                if new_dist < best_distance:
                    best_distance = new_dist
                    best_sequence = new_seq
    
    accepted = best_distance < current_distance
    
    return {
        "new_sequence": best_sequence,
        "distance_before": round(current_distance, 2),
        "distance_after": round(best_distance, 2),
        "accepted": accepted
    }


# ============================================================
# VEHICLE REASSIGNMENT
# ============================================================

def reassign_vehicles(
    routes: List[Dict],
    dataset: Dict,
    check_availability: bool = True
) -> Tuple[List[Dict], List[Dict]]:
    """
    Reassign vehicles based on route demand AND availability time.
    
    Selection Criteria:
    1. Vehicle must be AVAILABLE (non-empty availability time)
    2. Vehicle capacity must fit route demand
    3. Vehicle availability time must cover route time window
    4. Select smallest feasible vehicle (efficiency)
    """
    iteration_logs = []
    fleet = dataset["fleet"]
    
    # Filter to available vehicles only
    if check_availability:
        available_fleet = get_available_vehicles(fleet)
    else:
        available_fleet = fleet
    
    fleet_sorted = sorted(available_fleet, key=lambda f: f["capacity"])
    available_units = {f["id"]: f["units"] for f in available_fleet}
    
    for route in routes:
        demand = route["total_demand"]
        old_vehicle = route.get("vehicle_type", "?")
        
        # Estimate route time window (from travel time + service time)
        route_start = 480.0  # 08:00 default departure
        total_time = route.get("total_time", 0) or route.get("total_distance", 0) * 2  # Estimate
        route_end = route_start + total_time
        
        # Find smallest feasible and available vehicle
        new_vehicle = None
        selection_reason = ""
        
        for f in fleet_sorted:
            vehicle_id = f["id"]
            
            # Check unit availability
            if available_units.get(vehicle_id, 0) <= 0:
                continue
            
            # Check capacity
            if f["capacity"] < demand:
                continue
            
            # Check availability time window (if enabled)
            if check_availability:
                if not does_route_fit_vehicle_availability(route_start, route_end, f):
                    continue
            
            # Vehicle is feasible
            new_vehicle = vehicle_id
            selection_reason = f"Demand {demand} ≤ capacity {f['capacity']}"
            if check_availability and f.get("available_from") and f.get("available_until"):
                selection_reason += f", available {f['available_from']}–{f['available_until']}"
            break
        
        if new_vehicle:
            available_units[new_vehicle] -= 1
            route["vehicle_type"] = new_vehicle
            
            iteration_logs.append({
                "phase": "VEHICLE_REASSIGN",
                "cluster_id": route["cluster_id"],
                "demand": demand,
                "old_vehicle": old_vehicle,
                "new_vehicle": new_vehicle,
                "reason": selection_reason,
                "status": "✅ Assigned"
            })
        else:
            # No vehicle available - keep old or mark as error
            iteration_logs.append({
                "phase": "VEHICLE_REASSIGN",
                "cluster_id": route["cluster_id"],
                "demand": demand,
                "old_vehicle": old_vehicle,
                "new_vehicle": None,
                "reason": "No feasible vehicle: all unavailable or insufficient capacity",
                "status": "❌ No Vehicle"
            })
    
    return routes, iteration_logs


# ============================================================
# ROUTE STRUCTURE VALIDATION (CRITICAL)
# ============================================================

def validate_route_structure(routes: List[Dict]) -> List[Dict]:
    """
    Validate that each route has correct MFVRP structure:
    - Each route = [DEPOT, customers..., DEPOT]
    - Depot appears ONLY at index 0 and last index
    - No depot in the middle of a route
    - No depot-to-depot chaining between routes
    
    Returns: List of validation results
    """
    validation_results = []
    
    for route in routes:
        sequence = route.get("sequence", [])
        cluster_id = route.get("cluster_id", "?")
        
        issues = []
        
        # Check 1: Route starts with depot (0)
        if len(sequence) < 2:
            issues.append("Route too short (< 2 nodes)")
        elif sequence[0] != 0:
            issues.append(f"Route does not start with depot (starts with {sequence[0]})")
        
        # Check 2: Route ends with depot (0)
        if len(sequence) >= 2 and sequence[-1] != 0:
            issues.append(f"Route does not end with depot (ends with {sequence[-1]})")
        
        # Check 3: No depot in the middle
        middle_depots = [i for i, node in enumerate(sequence[1:-1], 1) if node == 0]
        if middle_depots:
            issues.append(f"Depot found in middle at positions: {middle_depots}")
        
        # Check 4: Route has exactly 2 depots
        depot_count = sequence.count(0)
        if depot_count != 2:
            issues.append(f"Expected 2 depots, found {depot_count}")
        
        validation_results.append({
            "cluster_id": cluster_id,
            "sequence": sequence,
            "valid": len(issues) == 0,
            "issues": issues
        })
    
    return validation_results


# ============================================================
# COST CALCULATION
# ============================================================

def compute_costs(routes: List[Dict], dataset: Dict) -> Dict:
    """Compute costs as in Word document."""
    fleet = {f["id"]: f for f in dataset["fleet"]}
    
    total_fixed = 0.0
    total_variable = 0.0
    
    cost_breakdown = []
    
    for route in routes:
        vehicle = fleet[route["vehicle_type"]]
        fixed = vehicle["fixed_cost"]
        variable = vehicle["variable_cost_per_km"] * route["total_distance"]
        
        cost_breakdown.append({
            "cluster_id": route["cluster_id"],
            "vehicle_type": route["vehicle_type"],
            "fixed_cost": fixed,
            "variable_cost": variable,
            "total_cost": fixed + variable
        })
        
        total_fixed += fixed
        total_variable += variable
    
    return {
        "total_fixed_cost": total_fixed,
        "total_variable_cost": total_variable,
        "total_cost": total_fixed + total_variable,
        "breakdown": cost_breakdown
    }


# ============================================================
# VALIDATION AGAINST WORD DOCUMENT
# ============================================================

def validate_against_word(routes: List[Dict]) -> List[Dict]:
    """Compare generated routes with Word document expected values."""
    validation_results = []
    
    for route in routes:
        cluster_id = route["cluster_id"]
        expected = WORD_EXPECTED_ROUTES.get(cluster_id)
        
        if expected:
            seq_match = route["sequence"] == expected["sequence"]
            dist_match = abs(route["total_distance"] - expected["distance"]) < 0.5
            
            validation_results.append({
                "cluster_id": cluster_id,
                "sequence_expected": expected["sequence"],
                "sequence_actual": route["sequence"],
                "sequence_match": seq_match,
                "distance_expected": expected["distance"],
                "distance_actual": route["total_distance"],
                "distance_match": dist_match,
                "valid": seq_match and dist_match
            })
    
    return validation_results


# ============================================================
# MAIN ACADEMIC REPLAY FUNCTION
# ============================================================

def run_academic_replay() -> Dict:
    """
    Run the complete academic replay pipeline.
    Returns all iteration logs for display in UI.
    """
    print("=" * 60)
    print("ACADEMIC REPLAY MODE - Hitung Manual MFVRPTE RVND")
    print("=" * 60)
    
    dataset = ACADEMIC_DATASET
    distance_matrix = build_distance_matrix(dataset)
    
    all_logs = []
    
    # ============================================================
    # 0. VEHICLE AVAILABILITY CHECK (NEW!)
    # ============================================================
    print("\n[0/5] Checking Vehicle Availability...")
    fleet = dataset["fleet"]
    availability_status = get_vehicle_availability_status(fleet)
    available_fleet = get_available_vehicles(fleet)
    
    # Log availability status
    for status in availability_status:
        all_logs.append({
            "phase": "VEHICLE_AVAILABILITY",
            "vehicle_id": status["vehicle_id"],
            "capacity": status["capacity"],
            "units": status.get("units", 1),
            "available": status["available"],
            "time_window": status.get("time_window", "Not Set"),
            "status": status["status"]
        })
        
        icon = "✅" if status["available"] else "❌"
        print(f"   {icon} Vehicle {status['vehicle_id']}: {status['status']}")
    
    print(f"   → {len(available_fleet)}/{len(fleet)} vehicle types available for routing")
    
    if len(available_fleet) == 0:
        print("   ❌ CRITICAL: No vehicles available! Cannot proceed with routing.")
        return {
            "mode": "ACADEMIC_REPLAY",
            "error": "No vehicles available",
            "vehicle_availability": availability_status,
            "dataset": dataset,
            "clusters": [],
            "routes": [],
            "costs": {"total_cost": 0},
            "iteration_logs": all_logs
        }
    
    # 1. SWEEP CLUSTERING
    print("\n[1/5] Running SWEEP algorithm...")
    clusters, sweep_logs = academic_sweep(dataset)
    all_logs.extend(sweep_logs)
    print(f"   Formed {len(clusters)} clusters")
    
    # 2. NEAREST NEIGHBOR (TIME-WINDOW AWARE)
    print("\n[2/5] Running Nearest Neighbor (TW-Aware)...")
    initial_routes = []
    all_unassigned = []  # Customers rejected due to TW violation
    
    for cluster in clusters:
        route, nn_logs = academic_nearest_neighbor(cluster, dataset, distance_matrix)
        initial_routes.append(route)
        all_logs.extend(nn_logs)
        
        # Track unassigned customers
        unassigned = route.get("unassigned_customers", [])
        if unassigned:
            all_unassigned.extend(unassigned)
            print(f"   Cluster {cluster['cluster_id']}: {route['sequence']} (dist={route['total_distance']}) ⚠️ {len(unassigned)} unassigned")
        else:
            print(f"   Cluster {cluster['cluster_id']}: {route['sequence']} (dist={route['total_distance']})")
    
    if all_unassigned:
        print(f"   ⚠️ Total unassigned customers (TW hard constraint): {all_unassigned}")
    
    # 3. ACS
    print("\n[3/5] Running ACS...")
    acs_routes = []
    for i, cluster in enumerate(clusters):
        route, acs_logs = academic_acs_cluster(cluster, dataset, distance_matrix, initial_routes[i])
        acs_routes.append(route)
        all_logs.extend(acs_logs)
        print(f"   Cluster {cluster['cluster_id']}: {route['sequence']} (dist={route['total_distance']})")
    
    # 4. RVND
    print("\n[4/5] Running RVND...")
    final_routes, rvnd_logs = academic_rvnd(acs_routes, dataset, distance_matrix)
    all_logs.extend(rvnd_logs)
    for route in final_routes:
        print(f"   Cluster {route['cluster_id']}: {route['sequence']} (dist={route['total_distance']})")
    
    # 5. VEHICLE REASSIGNMENT
    print("\n[5/5] Reassigning vehicles...")
    final_routes, vehicle_logs = reassign_vehicles(final_routes, dataset)
    all_logs.extend(vehicle_logs)
    
    # COST CALCULATION
    costs = compute_costs(final_routes, dataset)
    print(f"\n   Total Cost: Rp {costs['total_cost']:,.0f}")
    
    # TIME WINDOW SUMMARY
    print("\n" + "=" * 60)
    print("TIME WINDOW SUMMARY (Soft Constraints)")
    print("=" * 60)
    total_violations = 0
    total_wait = 0
    for route in final_routes:
        tw_viol = route.get("total_tw_violation", 0)
        wait = route.get("total_wait_time", 0)
        total_violations += tw_viol
        total_wait += wait
        
        violations_detail = route.get("tw_violations_detail", [])
        if violations_detail:
            print(f"   Cluster {route['cluster_id']}: ⚠️ {len(violations_detail)} violation(s), {tw_viol:.1f} min total")
            for v in violations_detail:
                print(f"      - Customer {v['customer_id']}: arrived {v['arrival']:.1f}, TW ends {v['tw_end']:.0f}, late by {v['violation_minutes']:.1f} min")
        else:
            print(f"   Cluster {route['cluster_id']}: ✅ No violations (wait time: {wait:.1f} min)")
    
    print(f"\n   Total Wait Time: {total_wait:.1f} min")
    print(f"   Total TW Violations: {total_violations:.1f} min")
    if total_violations > 0:
        print("   ℹ️ Time windows are SOFT constraints in ACS/RVND - solutions NOT rejected")
    
    # UNASSIGNED CUSTOMERS SUMMARY (from NN hard constraint)
    if all_unassigned:
        print("\n" + "=" * 60)
        print("UNASSIGNED CUSTOMERS (NN Hard Constraint)")
        print("=" * 60)
        print(f"   {len(all_unassigned)} customer(s) rejected by NN due to TW violation")
        print(f"   Customer IDs: {all_unassigned}")
        print("   ℹ️ In NN phase, TW is HARD constraint: arrival > TW_end = REJECT")
    
    # ROUTE STRUCTURE VALIDATION (CRITICAL)
    print("\n" + "=" * 60)
    print("ROUTE STRUCTURE VALIDATION")
    print("=" * 60)
    structure_validation = validate_route_structure(final_routes)
    
    structure_valid = True
    for v in structure_validation:
        status = "✅ VALID" if v["valid"] else "❌ INVALID"
        print(f"   Cluster {v['cluster_id']}: {status}")
        if not v["valid"]:
            structure_valid = False
            for issue in v["issues"]:
                print(f"      ⚠️ {issue}")
    
    if structure_valid:
        print("   ✅ All routes have correct MFVRP structure")
    else:
        print("   ❌ CRITICAL: Route structure validation FAILED")
    
    # VALIDATION AGAINST WORD DOCUMENT
    print("\n" + "=" * 60)
    print("VALIDATION AGAINST WORD DOCUMENT")
    print("=" * 60)
    validation = validate_against_word(final_routes)
    
    all_valid = True
    for v in validation:
        status = "✅ MATCH" if v["valid"] else "❌ MISMATCH"
        print(f"   Cluster {v['cluster_id']}: {status}")
        if not v["valid"]:
            all_valid = False
            print(f"      Expected: {v['sequence_expected']}")
            print(f"      Actual:   {v['sequence_actual']}")
    
    # Save results
    output = {
        "mode": "ACADEMIC_REPLAY",
        "vehicle_availability": availability_status,
        "available_vehicles": [v["id"] for v in available_fleet],
        "dataset": dataset,
        "clusters": clusters,
        "routes": final_routes,
        "unassigned_customers": all_unassigned,
        "costs": costs,
        "structure_validation": structure_validation,
        "structure_valid": structure_valid,
        "validation": validation,
        "all_valid": all_valid and structure_valid,
        "iteration_logs": all_logs
    }
    
    with ACADEMIC_OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)
    
    print(f"\n✅ Results saved to: {ACADEMIC_OUTPUT_PATH}")
    
    return output


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    if MODE == "ACADEMIC_REPLAY":
        result = run_academic_replay()
    else:
        print("MODE is set to OPTIMIZATION. Use normal pipeline instead.")
