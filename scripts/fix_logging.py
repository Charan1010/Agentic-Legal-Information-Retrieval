"""Add detailed logging to the pipeline logger cell in notebook."""
import json

nb_path = r'c:\Users\6764325\OneDrive - MyFedEx\Desktop\Full Pipeline - RAG Competition\Omnilex-Agentic-Retrieval-Competition\notebooks\04_planner_director.ipynb'

with open(nb_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

# Find cell 19 (the pipeline logger cell - Cell 16.5)
target_cell = None
for cell in nb['cells']:
    source = ''.join(cell.get('source', []))
    if 'Cell 16.5: Comprehensive Pipeline Logger' in source:
        target_cell = cell
        break

if target_cell is None:
    print('ERROR: Could not find Cell 16.5')
    exit(1)

source_lines = target_cell['source']
source_text = ''.join(source_lines)

# Fix 1: Replace truncated context logging with full context logging
old_context = '    L.debug(f"\\n  --- INJECTED CONTEXT (first 2000 chars) ---")\n    L.debug(context_text[:2000])\n    if len(context_text) > 2000:\n        L.debug(f"  [...{len(context_text)-2000} more chars...]")'

new_context = '    L.debug(f"\\n  --- FULL INJECTED CONTEXT ---")\n    L.debug(context_text)\n    L.debug(f"  --- END INJECTED CONTEXT ---")'

if old_context in source_text:
    source_text = source_text.replace(old_context, new_context)
    print('Fix 1 applied: Full context logging')
else:
    print('Fix 1 FAILED: Could not find old context pattern')
    # Debug: show what we're looking for
    if 'INJECTED CONTEXT' in source_text:
        idx = source_text.index('INJECTED CONTEXT')
        print(f'  Found "INJECTED CONTEXT" at pos {idx}')
        print(f'  Surrounding: {repr(source_text[idx-50:idx+200])}')

# Fix 2: Add full system prompt logging after the length line
old_sysprompt = '    L.debug(f"  System prompt length: {len(system_prompt):,} chars (~{len(system_prompt)//4} tokens)")\n    \n    # 3. User message'

new_sysprompt = '    L.debug(f"  System prompt length: {len(system_prompt):,} chars (~{len(system_prompt)//4} tokens)")\n    L.debug(f"\\n  --- FULL SYSTEM PROMPT ---")\n    L.debug(system_prompt)\n    L.debug(f"  --- END SYSTEM PROMPT ---\\n")\n    \n    # 3. User message'

if old_sysprompt in source_text:
    source_text = source_text.replace(old_sysprompt, new_sysprompt)
    print('Fix 2 applied: Full system prompt logging')
else:
    print('Fix 2 FAILED: Could not find old sysprompt pattern')
    if 'System prompt length' in source_text:
        idx = source_text.index('System prompt length')
        print(f'  Found at pos {idx}')
        print(f'  Surrounding: {repr(source_text[idx-10:idx+200])}')

# Fix 3: Add reranker query logging before aggregate_and_output call
old_rerank = '    # Run aggregation WITH diagnostics (single reranker pass)\n    result, diag = aggregate_and_output(all_direction_citations, question, rerank_query=plan.sachverhalt, return_diagnostics=True)'

new_rerank = '''    # Log what reranker will receive as its query
    _actual_rerank_q = plan.sachverhalt if plan.sachverhalt else question
    _log_header("RERANKER INPUT QUERY", 2)
    L.debug(f"  sachverhalt present: {bool(plan.sachverhalt)}")
    L.debug(f"  Using: " + ("plan.sachverhalt" if plan.sachverhalt else "question (fallback — sachverhalt was empty)"))
    L.debug(f"  Rerank query text:")
    L.debug(f"    {_actual_rerank_q}")
    L.debug("")

    # Run aggregation WITH diagnostics (single reranker pass)
    result, diag = aggregate_and_output(all_direction_citations, question, rerank_query=plan.sachverhalt, return_diagnostics=True)'''

if old_rerank in source_text:
    source_text = source_text.replace(old_rerank, new_rerank)
    print('Fix 3 applied: Reranker query logging')
else:
    print('Fix 3 FAILED: Could not find old rerank pattern')
    if 'Run aggregation WITH diagnostics' in source_text:
        idx = source_text.index('Run aggregation WITH diagnostics')
        print(f'  Found at pos {idx}')
        print(f'  Surrounding: {repr(source_text[idx-10:idx+200])}')

# Write back as properly split lines
new_lines = [line + '\n' for line in source_text.split('\n')]
# Last line should not have trailing newline if original didn't
if source_lines and not source_lines[-1].endswith('\n'):
    new_lines[-1] = new_lines[-1].rstrip('\n')

target_cell['source'] = new_lines

with open(nb_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print('Notebook saved successfully')
