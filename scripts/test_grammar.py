"""Test GBNF grammar string production."""
import re

_GBNF_LINES = [
    r'root ::= "{" ws "\"thought\"" ws ":" ws string "," ws "\"action\"" ws ":" ws action-val "," ws "\"query\"" ws ":" ws string "}" ws',
    r'action-val ::= "\"search_laws\"" | "\"search_courts\"" | "\"done\""',
    r'string ::= "\"" chars "\""',
    r'chars ::= char*',
    r'char ::= [^"\\] | "\\" escape-char',
    r'escape-char ::= "\"" | "\\" | "/" | "n" | "t" | "r"',
    r'ws ::= [ \t\n]*',
]
AGENT_GRAMMAR_STR = "\n".join(_GBNF_LINES)

print("=== GBNF Grammar (as will be passed to LlamaGrammar.from_string) ===")
print(AGENT_GRAMMAR_STR)
print()
print("=== Validation ===")
# Check basic structure
assert 'root ::=' in AGENT_GRAMMAR_STR
assert 'action-val ::=' in AGENT_GRAMMAR_STR
assert '"search_laws"' in AGENT_GRAMMAR_STR or r'\"search_laws\"' in AGENT_GRAMMAR_STR
assert 'string ::=' in AGENT_GRAMMAR_STR
print("All assertions passed - grammar string looks correct")

# Show what the grammar would accept as valid output
print()
print("=== Example valid output the grammar would produce ===")
print('{"thought": "I need to search for contract law", "action": "search_laws", "query": "contract formation obligations"}')
