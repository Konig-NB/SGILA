path = r"C:\Users\Administrator\Downloads\RIDOKUNDA_with_grade2_activities(1)\RIDOKUNDA\sgila_project\templates\questions.html"
with open(path, 'rb') as f:
    content = f.read()
crlf = content.count(b'\r\n')
lf = content.count(b'\n') - crlf
print(f"CRLF line endings: {crlf}")
print(f"LF line endings: {lf}")
print(f"File size: {len(content)} bytes")
print(f"Contains UTF-8 BOM: {content[:3] == b'\xef\xbb\xbf'}")
# Verify key strings exist
text = content.decode('utf-8')
checks = [
    "Look at the picture, then choose the word that names it.",
    "One word in this sentence is wrong",
    "Choose a match for all four",
    "const spokenText = instruction;",
    "const highlightElements = instructionEl ? [instructionEl, questionText] : [questionText];",
]
for c in checks:
    print(f"Contains '{c[:50]}...': {c in text}")
