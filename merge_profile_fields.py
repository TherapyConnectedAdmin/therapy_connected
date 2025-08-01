import os
import json

# Directory containing JSON files
PROFILE_FIELDS_DIR = 'profile_fields'
OUTPUT_FILE = 'profile_fields.json'

merged = {}

for filename in os.listdir(PROFILE_FIELDS_DIR):
    if filename.endswith('.json'):
        path = os.path.join(PROFILE_FIELDS_DIR, filename)
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # If the file is a dict, merge keys
            if isinstance(data, dict):
                merged.update(data)
            # If the file is a list, add under a key named after the file (without .json)
            elif isinstance(data, list):
                key = filename.replace('.json', '')
                merged[key] = data

with open(OUTPUT_FILE, 'w', encoding='utf-8') as out:
    json.dump(merged, out, indent=2)

print(f"Merged profile fields written to {OUTPUT_FILE}")
