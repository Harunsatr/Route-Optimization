import json
import math
from pathlib import Path
from typing import Dict, List, Tuple

DATA_DIR = Path(__file__).resolve().parent / "data" / "processed"
INSTANCE_PATH = DATA_DIR / "parsed_instance.json"
DISTANCE_PATH = DATA_DIR / "parsed_distance.json"
CLUSTERS_PATH = DATA_DIR / "clusters.json"
INITIAL_ROUTES_PATH = DATA_DIR / "initial_routes.json"


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def parse_time_to_minutes(value: str) -> float:
    hours, minutes = value.split(":")
    return int(hours) * 60 + int(minutes)


def minutes_to_clock(value: float) -> str:
    hours = int(value // 60)
    minutes = int(value % 60)
    seconds = (value - math.floor(value)) * 60
    if seconds < 1e-6:
        return f"{hours:02d}:{minutes:02d}"
    return f"{hours:02d}:{minutes:02d}+{seconds:02.0f}s"


def compute_polar_angle(customer: dict, depot: dict) -> float:
    angle = math.atan2(customer["y"] - depot["y"], customer["x"] - depot["x"])
    if angle < 0:
        angle += 2 * math.pi
    return angle


def build_clusters(instance: dict) -> Tuple[List[dict], Dict[str, int]]:
    depot = instance["depot"]
    customers = instance["customers"]
    fleets = instance["fleet"]

    customer_angles = []
    for customer in customers:
        angle = compute_polar_angle(customer, depot)
        customer_angles.append({"customer": customer, "angle": angle})
    customer_angles.sort(key=lambda item: item["angle"])

    available_units = {fleet["id"]: fleet["units"] for fleet in fleets}
    fleet_by_id = {fleet["id"]: fleet for fleet in fleets}

    clusters = []
    cluster_id = 1
    current_customers: List[dict] = []
    current_demand = 0
    current_vehicle = None

    for entry in customer_angles:
        customer = entry["customer"]
        added = False
        while not added:
            proposed_demand = current_demand + customer["demand"]
            feasible_fleets = [
                fleet for fleet in fleets
                if available_units[fleet["id"]] > 0 and fleet["capacity"] >= proposed_demand
            ]
            if feasible_fleets:
                chosen = min(feasible_fleets, key=lambda f: f["capacity"])
                current_customers.append(customer)
                current_demand = proposed_demand
                current_vehicle = chosen
                added = True
            else:
                if not current_customers:
                    raise RuntimeError("No available vehicle can serve customer demand")
                clusters.append({
                    "cluster_id": cluster_id,
                    "vehicle_type": current_vehicle["id"],
                    "customer_ids": [cust["id"] for cust in current_customers],
                    "total_demand": current_demand
                })
                available_units[current_vehicle["id"]] -= 1
                cluster_id += 1
                current_customers = []
                current_demand = 0
                current_vehicle = None
    if current_customers:
        clusters.append({
            "cluster_id": cluster_id,
            "vehicle_type": current_vehicle["id"],
            "customer_ids": [cust["id"] for cust in current_customers],
            "total_demand": current_demand
        })
        available_units[current_vehicle["id"]] -= 1

    used_units = {fleet_id: fleet["units"] - available_units[fleet_id] for fleet_id, fleet in zip(available_units.keys(), fleets)}
    # Correct used units calculation to ensure mapping by ID
    used_units = {fleet_id: instance_fleet["units"] - available_units[fleet_id] for fleet_id, instance_fleet in {fleet["id"]: fleet for fleet in fleets}.items()}

    return clusters, used_units


def nearest_neighbor_route(cluster: dict, instance: dict, distance_data: dict) -> dict:
    node_index = {node["id"]: idx for idx, node in enumerate(distance_data["nodes"])}
    distance_matrix = distance_data["distance_matrix"]
    travel_matrix = distance_data["travel_time_matrix"]

    depot = instance["depot"]
    depot_tw = {
        "start": parse_time_to_minutes(depot["time_window"]["start"]),
        "end": parse_time_to_minutes(depot["time_window"]["end"])
    }
    depot_service = depot.get("service_time", 0)

    customers = {customer["id"]: customer for customer in instance["customers"]}

    unvisited = set(cluster["customer_ids"])
    route_sequence = [0]
    current_node = 0
    while unvisited:
        next_node = min(
            unvisited,
            key=lambda cid: (distance_matrix[node_index[current_node]][node_index[cid]], cid)
        )
        route_sequence.append(next_node)
        unvisited.remove(next_node)
        current_node = next_node
    route_sequence.append(0)

    stops = []
    total_violation = 0.0
    total_distance = 0.0

    prev_node = 0
    prev_departure = depot_tw["start"] + depot_service

    stops.append({
        "node_id": 0,
        "arrival": depot_tw["start"],
        "arrival_str": minutes_to_clock(depot_tw["start"]),
        "departure": prev_departure,
        "departure_str": minutes_to_clock(prev_departure),
        "wait": 0.0,
        "violation": max(0.0, depot_tw["start"] - depot_tw["end"])
    })

    for next_node in route_sequence[1:]:
        travel = travel_matrix[node_index[prev_node]][node_index[next_node]]
        total_distance += distance_matrix[node_index[prev_node]][node_index[next_node]]
        arrival_no_wait = prev_departure + travel

        if next_node == 0:
            tw_start = depot_tw["start"]
            tw_end = depot_tw["end"]
            service_time = depot_service
        else:
            customer = customers[next_node]
            tw_start = parse_time_to_minutes(customer["time_window"]["start"])
            tw_end = parse_time_to_minutes(customer["time_window"]["end"])
            service_time = customer["service_time"]

        arrival = max(tw_start, arrival_no_wait)
        wait_time = max(0.0, tw_start - arrival_no_wait)
        violation = max(0.0, arrival - tw_end)
        departure = arrival + service_time

        if next_node != 0:
            total_violation += violation

        stops.append({
            "node_id": next_node,
            "arrival": arrival,
            "arrival_str": minutes_to_clock(arrival),
            "departure": departure,
            "departure_str": minutes_to_clock(departure),
            "wait": wait_time,
            "violation": violation
        })

        prev_node = next_node
        prev_departure = departure

    return {
        "cluster_id": cluster["cluster_id"],
        "vehicle_type": cluster["vehicle_type"],
        "sequence": route_sequence,
        "stops": stops,
        "total_distance": total_distance,
        "total_tw_violation": total_violation
    }


def save_clusters(clusters: List[dict], fleet_usage: Dict[str, int]) -> None:
    payload = {
        "total_clusters": len(clusters),
        "clusters": clusters,
        "fleet_usage": fleet_usage
    }
    with CLUSTERS_PATH.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def save_initial_routes(routes: List[dict]) -> None:
    payload = {
        "routes": routes,
        "units": {"time": "minutes", "distance": "km"}
    }
    with INITIAL_ROUTES_PATH.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def main() -> None:
    print("PROGRESS:sweep_nn:0:starting sweep_nn")
    instance = load_json(INSTANCE_PATH)
    distance_data = load_json(DISTANCE_PATH)
    print("PROGRESS:sweep_nn:20:loaded inputs")

    clusters, fleet_usage = build_clusters(instance)
    print(f"PROGRESS:sweep_nn:50:built {len(clusters)} clusters")

    routes = [nearest_neighbor_route(cluster, instance, distance_data) for cluster in clusters]
    print("PROGRESS:sweep_nn:80:constructed initial routes")

    save_clusters(clusters, fleet_usage)
    save_initial_routes(routes)
    print("PROGRESS:sweep_nn:100:done")

    total_demand = sum(cluster["total_demand"] for cluster in clusters)
    violations = sum(route["total_tw_violation"] for route in routes)
    print(
        "sweep_nn: clusters=", len(clusters),
        ", fleet_usage=", fleet_usage,
        ", total_demand=", total_demand,
        ", tw_violation=", round(violations, 2),
        sep=""
    )


if __name__ == "__main__":
    main()
