# Results

Published evaluation results, kept in version control as a record.

> **Read these with the caveat that they have no held-out split.** The trainer and
> `evaluate-curriculum` both draw from all 90 bugs, so the solve rate below
> measures how well the policy fit the training set, not whether it generalises.
> These numbers are a record of a run, not evidence for any of the project's
> claims — see [docs/research_plan.md](../docs/research_plan.md) for the experiment
> design that would actually test them.

| File | What it is |
| --- | --- |
| `qwen2.5-coder-3b-grpo.json` | The GRPO-trained `Qwen2.5-Coder-3B` adapter, scored on all 90 curriculum bugs. |
| `oracle.json` | The oracle agent on the three hand-written tasks — the score ceiling every model is compared against. Regenerate with `agentdebugger evaluate --output results/oracle.json`. |

To reproduce the trained-model numbers:

```bash
pip install -e '.[train]'
agentdebugger evaluate-curriculum \
    --adapter shashaank0707/AgentDebugger-trained \
    --output results/qwen2.5-coder-3b-grpo.json
```
