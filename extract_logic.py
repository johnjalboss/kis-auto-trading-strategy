import os
import ast
import json

def extract_module_info(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        
        # 1. Get module docstring (Purpose)
        docstring = ast.get_docstring(tree) or "No docstring provided."
        docstring = docstring.strip().split('\n')[0:3] # Get first few lines
        docstring = " ".join(docstring).replace('\r', '')
        
        # 2. Extract specific yfinance or kis_data fields
        data_fields = []
        scoring_logic = []
        
        for node in ast.walk(tree):
            # Look for dictionary/series access (e.g., info.get('trailingPE') or df['Close'])
            if isinstance(node, ast.Call) and getattr(node.func, 'attr', '') == 'get':
                if len(node.args) > 0 and isinstance(node.args[0], ast.Constant):
                    data_fields.append(node.args[0].value)
            
            if isinstance(node, ast.Subscript):
                if isinstance(node.slice, ast.Constant):
                    data_fields.append(node.slice.value)
            
            # Identify scoring logic (score += X, score -= Y)
            if isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name):
                if node.target.id == 'score' or 'score' in node.target.id:
                    if isinstance(node.value, ast.Constant):
                        op = '+' if isinstance(node.op, ast.Add) else '-' if isinstance(node.op, ast.Sub) else '?'
                        scoring_logic.append(f"{op}{node.value.value}")
        
        # Filter data fields to only string keys (like 'Close', 'trailingPE', etc)
        data_fields = list(set([str(f) for f in data_fields if isinstance(f, str)]))
        # Exclude common non-data strings
        ignore_list = ['score', 'symbol', 'date', 'name', 'value']
        data_fields = [f for f in data_fields if len(f) > 1 and f.lower() not in ignore_list]
        
        return {
            "file": os.path.basename(filepath),
            "purpose": docstring,
            "data_fields": data_fields[:15], # Limit to 15 to avoid noise
            "scoring": list(set(scoring_logic))
        }
    except Exception as e:
        return {"file": os.path.basename(filepath), "error": str(e)}

output = []
for filename in os.listdir('.'):
    if filename.endswith('.py'):
        info = extract_module_info(filename)
        output.append(info)

# Write to markdown
with open('all_modules_logical_audit.md', 'w', encoding='utf-8') as f:
    f.write("# 149 Modules Logical Validity Audit\n\n")
    for item in sorted(output, key=lambda x: x['file']):
        f.write(f"### {item['file']}\n")
        if 'error' in item:
            f.write(f"**Error:** {item['error']}\n\n")
        else:
            f.write(f"**Purpose:** {item['purpose']}\n")
            f.write(f"**Data Fields Fetched:** {', '.join(item['data_fields']) if item['data_fields'] else 'None directly parsed'}\n")
            f.write(f"**Scoring Logic:** {', '.join(item['scoring']) if item['scoring'] else 'None detected'}\n")
            f.write("\n")

print("Done generating all_modules_logical_audit.md")
