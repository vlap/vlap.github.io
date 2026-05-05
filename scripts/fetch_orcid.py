import requests
import yaml
import os
import re
from datetime import datetime

ORCID_ID = "0000-0001-7302-8539"
OUTPUT_FILE = "data/publications.yaml"
POSTS_DIR = "content/posts"

def slugify(text):
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    return re.sub(r'[-\s]+', '-', text).strip('-')

def create_micro_post(work):
    title = work.get('title', 'New Publication')
    date_str = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+02:00")
    filename = f"{datetime.now().strftime('%Y-%m-%d')}-{slugify(title)[:50]}.md"
    filepath = os.path.join(POSTS_DIR, filename)
    
    if os.path.exists(filepath):
        return

    content = f"""---
title: "New Publication: {title}"
date: {date_str}
draft: false
type: "posts"
layout: "micro"
tags: ["Research", "Publication"]
---

I am pleased to share a new publication: **{title}**. 

Published in *{work.get('journal', 'Unknown Journal')}* ({work.get('year', '')}).
"""
    if work.get('url'):
        content += f"\nFull paper available here: [{work.get('url')}]({work.get('url')})\n"

    with open(filepath, 'w') as f:
        f.write(content)
    print(f"  [News] Created micro-post: {filename}")

def fetch_orcid_works(orcid_id):
    print(f"Fetching works for ORCID: {orcid_id}...")
    url = f"https://pub.orcid.org/v3.0/{orcid_id}/works"
    headers = {"Accept": "application/json"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def parse_summary(summary):
    if not summary:
        return None
    try:
        title_obj = summary.get('title')
        title = "Unknown Title"
        if title_obj:
            title_val = title_obj.get('title')
            if title_val:
                title = title_val.get('value', 'Unknown Title')
        
        # Get Year
        pub_date = summary.get('publication-date')
        year = 'Unknown Year'
        if pub_date:
            year_obj = pub_date.get('year')
            if year_obj:
                year = year_obj.get('value', 'Unknown Year')
        
        # Get Journal/Source
        journal = summary.get('journal-title')
        if journal:
            journal = journal.get('value')
        
        if not journal:
            source = summary.get('source')
            if source:
                source_name = source.get('source-name')
                if source_name:
                    journal = source_name.get('value', 'Unknown Source')
            if not journal:
                journal = 'Unknown Source'
            
        # Get DOI
        doi = None
        external_ids_obj = summary.get('external-ids')
        if external_ids_obj:
            external_ids = external_ids_obj.get('external-id', [])
            for ext_id in external_ids:
                if ext_id.get('external-id-type') == 'doi':
                    doi = ext_id.get('external-id-value')
                    break
                
        return {
            'title': title,
            'year': str(year),
            'journal': journal,
            'doi': doi,
            'url': f"https://doi.org/{doi}" if doi else None
        }
    except Exception as e:
        print(f"Error parsing summary: {e}")
        return None

def main():
    try:
        # 1. Load existing publications to find "new" ones
        existing_keys = set()
        if os.path.exists(OUTPUT_FILE):
            with open(OUTPUT_FILE, 'r') as f:
                old_data = yaml.safe_load(f)
                if old_data:
                    # Use DOI if available, else title
                    existing_keys = {d.get('doi') or d.get('title') for d in old_data}

        # 2. Fetch new data
        data = fetch_orcid_works(ORCID_ID)
        works_groups = data.get('group', [])
        parsed_works = []
        
        for group in works_groups:
            summaries = group.get('work-summary', [])
            if summaries:
                work = parse_summary(summaries[0])
                if work:
                    parsed_works.append(work)
                    
                    # 3. If this is a new work, create a micro post
                    key = work.get('doi') or work.get('title')
                    if key and key not in existing_keys:
                        create_micro_post(work)
        
        # Sort by year descending
        parsed_works.sort(key=lambda x: x['year'], reverse=True)
        
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        with open(OUTPUT_FILE, 'w') as f:
            yaml.dump(parsed_works, f, sort_keys=False, allow_unicode=True)
            
        print(f"Successfully saved {len(parsed_works)} publications to {OUTPUT_FILE}")
        
        # Trigger stats update
        try:
            import update_stats
            update_stats.main()
        except ImportError:
            # If run from REPO_ROOT
            import scripts.update_stats as update_stats
            update_stats.main()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
