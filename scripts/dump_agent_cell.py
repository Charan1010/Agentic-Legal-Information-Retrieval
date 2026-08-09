"""Dump the agent-related cells (system prompt, action parsing, run_agent, and verbose outputs) to a text file."""
import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

nb_path = "notebooks/03_hyde_kaggle.ipynb"
with open(nb_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

code_cells = [c for c in nb["cells"] if c["cell_type"] == "code"]

# Dump cells 10-12 (agent, predictions, submission) - these have the ReAct logic and outputs
for i in [10, 11, 12]:
    print(f"\n{'='*80}")
    print(f"CELL {i} — {len(code_cells[i]['source'])} source lines, {len(code_cells[i].get('outputs',[]))} outputs")
    print(f"{'='*80}")
    
    # Source code
    print("\n--- SOURCE CODE ---")
    for line_num, line in enumerate(code_cells[i]["source"], 1):
        print(f"{line_num:4d} | {line}", end="")
    
    # Outputs (truncated)
    outputs = code_cells[i].get("outputs", [])
    if outputs:
        print(f"\n\n--- OUTPUTS ({len(outputs)} output blocks) ---")
        for oi, out in enumerate(outputs):
            otype = out.get("output_type", "?")
            if otype == "stream":
                text = "".join(out.get("text", []))
                # Show first 5000 chars
                if len(text) > 5000:
                    print(f"[Output block {oi}, stream, {len(text)} chars — showing first 5000]")
                    print(text[:5000])
                    print("... [TRUNCATED] ...")
                else:
                    print(f"[Output block {oi}, stream, {len(text)} chars]")
                    print(text)
            elif otype == "execute_result":
                data = out.get("data", {})
                for k, v in data.items():
                    text = "".join(v) if isinstance(v, list) else str(v)
                    if len(text) > 2000:
                        print(f"[Output block {oi}, {otype}, {k}: {len(text)} chars — showing first 2000]")
                        print(text[:2000])
                    else:
                        print(f"[Output block {oi}, {otype}, {k}]")
                        print(text)
            else:
                print(f"[Output block {oi}, type={otype}]")
    else:
        print("\n--- NO OUTPUTS ---")
