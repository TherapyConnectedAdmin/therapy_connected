import json
import os
import re
from django.apps import apps

PROFILE_FIELDS_PATH = 'profile_fields.json'
MODEL_NAME = 'TherapistProfile'
APP_LABEL = 'users'

# Load profile fields
with open(PROFILE_FIELDS_PATH) as f:
    profile_fields = json.load(f)

# Get all fields from TherapistProfile model
TherapistProfile = apps.get_model(APP_LABEL, MODEL_NAME)
model_fields = set([f.name for f in TherapistProfile._meta.get_fields() if not f.is_relation or f.one_to_one or f.many_to_one])

# Build new FIELD_MAP
field_map = {}
for section, fields in profile_fields.items():
    for field in fields:
        json_field = field.get('field')
        db_field = field.get('db_field_name')
        # Only map if db_field is a valid model field
        if db_field and db_field in model_fields:
            field_map[json_field] = db_field

# Output to field_map.py
with open('users/field_map.py', 'w') as out:
    out.write('# Mapping from JSON field names to TherapistProfile model field names\n')
    out.write('FIELD_MAP = ' + json.dumps(field_map, indent=4) + '\n')

print('FIELD_MAP rebuilt and written to users/field_map.py')
