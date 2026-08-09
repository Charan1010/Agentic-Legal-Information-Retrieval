"""Apply embedding diversity check to run_direction_logged in cell 18."""
import json

nb_path = 'notebooks/04_planner_director.ipynb'
with open(nb_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

cell18 = nb['cells'][18]
src18 = cell18['source']

# The cell stores content as list of strings (one per logical section sometimes)
# Need to find "Check for repeated query" in this cell and inject diversity check

new_diversity_block = '''        # Check for repeated query (exact match)
        query = parsed["query"].strip()
        if query in [h["query"] for h in history]:
            break

        # --- EMBEDDING DIVERSITY CHECK ---
        # Reject queries that are semantically too similar to previous ones
        if history:
            new_emb = embed_query(query, direction.corpus)  # (1, dim)
            too_similar = False
            for prev in history:
                prev_emb = embed_query(prev["query"], direction.corpus)
                sim = float((new_emb @ prev_emb.T)[0, 0])
                if sim > 0.80:
                    too_similar = True
                    break
            if too_similar:
                break  # Query too similar to a previous one

'''

found = False
for i, line in enumerate(src18):
    if 'Check for repeated query' in line or 'Check repeated' in line:
        # Find the extent of the old block - up to next "# Execute search" or similar
        j = i + 1
        while j < len(src18):
            content = src18[j]
            # Look for the next logical section (Execute search, search call, etc)
            if '# Execute search' in content or 'filtered_hybrid_search' in content:
                break
            j += 1
        # Replace lines i through j-1 with new block
        src18[i:j] = [new_diversity_block]
        found = True
        print(f'Fixed cell 18: Replaced lines {i}-{j-1} with diversity check')
        break

if not found:
    # Maybe the content is all in one big string
    joined = ''.join(src18)
    if 'Check for repeated query' in joined or 'Check repeated' in joined:
        print("Found in joined source - need different approach")
        # Find and replace within the joined string
        import re
        # Pattern: from "# Check for repeated query" to just before "# Execute search"
        pattern = r'(        # Check for repeated query.*?break\n)\n(        # Execute search)'
        replacement = new_diversity_block + '\n        # Execute search'
        new_joined, count = re.subn(pattern, replacement, joined, flags=re.DOTALL)
        if count > 0:
            src18[:] = [new_joined]
            found = True
            print(f'Fixed cell 18 via regex replacement ({count} occurrence(s))')
        else:
            # Try alternate patterns
            print("Regex didn't match. Searching for exact text...")
            idx = joined.find('Check repeated')
            if idx < 0:
                idx = joined.find('repeated query')
            print(f"  Found at position {idx}")
            context = joined[max(0,idx-20):idx+200] if idx >= 0 else "NOT FOUND"
            print(f"  Context: {context[:300]}")
    else:
        print("NOT FOUND anywhere in cell 18")

with open(nb_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)
    f.write('\n')

print('Done.')
