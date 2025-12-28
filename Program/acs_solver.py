import json
import math
import random
from pathlib import Path
from typing import Dict, List, Tuple

DATA_DIR = Path(__file__).resolve().parent / "data" / "processed"
INSTANCE_PATH = DATA_DIR / "parsed_instance.json"
DISTANCE_PATH = DATA_DIR / "parsed_distance.json"
CLUSTERS_PATH = DATA_DIR / "clusters.json"
INITIAL_ROUTES_PATH = DATA_DIR / "initial_routes.json"
ACS_RESULTS_PATH = DATA_DIR / "acs_routes.json"


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def parse_time_to_minutes(value: str) -> float:
    hours, minutes = value.split(":")
    return int(hours) * 60 + int(minutes)


def minutes_to_clock(value: float) -> str:
    hours = int(value // 60)
    minutes = int(value % 60)
    seconds = round((value - math.floor(value)) * 60)
    if seconds == 0:
        return f"{hours:02d}:{minutes:02d}"
    return f"{hours:02d}:{minutes:02d}+{seconds:02d}s"


def evaluate_route(sequence: List[int], instance: dict, distance_data: dict) -> dict:
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

    stops = []
    total_distance = 0.0
    total_travel_time = 0.0
    total_service_time = 0.0
    total_violation = 0.0

    prev_node = sequence[0]
    current_time = depot_tw["start"] + depot_service

    stops.append({
        "node_id": 0,
        "arrival": depot_tw["start"],
        "arrival_str": minutes_to_clock(depot_tw["start"]),
        "departure": current_time,
        "departure_str": minutes_to_clock(current_time),
        "wait": 0.0,
        "violation": 0.0
    })

    for next_node in sequence[1:]:
        travel_time = travel_matrix[node_index[prev_node]][node_index[next_node]]
        distance = distance_matrix[node_index[prev_node]][node_index[next_node]]
        total_distance += distance
        total_travel_time += travel_time

        arrival_no_wait = current_time + travel_time

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
            total_service_time += service_time
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
        current_time = departure

    total_time_component = total_travel_time + total_service_time
    objective_value = total_distance + total_time_component + total_violation

    return {
        "sequence": sequence,
        "stops": stops,
        "total_distance": total_distance,
        "total_travel_time": total_travel_time,
        "total_service_time": total_service_time,
        "total_time_component": total_time_component,
        "total_tw_violation": total_violation,
        "objective": objective_value
    }


def initialize_pheromone(customers: List[int], initial_length: float) -> Dict[Tuple[int, int], float]:
    tau0 = 1.0 / (max(1, len(customers)) * max(initial_length, 1e-6))
    nodes = [0] + customers
    pheromone = {}
    for i in nodes:
        for j in nodes:
            if i == j:
                continue
            pheromone[(i, j)] = tau0
    return pheromone, tau0


def select_next_node(prev_node: int, allowed: List[int], pheromone: Dict[Tuple[int, int], float],
                     distance_matrix: List[List[float]], node_index: Dict[int, int],
                     alpha: float, beta: float, q0: float, rng: random.Random) -> int:
    desirabilities = []
    for candidate in allowed:
        pher = pheromone[(prev_node, candidate)]
        dist = distance_matrix[node_index[prev_node]][node_index[candidate]]
        visibility = 1.0 / dist if dist > 0 else 0.0
        value = (pher ** alpha) * (visibility ** beta) if visibility > 0 else 0.0
        desirabilities.append((candidate, value))

    if not desirabilities:
        raise RuntimeError("No candidates available for selection")

    q = rng.random()
    if q <= q0:
        candidate = max(desirabilities, key=lambda item: (item[1], -item[0]))[0]
        return candidate

    total = sum(value for _, value in desirabilities)
    if total <= 0:
        return rng.choice([candidate for candidate, _ in desirabilities])

    threshold = rng.random() * total
    cumulative = 0.0
    for candidate, value in desirabilities:
        cumulative += value
        if threshold <= cumulative:
            return candidate
    return desirabilities[-1][0]


def local_update(pheromone: Dict[Tuple[int, int], float], edge: Tuple[int, int], rho: float, tau0: float) -> None:
    i, j = edge
    updated = (1 - rho) * pheromone[(i, j)] + rho * tau0
    pheromone[(i, j)] = updated
    pheromone[(j, i)] = updated


def global_update(pheromone: Dict[Tuple[int, int], float], best_sequence: List[int], rho: float, best_distance: float) -> None:
    edges_in_best = set(zip(best_sequence[:-1], best_sequence[1:]))
    contribution = rho * (1.0 / max(best_distance, 1e-6))
    for (i, j), value in list(pheromone.items()):
        base = (1 - rho) * value
        if (i, j) in edges_in_best:
            pheromone[(i, j)] = base + contribution
        else:
            pheromone[(i, j)] = base
    # ensure symmetry
    for (i, j) in list(pheromone.keys()):
        pheromone[(j, i)] = pheromone[(i, j)]


def acs_cluster(cluster: dict, instance: dict, distance_data: dict, initial_route: dict,
                acs_params: dict, rng: random.Random) -> dict:
    customers = cluster["customer_ids"]
    node_index = {node["id"]: idx for idx, node in enumerate(distance_data["nodes"])}
    distance_matrix = distance_data["distance_matrix"]

    initial_length = initial_route["total_distance"]
    pheromone, tau0 = initialize_pheromone(customers, initial_length)

    alpha = acs_params["alpha"]
    beta = acs_params["beta"]
    rho = acs_params["rho"]
    q0 = acs_params["q0"]
    num_ants = acs_params["num_ants"]
    max_iterations = acs_params["max_iterations"]

    best_metrics = evaluate_route(initial_route["sequence"], instance, distance_data)
    best_sequence = best_metrics["sequence"]

    for iteration in range(1, max_iterations + 1):
        iteration_best_sequence = None
        iteration_best_metrics = None

        for _ in range(num_ants):
            route = [0]
            allowed = set(customers)
            prev = 0
            while allowed:
                selected_node = select_next_node(prev, list(allowed), pheromone,
                                                 distance_matrix, node_index,
                                                 alpha, beta, q0, rng)
                route.append(selected_node)
                allowed.remove(selected_node)
                local_update(pheromone, (prev, selected_node), rho, tau0)
                prev = selected_node
            route.append(0)
            local_update(pheromone, (prev, 0), rho, tau0)

            metrics = evaluate_route(route, instance, distance_data)
            if iteration_best_metrics is None or metrics["objective"] < iteration_best_metrics["objective"]:
                iteration_best_metrics = metrics
                iteration_best_sequence = route

        global_update(pheromone, iteration_best_sequence, rho, iteration_best_metrics["total_distance"])

        if iteration_best_metrics["objective"] < best_metrics["objective"]:
            best_metrics = iteration_best_metrics
            best_sequence = iteration_best_sequence

    best_metrics["cluster_id"] = cluster["cluster_id"]
    best_metrics["vehicle_type"] = cluster["vehicle_type"]
    best_metrics["tau0"] = tau0
    best_metrics["iterations"] = max_iterations

    return best_metrics


def main() -> None:
    print("PROGRESS:acs_solver:0:starting acs_solver")
    instance = load_json(INSTANCE_PATH)
    distance_data = load_json(DISTANCE_PATH)
    clusters_data = load_json(CLUSTERS_PATH)
    initial_routes_data = load_json(INITIAL_ROUTES_PATH)
    print("PROGRESS:acs_solver:20:loaded inputs")
    acs_params = instance["acs_parameters"]

    rng = random.Random(42)

    initial_route_map = {route["cluster_id"]: route for route in initial_routes_data["routes"]}

    results = []
    total_violation = 0.0
    total_distance = 0.0

    total_clusters = len(clusters_data.get("clusters", []))
    for idx, cluster in enumerate(clusters_data["clusters"]):
        cluster_id = cluster["cluster_id"]
        metrics = acs_cluster(cluster, instance, distance_data, initial_route_map[cluster_id], acs_params, rng)
        results.append(metrics)
        total_violation += metrics["total_tw_violation"]
        total_distance += metrics["total_distance"]
        try:
            pct = 20 + int((idx + 1) / max(1, total_clusters) * 70)
            print(f"PROGRESS:acs_solver:{pct}:processed cluster {idx+1}/{total_clusters}")
        except Exception:
            pass

    output = {
        "clusters": results,
        "summary": {
            "total_distance": total_distance,
            "total_tw_violation": total_violation,
            "objective_sum": sum(route["objective"] for route in results)
        },
        "parameters": instance["acs_parameters"],
        "random_seed": 42
    }

    with ACS_RESULTS_PATH.open("w", encoding="utf-8") as handle:
        json.dump(output, handle, indent=2)
    print("PROGRESS:acs_solver:100:done")

    print(
        "acs_solver: clusters=", len(results),
        ", total_distance=", round(total_distance, 3),
        ", total_tw_violation=", round(total_violation, 3),
        sep=""
    )


if __name__ == "__main__":
    main()
