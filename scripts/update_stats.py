import yaml
import os

DATA_DIR = "data"
OUTPUT_FILE = os.path.join(DATA_DIR, "stats.yaml")

def count_items(filename):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return 0
    with open(path, 'r') as f:
        data = yaml.safe_load(f)
        return len(data) if data else 0

def main():
    stats = {
        'publications': count_items("publications.yaml"),
        'software': count_items("curated_software.yaml"),
        'presentations': count_items("presentations.yaml"),
        'trainings': count_items("trainings.yaml")
    }
    
    with open(OUTPUT_FILE, 'w') as f:
        yaml.dump(stats, f, sort_keys=False)
    
    print(f"Updated stats: {stats}")

if __name__ == "__main__":
    main()
