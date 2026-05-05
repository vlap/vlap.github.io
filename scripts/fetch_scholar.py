from scholarly import scholarly
import yaml
import os

SCHOLAR_ID = "ZVQF-ggAAAAJ" # From your Google Scholar URL
OUTPUT_FILE = "data/scholar_stats.yaml"

def fetch_scholar_stats(scholar_id):
    print(f"Fetching Google Scholar stats for ID: {scholar_id}...")
    try:
        author = scholarly.search_author_id(scholar_id)
        author = scholarly.fill(author, sections=['indices'])
        
        stats = {
            'citations': author.get('citedby', 0),
            'h_index': author.get('hindex', 0),
            'i10_index': author.get('i10index', 0),
            'last_updated': str(os.popen('date -I').read().strip())
        }
        return stats
    except Exception as e:
        print(f"Error fetching from Google Scholar: {e}")
        return None

def main():
    stats = fetch_scholar_stats(SCHOLAR_ID)
    if stats:
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        with open(OUTPUT_FILE, 'w') as f:
            yaml.dump(stats, f, sort_keys=False)
        print(f"Successfully saved scholar stats to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
