"""
Apply translations to language.py
This script adds missing translations to each language dictionary
"""

import json
import re

# Load the generated translations
with open('/app/backend/utils/translations_to_add.json', 'r', encoding='utf-8') as f:
    translations_to_add = json.load(f)

# Read the current language.py
with open('/app/backend/routes/language.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find each language dictionary and add missing keys
for lang, translations in translations_to_add.items():
    if not translations:
        continue
    
    # Find the closing brace of this language's dictionary
    # Pattern: find "lang": { ... }, and add before the final },
    pattern = rf'("{lang}": \{{[^}}]*?\n    }})'
    
    # Build the addition string
    additions = []
    for key, value in sorted(translations.items()):
        # Escape special characters
        escaped_value = value.replace('\\', '\\\\').replace('"', '\\"')
        additions.append(f'        "{key}": "{escaped_value}"')
    
    additions_str = ',\n'.join(additions)
    
    # Find the last entry in each language section and add after it
    # Look for pattern like "key": "value",\n    }, where }, ends the dict
    search_pattern = rf'("{lang}": \{{\n)(.*?)(\n    \}})'
    
    def replacement(match):
        prefix = match.group(1)
        existing = match.group(2)
        suffix = match.group(3)
        
        # Add new entries before closing brace
        if additions_str:
            # Ensure existing content ends with comma if it doesn't
            if existing.rstrip().endswith('"'):
                existing = existing.rstrip() + ','
            return f'{prefix}{existing}\n        # Auto-filled translations\n{additions_str}{suffix}'
        return match.group(0)
    
    content = re.sub(search_pattern, replacement, content, flags=re.DOTALL)

# Write the updated content
with open('/app/backend/routes/language.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Translations applied successfully!")

# Verify the update
import sys
sys.path.insert(0, '/app/backend/routes')
# Force reload
import importlib
import language
importlib.reload(language)

from language import TRANSLATIONS

en_keys = set(TRANSLATIONS.get('en', {}).keys())
print(f"\nEnglish keys: {len(en_keys)}")

for lang in ['hi', 'fr', 'ar', 'th', 'vi', 'id', 'ms']:
    lang_keys = set(TRANSLATIONS.get(lang, {}).keys())
    missing = en_keys - lang_keys
    print(f"{lang}: {len(lang_keys)} keys, missing {len(missing)}")
