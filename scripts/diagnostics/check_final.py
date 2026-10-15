import re
template_path = r"C:\Users\Administrator\Downloads\RIDOKUNDA_with_grade2_activities(1)\RIDOKUNDA\sgila_project\templates\questions.html"
with open(template_path, 'r', encoding='utf-8') as f:
    content = f.read()
script_sections = re.findall(r'<script>(.*?)</script>', content, re.DOTALL)
if script_sections:
    js_code = script_sections[0]
    open_braces = js_code.count('{')
    close_braces = js_code.count('}')
    open_parens = js_code.count('(')
    close_parens = js_code.count(')')
    print(f"Braces: {open_braces} open, {close_braces} close, balanced={open_braces==close_braces}")
    print(f"Parens: {open_parens} open, {close_parens} close, balanced={open_parens==close_parens}")
    has_question = 'const question = activity.question;' in js_code
    has_hasOverlap = 'hasOverlap' in js_code
    has_spokenText = 'const spokenText = hasOverlap' in js_code or 'spokenText = hasOverlap' in js_code
    has_highlight = 'instructionEl ? [instructionEl, questionText]' in js_code
    print(f"question variable: {has_question}")
    print(f"hasOverlap logic: {has_hasOverlap}")
    print(f"spokenText with hasOverlap: {has_spokenText}")
    print(f"both highlight: {has_highlight}")
