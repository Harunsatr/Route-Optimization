import json
from pathlib import Path
from typing import Dict, List, Tuple

DATA_DIR = Path(__file__).resolve().parent / "data" / "processed"
INSTANCE_PATH = DATA_DIR / "parsed_instance.json"
DISTANCE_PATH = DATA_DIR / "parsed_distance.json"
CLUSTERS_PATH = DATA_DIR / "clusters.json"
INITIAL_ROUTES_PATH = DATA_DIR / "initial_routes.json"
ACS_PATH = DATA_DIR / "acs_routes.json"
RVND_PATH = DATA_DIR / "rvnd_routes.json"
FINAL_SOLUTION_PATH = DATA_DIR / "final_solution.json"

SUMMARY_PATH = Path(__file__).resolve().parent / "docs" / "final_summary.md"


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def aggregate_costs(instance: dict, routes: List[dict]) -> Tuple[float, Dict[str, int]]:
    fleet_data = {fleet["id"]: fleet for fleet in instance["fleet"]}
    usage_counts = {fleet_id: 0 for fleet_id in fleet_data}

    total_fixed = 0.0
    total_variable = 0.0

    for route in routes:
        vehicle_type = route["vehicle_type"]
        fleet = fleet_data[vehicle_type]
        usage_counts[vehicle_type] += 1
        total_fixed += fleet["fixed_cost"]
        total_variable += fleet["variable_cost_per_km"] * route["total_distance"]

    return total_fixed + total_variable, usage_counts


def validate_solution(instance: dict, distance_data: dict, clusters_data: dict, final_routes: List[dict]) -> Dict[str, bool]:
    node_count_instance = 1 + len(instance["customers"])
    node_count_distance = len(distance_data["nodes"])
    nodes_match = node_count_instance == node_count_distance

    symmetric = True
    zero_diagonal = True
    matrix = distance_data["distance_matrix"]
    for i in range(len(matrix)):
        if abs(matrix[i][i]) > 1e-9:
            zero_diagonal = False
            break
        for j in range(i + 1, len(matrix)):
            if abs(matrix[i][j] - matrix[j][i]) > 1e-9:
                symmetric = False
                break
        if not symmetric:
            break

    capacity_ok = True
    fleet_capacities = {fleet["id"]: fleet["capacity"] for fleet in instance["fleet"]}
    customer_demand = {customer["id"]: customer["demand"] for customer in instance["customers"]}
    for cluster in clusters_data["clusters"]:
        total = sum(customer_demand[cid] for cid in cluster["customer_ids"])
        if total > fleet_capacities[cluster["vehicle_type"]] + 1e-9:
            capacity_ok = False
            break

    tw_consistent = all(abs(route["total_tw_violation"]) < 1e-9 for route in final_routes)

    return {
        "nodes_match": nodes_match,
        "distance_symmetric": symmetric,
        "distance_zero_diagonal": zero_diagonal,
        "capacity_respected": capacity_ok,
        "tw_no_violation": tw_consistent
    }


def main() -> None:
    print("PROGRESS:final_integration:0:starting final_integration")
    instance = load_json(INSTANCE_PATH)
    distance_data = load_json(DISTANCE_PATH)
    clusters_data = load_json(CLUSTERS_PATH)
    initial_routes_data = load_json(INITIAL_ROUTES_PATH)
    acs_data = load_json(ACS_PATH)
    rvnd_data = load_json(RVND_PATH)
    print("PROGRESS:final_integration:20:loaded inputs")

    final_routes = []
    total_distance = 0.0
    total_time_component = 0.0
    total_violation = 0.0
    total_objective = 0.0

    rvnd_map = {entry["cluster_id"]: entry for entry in rvnd_data["routes"]}
    acs_map = {entry["cluster_id"]: entry for entry in acs_data["clusters"]}

    for idx, cluster in enumerate(clusters_data["clusters"]):
        cid = cluster["cluster_id"]
        rvnd_entry = rvnd_map[cid]
        improved = rvnd_entry["improved"]
        route_summary = {
            "cluster_id": cid,
            "vehicle_type": cluster["vehicle_type"],
            "sequence": improved["sequence"],
            "stops": improved["stops"],
            "total_distance": improved["total_distance"],
            "total_travel_time": improved["total_travel_time"],
            "total_service_time": improved["total_service_time"],
            "total_time_component": improved["total_time_component"],
            "total_tw_violation": improved["total_tw_violation"],
            "objective": improved["objective"],
            "initial_sequence": initial_routes_data["routes"][cid - 1]["sequence"],
            "acs_sequence": acs_map[cid]["sequence"],
            "rvnd_sequence": improved["sequence"]
        }
        final_routes.append(route_summary)
        total_distance += improved["total_distance"]
        total_time_component += improved["total_time_component"]
        total_violation += improved["total_tw_violation"]
        total_objective += improved["objective"]
        try:
            pct = 20 + int((idx + 1) / max(1, len(clusters_data.get("clusters", []))) * 70)
            print(f"PROGRESS:final_integration:{pct}:processed cluster {idx+1}")
        except Exception:
            pass

    total_cost, fleet_usage = aggregate_costs(instance, final_routes)
    validations = validate_solution(instance, distance_data, clusters_data, final_routes)

    final_payload = {
        "summary": {
            "total_distance": total_distance,
            "total_time_component": total_time_component,
            "total_tw_violation": total_violation,
            "total_objective": total_objective,
            "total_cost": total_cost,
            "fleet_usage": fleet_usage
        },
        "routes": final_routes,
        "validations": validations,
        "seeds": {
            "acs": 42,
            "rvnd": 84
        }
    }

    with FINAL_SOLUTION_PATH.open("w", encoding="utf-8") as handle:
        json.dump(final_payload, handle, indent=2)

    with SUMMARY_PATH.open("w", encoding="utf-8") as handle:
        handle.write("# MFVRPTW Final Summary\n\n")
        handle.write("- Total distance: {:.3f} km\n".format(total_distance))
        handle.write("- Total time component: {:.3f} minutes\n".format(total_time_component))
        handle.write("- Total TW violation: {:.3f} minutes\n".format(total_violation))
        handle.write("- Total objective: {:.3f}\n".format(total_objective))
        handle.write("- Total cost: Rp {:.0f}\n".format(total_cost))
        handle.write("- Fleet usage: {}\n\n".format(fleet_usage))
        handle.write("## Validations\n")
        for key, value in validations.items():
            handle.write(f"- {key}: {'PASS' if value else 'FAIL'}\n")

    print("PROGRESS:final_integration:100:done")
    print(
        "final_integration: distance=", round(total_distance, 3),
        ", time_component=", round(total_time_component, 3),
        ", objective=", round(total_objective, 3),
        ", cost=", round(total_cost, 2),
        sep=""
    )


if __name__ == "__main__":
    main()
