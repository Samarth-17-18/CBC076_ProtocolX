import json

with open('main_patch_859.json', 'r', encoding='utf-8') as f:
    args = json.load(f)
repl = args['ReplacementContent']

with open('backend/main.py', 'r', encoding='utf-8') as f:
    text = f.read()

p1 = text.find('@app.get("/api/admin/ml-model")')
p2 = text.find('@app.put("/api/reports/{report_id}/review")')

text = text[:p1] + repl + '\n\n' + text[p2:]
with open('backend/main.py', 'w', encoding='utf-8') as f:
    f.write(text)

print('Patch 859 applied cleanly! Final lines:', len(text.splitlines()))
