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

MONTH_MAP = {
    'january': 1, 'february': 2, 'march': 3, 'april': 4,
    'may': 5, 'june': 6, 'july': 7, 'august': 8,
    'september': 9, 'october': 10, 'november': 11, 'december': 12,
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4,
    'jun': 6, 'jul': 7, 'aug': 8, 'sep': 9,
    'oct': 10, 'nov': 11, 'dec': 12
}

def parse_bib(file_path):
    if not os.path.exists(file_path):
        print(f"Error: Bib file not found at {file_path}")
        return []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Improved regex to handle basic BibTeX entries more reliably
    entries = re.findall(r'@(\w+)\s*\{\s*([^,]+),([\s\S]*?)\n\}', content)
    parsed = []

    for entry_type, cite_key, fields_raw in entries:
        fields = {}
        # Match fields like title = {Content} or year = "2023"
        field_matches = re.findall(r'(\w+)\s*=\s*[\{"](.*?)[\"\}]', fields_raw)
        for k, v in field_matches:
            clean_val = v.strip().replace('{', '').replace('}', '')
            clean_val = clean_val.replace(r'\_', '_').replace(r'\&', '&').replace(r'\"', '"')
            clean_val = re.sub(r'[ \t]+', ' ', clean_val)
            fields[k.lower()] = clean_val

        parsed.append({
            'type': entry_type.lower(),
            'key': cite_key.strip(),
            **fields
        })
    return parsed

def get_sort_key(pub):
    raw_year = pub.get('year', '')
    try:
        year = int(raw_year)
    except (ValueError, TypeError):
        year = 0
    
    m_str = str(pub.get('month', '')).strip().lower()
    month = MONTH_MAP.get(m_str, 0)
    return (year, month)

# Handle BibTeX -> YAML
bib_file = os.path.join(DROPBOX_CV_PATH, 'orcid_works.bib')
pubs = parse_bib(bib_file)

if pubs:
    pubs.sort(key=get_sort_key, reverse=True)
    out_file = os.path.join(REPO_ROOT, 'data/publications.yaml')
    with open(out_file, 'w', encoding='utf-8') as f:
        yaml.dump(pubs, f, allow_unicode=True, sort_keys=False)
    print(f"  [BibTeX] Converted and counter-chronologically sorted {len(pubs)} entries to publications.yaml")
else:
    print(f"  [BibTeX] Warning: No publications found in {bib_file}")
