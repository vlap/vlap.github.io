import requests
import yaml
import os

GITHUB_USER = "vlap"
OUTPUT_FILE = "data/github_activity.yaml"
GH_TOKEN = os.getenv('GH_TOKEN')

def fetch_repos(username):
    print(f"Fetching GitHub activity for {username}...")
    url = f"https://api.github.com/users/{username}/repos"
    params = {
        "sort": "updated",
        "per_page": 10
    }
    headers = {"Accept": "application/vnd.github.v3+json"}
    if GH_TOKEN:
        headers["Authorization"] = f"token {GH_TOKEN}"
        
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()

def main():
    try:
        repos = fetch_repos(GITHUB_USER)
        activity = []
        
        for repo in repos:
            # Skip forks if you only want your own work
            if repo.get('fork'):
                continue
                
            activity.append({
                'name': repo.get('name'),
                'description': repo.get('description'),
                'url': repo.get('html_url'),
                'stars': repo.get('stargazers_count'),
                'language': repo.get('language'),
                'updated': repo.get('updated_at')
            })
            
            if len(activity) >= 5:
                break
                
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        with open(OUTPUT_FILE, 'w') as f:
            yaml.dump(activity, f, sort_keys=False)
            
        print(f"Successfully saved GitHub activity to {OUTPUT_FILE}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
