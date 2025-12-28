import json
import math
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data" / "processed"
INSTANCE_PATH = DATA_DIR / "parsed_instance.json"
DISTANCE_PATH = DATA_DIR / "parsed_distance.json"


def load_instance(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def extract_nodes(instance: dict) -> list:
    nodes = []
    depot = instance["depot"]
    nodes.append({
        "id": depot["id"],
        "name": depot["name"],
        "x": float(depot["x"]),
        "y": float(depot["y"])
    })
    for customer in instance["customers"]:
        nodes.append({
            "id": customer["id"],
            "name": customer["name"],
            "x": float(customer["x"]),
            "y": float(customer["y"])
        })
    return nodes


def euclidean_distance(node_a: dict, node_b: dict) -> float:
    dx = node_a["x"] - node_b["x"]
    dy = node_a["y"] - node_b["y"]
    return math.hypot(dx, dy)


def compute_distance_matrix(nodes: list) -> list:
    size = len(nodes)
    matrix = [[0.0 for _ in range(size)] for _ in range(size)]
    for i in range(size):
        for j in range(i + 1, size):
            distance = euclidean_distance(nodes[i], nodes[j])
            matrix[i][j] = distance
            matrix[j][i] = distance
    return matrix


def compute_travel_time_matrix(distance_matrix: list) -> list:
    return [row[:] for row in distance_matrix]


def save_distance_data(nodes: list, distance_matrix: list, travel_matrix: list, path: Path) -> None:
    payload = {
        "nodes": [
            {"id": node["id"], "name": node["name"]}
            for node in nodes
        ],
        "distance_matrix": distance_matrix,
        "travel_time_matrix": travel_matrix,
        "units": {"distance": "km", "time": "minutes"}
    }
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def main() -> None:
    print("PROGRESS:distance_time:0:starting distance_time")
    instance = load_instance(INSTANCE_PATH)
    print("PROGRESS:distance_time:20:loaded instance")
    nodes = extract_nodes(instance)
    print(f"PROGRESS:distance_time:40:extracted {len(nodes)} nodes")
    distance_matrix = compute_distance_matrix(nodes)
    travel_matrix = compute_travel_time_matrix(distance_matrix)
    print("PROGRESS:distance_time:80:computed matrices")
    save_distance_data(nodes, distance_matrix, travel_matrix, DISTANCE_PATH)
    print("PROGRESS:distance_time:100:done")
    print(f"distance_time: nodes={len(nodes)}, matrix={len(distance_matrix)}x{len(distance_matrix)}")


if __name__ == "__main__":
    main()
