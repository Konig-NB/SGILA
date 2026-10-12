import urllib.request, json, re

# Fetch the template directly from the Django project
template_path = r"C:\Users\Administrator\Downloads\RIDOKUNDA_with_grade2_activities(1)\RIDOKUNDA\sgila_project\templates\questions.html"

# Check JavaScript syntax by extracting JS between <script> tags
with open(template_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Find all script content
script_sections = re.findall(r'<script>(.*?)</script>', content, re.DOTALL)
print(f"Found {len(script_sections)} script section(s)")

if script_sections:
    js_code = script_sections[0]
    print(f"JS code length: {len(js_code)}")
    
    # Check for common syntax issues
    # Count braces
    open_braces = js_code.count('{')
    close_braces = js_code.count('}')
    open_parens = js_code.count('(')
    close_parens = js_code.count(')')
    
    print(f"Braces: {open_braces} open, {close_braces} close, balanced={open_braces==close_braces}")
    print(f"Parens: {open_parens} open, {close_parens} close, balanced={open_parens==close_parens}")
    
    # Check template syntax ({% ... %}) - these should NOT be in JS
    django_tags = re.findall(r'\{%\s*.*?\s*%\}', js_code)
    if django_tags:
        print(f"WARNING: Found Django template tags in JS: {django_tags}")
    else:
        print("No Django template tags in JS sections")
    
    # Check the renderActivity function specifically
    ra_start = js_code.find('function renderActivity()')
    if ra_start >= 0:
        ra_end = js_code.find('\nfunction ', ra_start + 10)
        if ra_end < 0:
            ra_end = len(js_code)
        ra_code = js_code[ra_start:ra_end]
        print(f"\nrenderActivity function ({len(ra_code)} chars):")
        # Check for the key logic
        has_isVisualMatch = 'isVisualMatch' in ra_code
        has_isFixMistake = 'isFixMistake' in ra_code
        has_instruction = 'const instruction' in ra_code
        has_set_instruction = 'activity-instruction' in ra_code and 'textContent' in ra_code
        print(f"  Has isVisualMatch: {has_isVisualMatch}")
        print(f"  Has isFixMistake: {has_isFixMistake}")
        print(f"  Has instruction variable: {has_instruction}")
        print(f"  Sets activity-instruction: {has_set_instruction}")
