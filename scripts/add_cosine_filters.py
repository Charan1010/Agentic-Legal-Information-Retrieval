"""Implement 3 cosine similarity improvements in the pipeline notebook."""
import json

nb_path = 'notebooks/04_planner_director.ipynb'
with open(nb_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

# ═══════════════════════════════════════════════════════════════════════════════
# FIX 1: Smart default filtering using cosine similarity
# In aggregate_and_output (cell 16): Instead of blindly injecting all defaults,
# score each against the query embedding and only keep relevant ones.
# ═══════════════════════════════════════════════════════════════════════════════

cell16 = nb['cells'][16]
src = cell16['source']

# Find the old default injection block and replace it
old_default_block = '    for default_cit in defaults:\n'
new_default_block = '''    # --- SMART DEFAULT FILTERING (cosine similarity) ---
    # Only inject defaults that are semantically relevant to this query.
    # Prevents 8-9 irrelevant boilerplate citations from polluting output.
    if defaults:
        query_emb = embed_query(_rerank_q, "laws")  # (1, dim)
        default_texts = [citation_to_text.get(d, d) for d in defaults]
        default_embs = _st_model.encode(
            default_texts,
            prompt=CONFIG["prompt_doc_law"],
            normalize_embeddings=True,
            batch_size=len(defaults),
        ).astype("float32")
        sims = (query_emb @ default_embs.T)[0]  # shape (n_defaults,)
        DEFAULTS_SIM_THRESHOLD = 0.30
        for default_cit, sim in zip(defaults, sims):
            if sim >= DEFAULTS_SIM_THRESHOLD:
                all_citations.append((default_cit, float(sim) * 0.005))  # Tiny score so real results still rank above
    defaults_injected = [d for d, s in zip(defaults, sims) if s >= DEFAULTS_SIM_THRESHOLD] if defaults else []
'''

found_fix1 = False
for i, line in enumerate(src):
    if 'for default_cit in defaults:' in line:
        # Replace this line and the next (the append line)
        # Find the append line
        j = i + 1
        while j < len(src) and 'all_citations.append' not in src[j]:
            j += 1
        if j < len(src):
            # Replace lines i through j (inclusive)
            src[i:j+1] = [new_default_block]
            found_fix1 = True
            print(f'Fix 1: Smart default filtering (cell 16, replaced lines {i}-{j})')
            break

if not found_fix1:
    print('Fix 1: NOT FOUND')

# Also update the diagnostics to show which defaults were actually injected
for i, line in enumerate(src):
    if '"defaults": defaults' in line:
        src[i] = line.replace('"defaults": defaults', '"defaults": defaults_injected if "defaults_injected" in dir() else defaults')
        print(f'Fix 1b: Updated diagnostics to show filtered defaults (line {i})')
        break

# ═══════════════════════════════════════════════════════════════════════════════
# FIX 2: Post-retrieval quality filter using cosine similarity
# After RRF dedup, drop any citation whose doc embedding has low similarity
# to the query. This replaces the broken Qwen3-Reranker.
# ═══════════════════════════════════════════════════════════════════════════════

# Find the "Sort by RRF score descending" block and insert quality filter after dedup
old_sort_line = '    # Sort by RRF score descending (higher = better retrieval match)\n'
new_sort_block = '''    # --- POST-RETRIEVAL QUALITY FILTER (cosine similarity) ---
    # Score each candidate's document text against the query.
    # This replaces the broken Qwen3-Reranker with a working semantic filter.
    if len(citation_scores) > 5:  # Only filter if we have enough candidates
        query_emb = embed_query(_rerank_q, "laws")  # (1, dim)
        cit_list = list(citation_scores.keys())
        doc_texts = [citation_to_text.get(c, c)[:512] for c in cit_list]
        doc_embs = _st_model.encode(
            doc_texts,
            prompt=CONFIG["prompt_doc_law"],
            normalize_embeddings=True,
            batch_size=CONFIG["embed_batch_size"],
        ).astype("float32")
        doc_sims = (query_emb @ doc_embs.T)[0]  # shape (n_candidates,)
        POST_RETRIEVAL_SIM_FLOOR = 0.20  # Drop clearly irrelevant results
        for cit, sim in zip(cit_list, doc_sims):
            if sim < POST_RETRIEVAL_SIM_FLOOR and citation_scores[cit] < 0.01:
                # Only drop if BOTH RRF score is low AND embedding similarity is low
                del citation_scores[cit]

    # Sort by RRF score descending (higher = better retrieval match)
'''

found_fix2 = False
src = cell16['source']  # re-read after fix 1 modified it
for i, line in enumerate(src):
    if '# Sort by RRF score descending' in line:
        src[i] = new_sort_block
        found_fix2 = True
        print(f'Fix 2: Post-retrieval quality filter (cell 16, line {i})')
        break

if not found_fix2:
    print('Fix 2: NOT FOUND')

# ═══════════════════════════════════════════════════════════════════════════════
# FIX 3: Executor query diversity using embedding similarity
# In run_direction (cell 15): Before executing a new query, check if it's too
# similar to any previous query's embedding. If >0.80, regenerate or skip.
# ═══════════════════════════════════════════════════════════════════════════════

cell15 = nb['cells'][15]
src15 = cell15['source']

# Find "# Check for repeated query" and insert embedding diversity check after it
old_repeat_check = '        # Check for repeated query\n'
new_repeat_block = '''        # Check for repeated query (exact match)
        query = parsed["query"].strip()
        if query in [h["query"] for h in history]:
            break

        # --- EMBEDDING DIVERSITY CHECK ---
        # Reject queries that are semantically too similar to previous ones
        # (catches synonym rephrasing that word-overlap rules miss)
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
                break  # Query too similar to a previous one — stop direction

'''

found_fix3 = False
for i, line in enumerate(src15):
    if '# Check for repeated query' in line or '# Check repeated' in line:
        # Find the end of the existing repeat-check block (the 'break' line after it)
        j = i + 1
        while j < len(src15):
            if 'break' in src15[j] and 'query' not in src15[j]:
                break
            j += 1
        # Replace lines i through j (the check + query assignment + if + break)
        src15[i:j+1] = [new_repeat_block]
        found_fix3 = True
        print(f'Fix 3: Executor embedding diversity check (cell 15, replaced lines {i}-{j})')
        break

if not found_fix3:
    print('Fix 3: NOT FOUND — trying alternate pattern')
    # Try looking for the exact current code pattern
    for i, line in enumerate(src15):
        if 'Check repeated' in line or 'repeated query' in line:
            print(f'  Found at line {i}: {line.rstrip()}')

# Save
with open(nb_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)
    f.write('\n')

print('\nDone — notebook saved with 3 cosine similarity improvements.')
