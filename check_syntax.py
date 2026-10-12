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
    # Check the new code is present
    has_new_spokenText = 'const spokenText = instruction || activity.question;' in js_code
    has_new_highlight = 'const highlightElements = instructionEl ? [instructionEl] : [questionText];' in js_code
    has_old_readingActivity = 'isReadingActivity' in js_code
    print(f"New spokenText present: {has_new_spokenText}")
    print(f"New highlight present: {has_new_highlight}")
    print(f"Old isReadingActivity still present: {has_old_readingActivity}")
