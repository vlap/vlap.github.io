import re

def parse_bib(file_path):
    with open(file_path, 'r') as f:
        content = f.read()
    
    entries = re.findall(r'@(\w+)\{(.*?),([\s\S]*?)\n\}', content)
    parsed = []
    
    for entry_type, cite_key, fields_raw in entries:
        fields = {}
        # Simple field extraction
        field_matches = re.findall(r'(\w+)\s*=\s*\{(.*?)\}', fields_raw)
        for k, v in field_matches:
            fields[k.lower()] = v
        
        # Handle fields with double braces or naked strings if necessary, 
        # but this simple regex covers basic bib files.
        
        parsed.append({
            'type': entry_type,
            'key': cite_key,
            **fields
        })
    return parsed

# For now, we will just parse and provide a way to render. 
# In a real Hugo setup, we'd use a shortcode that reads a JSON/YAML version.
# Let's convert the bib to YAML for Hugo.
import yaml

pubs = parse_bib('/home/volant/Dropbox/postdocs/cv/tex/orcid_works.bib')
# Sort by year descending
pubs.sort(key=lambda x: x.get('year', '0'), reverse=True)

with open('/home/volant/vlap.github.io/data/publications.yaml', 'w') as f:
    yaml.dump(pubs, f)

# Extract counts from counts.tex
counts = {}
try:
    with open('/home/volant/Dropbox/postdocs/cv/tex/src/parts/counts.tex', 'r') as f:
        content = f.read()
        pub_count = re.search(r'\\newcommand\{\\pubcount\}\{(\d+)\}', content)
        pres_count = re.search(r'\\newcommand\{\\prescount\}\{(\d+)\}', content)
        if pub_count: counts['publications'] = pub_count.group(1)
        if pres_count: counts['presentations'] = pres_count.group(1)
    
    with open('/home/volant/vlap.github.io/data/counts.yaml', 'w') as f:
        yaml.dump(counts, f)
except Exception as e:
    print(f"Warning: Could not extract counts: {e}")
