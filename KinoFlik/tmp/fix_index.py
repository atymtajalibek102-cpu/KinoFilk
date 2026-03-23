
import re
import os

filepath = r"c:\Users\ПК\Desktop\KinoFlik — копия\KinoFlik\templates\index.html"

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix Jinja2 tags split by tool
# Pattern: { \n % -> {% or { % -> {%
content = re.sub(r'\{\s+%', '{%', content)
content = re.sub(r'%\s+\}', '%}', content)
content = re.sub(r'\{\s+\{', '{{', content)
content = re.sub(r'\}\s+\}', '}}', content)

# Fix JS template literals split by tool
# Pattern: $ { -> ${
content = re.sub(r'\$\s+\{', '${', content)

# Fix specifically botched block tags if they got extra spaces
content = re.sub(r'\{%\s+block', '{% block', content)
content = re.sub(r'\{%\s+endblock', '{% endblock', content)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Repair complete.")
