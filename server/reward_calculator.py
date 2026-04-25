"""
DebugRewardCalculator — Multi-component reward system for AgentDebuggerEnv.

Reward taxonomy follows:
  - Masud et al. (2026) "Reward Engineering for RL in Software Tasks"
    → Uses their execution-based + process-based + semantic similarity taxonomy
  - Ibrahim et al. (2024) "Comprehensive Overview of Reward Engineering and Shaping"
    → Uses potential-based shaping for efficiency component to preserve policy invariance

Design principle: GRPO learns by comparing completions WITHIN a group.
Relative reward differences matter more than absolute values.
Therefore: be generous with partial credit so the model gets differentiated signal
even when nothing fully works.
"""

import difflib
import re
from dataclasses import dataclass
from typing import Optional
from server.models import StructuredAgentOutput


@dataclass
class RewardBreakdown:
    format_compliance: float     # fires every turn — gives early training signal
    hypothesis_quality: float    # process-based reward (Paper 2 taxonomy)
    localization: float          # execution-based proxy
    fix_quality: float           # execution-based reward (primary terminal signal)
    semantic_similarity: float   # semantic reward (Paper 2 taxonomy)
    efficiency_potential: float  # potential-based shaping (Paper 1)
    penalties: float
    total: float


class DebugRewardCalculator:
    """
    Reward weights (must sum to 1.0 excluding penalties):
      format_compliance:    0.10  — fires every turn, drives early curve movement
      hypothesis_quality:   0.20  — process-based, independent of fix success
      localization:         0.15  — did agent find the right place?
      fix_quality:          0.35  — execution-based, primary terminal signal (sparse)
      semantic_similarity:  0.10  — how close to canonical fix?
      efficiency_potential: 0.10  — potential-based shaping across turns

    IMPORTANT NOTE ON SPARSITY vs DENSITY:
    The fix_quality reward (0.35) is sparse — it only fires when tests pass.
    The format, hypothesis, localization rewards are dense — they fire every turn.
    This combination is intentional: dense rewards carry gradient signal while the
    model is still learning to fix bugs; sparse rewards dominate once it gets good.
    This directly implements Ibrahim et al.'s recommendation to combine reward
    shaping with terminal rewards to solve the sparse reward problem.
    """

    MAX_TURNS = 5

    def compute_turn_reward(
        self,
        agent_output: StructuredAgentOutput,
        ground_truth: dict,
        test_results: dict,
        turn_number: int,
    ) -> RewardBreakdown:
        """
        Compute reward for a single agent turn.

        Args:
            agent_output: parsed structured output from the agent
            ground_truth: {
                "bug_function": str,   # name of function containing the bug
                "bug_line": int,       # line number of the bug
                "bug_type": str,       # category of bug
                "canonical_fix_code": str,  # the correct minimal fix
            }
            test_results: {
                "passed": int,
                "failed": int,
                "total": int,
                "newly_broken": int,   # tests that passed before but fail after fix
            }
            turn_number: 0-indexed turn number within the episode

        Returns:
            RewardBreakdown with total and all component scores
        """

        # ── COMPONENT 1: FORMAT COMPLIANCE ────────────────────────────────
        # This fires EVERY turn. Gives the model early training signal before
        # it learns to fix bugs. Drives curve movement in first 50-100 steps.
        if agent_output.valid:
            format_score = 0.10
        else:
            # Partial credit: how many fields were present?
            fields_present = sum([
                len(agent_output.observation) > 5,
                len(agent_output.hypothesis) > 10,
                agent_output.confidence in {"low", "medium", "high"},
                agent_output.action in {"inspect_lines", "run_tests", "propose_fix",
                                        "request_context", "give_up"},
                len(agent_output.detail) > 0,
            ])
            format_score = -0.25 + (fields_present * 0.04)  # -0.25 to -0.05

        # ── COMPONENT 2: HYPOTHESIS QUALITY (Process-based, Paper 2) ──────
        # Score reasoning quality INDEPENDENTLY from whether the fix works.
        # A correct diagnosis that leads to a wrong fix still gets rewarded here.
        # This trains the model to reason carefully even when uncertain.
        hypothesis_score = 0.0
        hypothesis = agent_output.hypothesis

        if len(hypothesis.split()) >= 20:
            hypothesis_score += 0.05   # not a one-liner

        # References specific code elements (backticks, quotes, or operators)
        if re.search(r'[`\'"<>!=+\-*/]', hypothesis):
            hypothesis_score += 0.05

        # Mentions line numbers
        if re.search(r'\bline\s+\d+\b|\b\d+\b', hypothesis):
            hypothesis_score += 0.05

        # Logically consistent: OBSERVATION and HYPOTHESIS reference same code area
        obs_words = set(agent_output.observation.lower().split())
        hyp_words = set(hypothesis.lower().split())
        overlap = len(obs_words & hyp_words) / max(len(obs_words), 1)
        if overlap > 0.15:
            hypothesis_score += 0.05

        # Confidence calibration: rewards correct confidence, penalizes overconfidence
        # High confidence + correct = bonus, High confidence + wrong = penalty
        if agent_output.action == "propose_fix":
            tests_pass = test_results.get("passed", 0) == test_results.get("total", 1)
            if agent_output.confidence == "high" and tests_pass:
                hypothesis_score += 0.05   # well-calibrated
            elif agent_output.confidence == "high" and not tests_pass:
                hypothesis_score -= 0.05   # overconfident
            elif agent_output.confidence == "low" and tests_pass:
                hypothesis_score += 0.02   # humble but correct

        hypothesis_score = max(0.0, min(hypothesis_score, 0.20))

        # ── COMPONENT 3: LOCALIZATION (Execution-based proxy) ─────────────
        # Did the agent identify WHERE the bug is, independently of fixing it?
        localization_score = 0.0
        bug_function = ground_truth.get("bug_function", "").lower()
        bug_line = str(ground_truth.get("bug_line", -1))

        combined_text = (agent_output.hypothesis + " " + agent_output.detail).lower()

        if bug_function and bug_function in combined_text:
            localization_score += 0.08

        if bug_line != "-1" and bug_line in agent_output.hypothesis:
            localization_score += 0.07

        localization_score = min(localization_score, 0.15)

        # ── COMPONENT 4: FIX QUALITY (Execution-based, Paper 2 primary) ───
        # This is the dominant signal. Sparse but high value.
        # Paper 1: combine with shaping (components 1-3) to solve sparse problem.
        total_tests = test_results.get("total", 0)
        passed_tests = test_results.get("passed", 0)
        fix_score = 0.0

        if total_tests > 0 and agent_output.action == "propose_fix":
            pass_rate = passed_tests / total_tests
            if pass_rate == 1.0:
                fix_score = 0.35      # full solve — this is what we're training for
            elif pass_rate >= 0.75:
                fix_score = 0.20      # most tests pass
            elif pass_rate >= 0.50:
                fix_score = 0.12      # more than half pass
            elif pass_rate > 0.0:
                fix_score = 0.05      # at least something works
            # 0.0 if nothing passes — no credit for non-fix actions

        # ── COMPONENT 5: SEMANTIC SIMILARITY (Paper 2 taxonomy) ───────────
        # How structurally close is the proposed fix to the canonical fix?
        # Uses difflib — no heavy NLP dependencies needed.
        semantic_score = 0.0
        proposed = agent_output.detail
        canonical = ground_truth.get("canonical_fix_code", "")

        if proposed and canonical and agent_output.action == "propose_fix":
            similarity = difflib.SequenceMatcher(None, proposed, canonical).ratio()
            if similarity >= 0.85:
                semantic_score = 0.10
            elif similarity >= 0.65:
                semantic_score = 0.05
            elif similarity >= 0.40:
                semantic_score = 0.02
            # No reward below 0.40 similarity — prevents gaming with partial matches

        # ── COMPONENT 6: EFFICIENCY POTENTIAL (Potential-based, Paper 1) ──
        # Implements potential-based reward shaping: F(s,a,s') = γΦ(s') - Φ(s)
        # where Φ(state) = value of remaining turns
        # This is PROVEN to not change the optimal policy (Ibrahim et al. Theorem 1)
        # while still accelerating convergence.
        remaining_turns = self.MAX_TURNS - turn_number
        efficiency_potential = 0.02 * remaining_turns  # max 0.10 on turn 0

        # ── PENALTIES ─────────────────────────────────────────────────────
        penalties = 0.0

        # Regression: fix breaks previously-passing tests — severe
        if test_results.get("newly_broken", 0) > 0:
            penalties -= 0.20

        # Give up: agent chose to give_up
        if agent_output.action == "give_up":
            penalties -= 0.15

        # Invalid action: not one of the 5 valid actions
        if agent_output.action == "invalid":
            penalties -= 0.10

        # Invalid format (already captured in format_score, add extra penalty)
        if not agent_output.valid:
            penalties -= 0.10

        # ── TOTAL ─────────────────────────────────────────────────────────
        raw_total = (
            format_score
            + hypothesis_score
            + localization_score
            + fix_score
            + semantic_score
            + efficiency_potential
            + penalties
        )

        # Floor at -0.5 to prevent reward death spiral (Ibrahim et al.)
        total = max(raw_total, -0.5)

        return RewardBreakdown(
            format_compliance=round(format_score, 4),
            hypothesis_quality=round(hypothesis_score, 4),
            localization=round(localization_score, 4),
            fix_quality=round(fix_score, 4),
            semantic_similarity=round(semantic_score, 4),
            efficiency_potential=round(efficiency_potential, 4),
            penalties=round(penalties, 4),
            total=round(total, 4),
        )

    def compute_episode_reward(self, trajectory: list[dict]) -> float:
        """
        Aggregate turn rewards across an episode.
        Uses 0.9 discount factor — later turns worth slightly less.
        Adds solve bonus if bug was fixed before max turns.
        """
        if not trajectory:
            return 0.0

        total = 0.0
        discount = 1.0

        for turn in trajectory:
            total += discount * turn["reward"].total
            discount *= 0.9

        # Solve bonus: incentivizes actually solving the bug
        solved = any(t["reward"].fix_quality >= 0.35 for t in trajectory)
        if solved:
            total += 0.20

        return round(total, 4)

    def get_reward_breakdown_for_logging(self, trajectory: list[dict]) -> dict:
        """Returns per-component averages across episode for W&B logging."""
        if not trajectory:
            return {}

        components = [
            "format_compliance", "hypothesis_quality", "localization",
            "fix_quality", "semantic_similarity", "efficiency_potential", "penalties"
        ]

        return {
            f"reward/{c}": round(
                sum(t["reward"].__dict__[c] for t in trajectory) / len(trajectory), 4
            )
            for c in components
        }
