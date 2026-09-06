import requests
import pandas as pd
import json

print("Downloading MITRE ATT&CK Data...")
url = "https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json"
data = requests.get(url).json()
objects = data['objects']

# Filter objects
techniques = [obj for obj in objects if obj['type'] == 'attack-pattern' and not obj.get('revoked') and not obj.get('x_mitre_deprecated')]
mitigations = {obj['id']: obj for obj in objects if obj['type'] == 'course-of-action'}
relationships = [obj for obj in objects if obj['type'] == 'relationship']

# Map external IDs (T-codes, M-codes)
id_map = {}
for obj in objects:
    for ref in obj.get('external_references', []):
        if ref.get('source_name') == 'mitre-attack':
            id_map[obj['id']] = ref['external_id']

# Build the flat CSV rows
rows = []
for tech in techniques:
    tech_id = id_map.get(tech['id'], tech['id'])
    name = tech['name']
    desc = tech.get('description', '')
    
    # Get tactics
    tactics = ", ".join([kcp['phase_name'] for kcp in tech.get('kill_chain_phases', [])])
    
    # Find mitigations via relationships
    tech_mits = []
    for rel in relationships:
        if rel['relationship_type'] == 'mitigates' and rel['target_ref'] == tech['id']:
            mit_id = rel['source_ref']
            mit_code = id_map.get(mit_id, 'Unknown')
            mit_name = mitigations.get(mit_id, {}).get('name', 'Unknown')
            tech_mits.append(f"{mit_code}: {mit_name}")
            
    # Join mitigations into a single string for Pinecone metadata
    mit_string = "; ".join(tech_mits) if tech_mits else "None"

    # Create the semantic text chunk
    text_chunk = f"MITRE Technique {tech_id} ({name}). Tactic: {tactics}. Description: {desc}. Mitigations: {mit_string}"

    rows.append({
        "id": tech_id,             # Pinecone ID
        "text_chunk": text_chunk,  # What the LLM will read
        "technique_name": name,    # Metadata
        "tactic": tactics,         # Metadata
        "mitigations": mit_string  # Metadata
    })

# Save to CSV
df = pd.DataFrame(rows)
df.to_csv("mitre_normalized.csv", index=False)
print("Success! Saved 'mitre_normalized.csv'. Upload this to your Google Drive.")