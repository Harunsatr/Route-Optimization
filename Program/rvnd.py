import json
import math
import random
from copy import deepcopy
from pathlib import Path
from typing import Dict, List, Tuple

DATA_DIR = Path(__file__).resolve().parent / "data" / "processed"
INSTANCE_PATH = DATA_DIR / "parsed_instance.json"
DISTANCE_PATH = DATA_DIR / "parsed_distance.json"
ACS_PATH = DATA_DIR / "acs_routes.json"
RVND_PATH = DATA_DIR / "rvnd_routes.json"

NEIGHBORHOODS = ["two_opt", "swap", "relocate"]


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


def evaluate_route(sequence: List[int], instance: dict, distance_data: dict) -> Dict[str, float]:
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
    travel_time_sum = 0.0
    service_time_sum = 0.0
    violation_sum = 0.0

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
        travel = travel_matrix[node_index[prev_node]][node_index[next_node]]
        distance = distance_matrix[node_index[prev_node]][node_index[next_node]]
        total_distance += distance
        travel_time_sum += travel

        arrival_no_wait = current_time + travel

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
        wait = max(0.0, tw_start - arrival_no_wait)
        violation = max(0.0, arrival - tw_end)
        departure = arrival + service_time

        if next_node != 0:
            service_time_sum += service_time
            violation_sum += violation

        stops.append({
            "node_id": next_node,
            "arrival": arrival,
            "arrival_str": minutes_to_clock(arrival),
            "departure": departure,
            "departure_str": minutes_to_clock(departure),
            "wait": wait,
            "violation": violation
        })

        prev_node = next_node
        current_time = departure

    time_component = travel_time_sum + service_time_sum
    objective = total_distance + time_component + violation_sum

    return {
        "sequence": sequence,
        "stops": stops,
        "total_distance": total_distance,
        "total_travel_time": travel_time_sum,
        "total_service_time": service_time_sum,
        "total_time_component": time_component,
        "total_tw_violation": violation_sum,
        "objective": objective
    }


def two_opt(sequence: List[int]) -> List[Tuple[int, int]]:
    moves = []
    for i in range(1, len(sequence) - 2):
        for j in range(i + 1, len(sequence) - 1):
            moves.append((i, j))
    return moves


def apply_two_opt(sequence: List[int], i: int, j: int) -> List[int]:
    return sequence[:i] + list(reversed(sequence[i:j + 1])) + sequence[j + 1:]


def swap_moves(sequence: List[int]) -> List[Tuple[int, int]]:
    moves = []
    for i in range(1, len(sequence) - 2):
        for j in range(i + 1, len(sequence) - 1):
            moves.append((i, j))
    return moves


def apply_swap(sequence: List[int], i: int, j: int) -> List[int]:
    new_sequence = sequence[:]
    new_sequence[i], new_sequence[j] = new_sequence[j], new_sequence[i]
    return new_sequence


def relocate_moves(sequence: List[int]) -> List[Tuple[int, int]]:
    moves = []
    for i in range(1, len(sequence) - 1):
        for j in range(1, len(sequence)):
            if j == i or j == i + 1:
                continue
            moves.append((i, j))
    return moves


def apply_relocate(sequence: List[int], i: int, j: int) -> List[int]:
    new_sequence = sequence[:]
    node = new_sequence.pop(i)
    if j > i:
        new_sequence.insert(j - 1, node)
    else:
        new_sequence.insert(j, node)
    return new_sequence


def rvnd_route(route: Dict, instance: Dict, distance_data: Dict, rng: random.Random) -> Dict:
    """Apply RVND to improve route."""
    sequence = deepcopy(route["sequence"])
    
    # Get baseline
    baseline = evaluate_route(sequence, instance, distance_data)
    best_solution = sequence[:]
    best_distance = baseline["total_distance"]
    
    improved = True
    iterations = 0
    max_iterations = 100
    
    while improved and iterations < max_iterations:
        improved = False
        iterations += 1
        
        for neighborhood_func in [two_opt, swap_moves, relocate_moves]:
            for move in neighborhood_func(best_solution):
                if neighborhood_func == two_opt:
                    new_solution = apply_two_opt(best_solution, move[0], move[1])
                elif neighborhood_func == swap_moves:
                    new_solution = apply_swap(best_solution, move[0], move[1])
                else:
                    new_solution = apply_relocate(best_solution, move[0], move[1])
                
                new_metrics = evaluate_route(new_solution, instance, distance_data)
                if new_metrics["total_distance"] < best_distance:
                    best_solution = new_solution
                    best_distance = new_metrics["total_distance"]
                    improved = True
                    break
            
            if improved:
                break
    
    final_metrics = evaluate_route(best_solution, instance, distance_data)
    return final_metrics


def main() -> None:
    instance = load_json(INSTANCE_PATH)
    distance_data = load_json(DISTANCE_PATH)
    acs_data = load_json(ACS_PATH)

    rng = random.Random(84)

    results = []
    summary = {
        "distance_before": 0.0,
        "distance_after": 0.0,
        "objective_before": 0.0,
        "objective_after": 0.0,
        "tw_before": 0.0,
        "tw_after": 0.0
    }

    for route in acs_data["clusters"]:
        baseline = evaluate_route(route["sequence"], instance, distance_data)
        improved = rvnd_route(route, instance, distance_data, rng)

        summary["distance_before"] += baseline["total_distance"]
        summary["distance_after"] += improved["total_distance"]
        summary["objective_before"] += baseline["objective"]
        summary["objective_after"] += improved["objective"]
        summary["tw_before"] += baseline["total_tw_violation"]
        summary["tw_after"] += improved["total_tw_violation"]

        results.append({
            "cluster_id": route["cluster_id"],
            "vehicle_type": route["vehicle_type"],
            "baseline": baseline,
            "improved": improved
        })

    output = {
        "routes": results,
        "summary": summary,
        "parameters": {
            "neighborhoods": NEIGHBORHOODS,
            "seed": 84
        }
    }

    with RVND_PATH.open("w", encoding="utf-8") as handle:
        json.dump(output, handle, indent=2)

    print(
        "rvnd: distance_before=", round(summary["distance_before"], 3),
        ", distance_after=", round(summary["distance_after"], 3),
        ", objective_before=", round(summary["objective_before"], 3),
        ", objective_after=", round(summary["objective_after"], 3),
        sep=""
    )


if __name__ == "__main__":
    main()
