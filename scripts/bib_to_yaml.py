import os
import yaml
import re
import sys

# Configuration from Environment Variables
DROPBOX_CV_PATH = os.getenv('DROPBOX_CV_PATH')
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if not DROPBOX_CV_PATH:
    print("Error: DROPBOX_CV_PATH environment variable not set.")
    sys.exit(1)

def parse_bib(file_path):
    if not os.path.exists(file_path):
        print(f"Error: Bib file not found at {file_path}")
        return []
    
    with open(file_path, 'r') as f:
        content = f.read()

    # Improved regex to handle basic BibTeX entries more reliably
    entries = re.findall(r'@(\w+)\s*\{\s*([^,]+),([\s\S]*?)\n\}', content)
    parsed = []

    for entry_type, cite_key, fields_raw in entries:
        fields = {}
        # Match fields like title = {Content} or year = "2023"
        field_matches = re.findall(r'(\w+)\s*=\s*[\{"](.*?)[\"\}]', fields_raw)
        for k, v in field_matches:
            fields[k.lower()] = v.strip()

        parsed.append({
            'type': entry_type.lower(),
            'key': cite_key.strip(),
            **fields
        })
    return parsed

# Handle BibTeX -> YAML
bib_file = os.path.join(DROPBOX_CV_PATH, 'orcid_works.bib')
pubs = parse_bib(bib_file)

if pubs:
    pubs.sort(key=lambda x: x.get('year', '0'), reverse=True)
    out_file = os.path.join(REPO_ROOT, 'data/publications.yaml')
    with open(out_file, 'w') as f:
        yaml.dump(pubs, f)
    print(f"  [BibTeX] Converted {len(pubs)} entries to publications.yaml")
else:
    print(f"  [BibTeX] Warning: No publications found in {bib_file}")
