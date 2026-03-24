import json


def load_processed():
    try:
        with open("data/processed.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []


def save_processed(timestamp):
    processed = load_processed()
    processed.append(timestamp)
    with open("data/processed.json", "w") as f:
        json.dump(processed, f, indent=4)


def get_most_recent_timestamp():
    processed = load_processed()
    if not processed:
        return None
    return max(item for item in processed)
