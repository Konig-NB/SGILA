import re
template_path = r"C:\Users\Administrator\Downloads\RIDOKUNDA_with_grade2_activities(1)\RIDOKUNDA\sgila_project\templates\questions.html"
with open(template_path, 'r', encoding='utf-8') as f:
    content = f.read()
script_sections = re.findall(r'<script>(.*?)</script>', content, re.DOTALL)
if script_sections:
    js_code = script_sections[0]
    print(f"Braces balanced: {js_code.count('{') == js_code.count('}')}")
    print(f"Parens balanced: {js_code.count('(') == js_code.count(')')}")
    print(f"spokenText = instruction only: {'const spokenText = instruction;' in js_code}")
    print(f"hasOverlap for highlight: {'hasOverlap' in js_code}")
    print(f"both highlight: {'[instructionEl, questionText]' in js_code}")
    print(f"no concat: {'${instruction}. ${question}' not in js_code}")
