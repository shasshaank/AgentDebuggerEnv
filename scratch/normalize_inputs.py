import os
import sys
import pprint

sys.path.append(os.path.abspath('.'))
from data.generate_bugs import TIER1_BUGS, TIER2_BUGS, TIER3_BUGS

def normalize_test_cases(bugs):
    for b in bugs:
        for t in b.get("test_cases", []):
            inp = t["input"]
            if isinstance(inp, (list, tuple)):
                t["input"] = list(inp)
            else:
                t["input"] = [inp]

normalize_test_cases(TIER1_BUGS)
normalize_test_cases(TIER2_BUGS)
normalize_test_cases(TIER3_BUGS)

def dump_var(f, name, val):
    f.write(f'{name} = ')
    f.write(pprint.pformat(val, sort_dicts=False, width=120))
    f.write('\n\n')

with open("data/generate_bugs.py", "w", encoding="utf-8") as f:
    f.write('"""\nAgentDebuggerEnv - Bug Dataset Generator\n\n')
    f.write('Generates three tiers of buggy Python functions for curriculum learning:\n')
    f.write('  Tier 1 (easy):   Off-by-one errors, wrong operators, simple logic inversions\n')
    f.write('  Tier 2 (medium): Incorrect algorithm logic, wrong variable references, subtle type errors\n')
    f.write('  Tier 3 (hard):   Multi-bug interactions, concurrency, edge-case-only failures\n\n')
    f.write('Usage:\n  python data/generate_bugs.py\n\n')
    f.write('Outputs:\n  data/bugs_tier1.jsonl  (~40 bugs)\n  data/bugs_tier2.jsonl  (~30 bugs)\n  data/bugs_tier3.jsonl  (~20 bugs)\n"""\n\n')
    f.write('import json\nimport os\n\n')
    
    dump_var(f, 'TIER1_BUGS', TIER1_BUGS)
    dump_var(f, 'TIER2_BUGS', TIER2_BUGS)
    dump_var(f, 'TIER3_BUGS', TIER3_BUGS)
    
    f.write('def write_jsonl(bugs: list, path: str):\n')
    f.write('    with open(path, "w") as f:\n')
    f.write('        for bug in bugs:\n')
    f.write('            f.write(json.dumps(bug) + "\\n")\n\n')
    f.write('if __name__ == "__main__":\n')
    f.write('    os.makedirs("data", exist_ok=True)\n')
    f.write('    write_jsonl(TIER1_BUGS, "data/bugs_tier1.jsonl")\n')
    f.write('    write_jsonl(TIER2_BUGS, "data/bugs_tier2.jsonl")\n')
    f.write('    write_jsonl(TIER3_BUGS, "data/bugs_tier3.jsonl")\n')
    f.write('    print(f"Tier 1: {len(TIER1_BUGS)}, Tier 2: {len(TIER2_BUGS)}, Tier 3: {len(TIER3_BUGS)}")\n')
    f.write('    print("\\nDone. Run training/train_grpo.py to start training.")\n')

print("Normalization applied successfully.")
