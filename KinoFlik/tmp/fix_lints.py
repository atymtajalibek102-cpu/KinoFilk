
import re
import os

filepath = r"c:\Users\ПК\Desktop\KinoFlik — копия\KinoFlik\templates\index.html"

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix aspect-ratio to be more compatible (space it out)
content = content.replace('aspect-ratio: 2/3;', 'aspect-ratio: 2 / 3;')

# Ensure all JS variables use tojson and are quoted where appropriate to satisfy linter
# though they were already mostly fine, let's make sure they are compact
content = re.sub(r'id:\s+\{\{\s+m\.id\s+\}\}', 'id: {{ m.id | tojson }}', content)
content = re.sub(r'title:\s+\{\{\s+\(m\.title\s+or\s+\'\'\)\|tojson\s+\}\}', 'title: {{ (m.title or "")|tojson }}', content)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Check complete.")
