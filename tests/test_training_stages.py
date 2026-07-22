"""Unit tests for `curriculum_stages`, the fix for the curriculum-never-advances bug.

`agentdebugger.training.grpo.train()` used to swap `trainer.train_dataset` from a
`TrainerCallback` mid-run. TRL/transformers builds the train sampler exactly once
per `Trainer.train()` call and caches `len(dataset)` at construction time, so that
swap never actually reached the sampler: the bug pool silently never grew past
tier 1 for the whole run, no matter what the curriculum schedule said. The fix is
to run one short `GRPOTrainer` per curriculum stage instead. `curriculum_stages`
is the pure step-range arithmetic behind that; it needs no GPU/torch/trl to test.
"""

from __future__ import annotations

from itertools import pairwise

from agentdebugger.config import DEFAULT_CURRICULUM, CurriculumSchedule, CurriculumStage
from agentdebugger.training.grpo import curriculum_stages


def test_default_schedule_splits_a_full_run_into_three_stages():
    assert curriculum_stages(DEFAULT_CURRICULUM, max_steps=500) == [(0, 150), (150, 350), (350, 500)]


def test_a_short_calibration_run_never_reaches_the_first_boundary():
    # `--max-steps 20` for a calibration run: entirely inside tier-1-only territory.
    assert curriculum_stages(DEFAULT_CURRICULUM, max_steps=20) == [(0, 20)]


def test_a_run_that_stops_exactly_on_a_boundary_does_not_emit_an_empty_stage():
    assert curriculum_stages(DEFAULT_CURRICULUM, max_steps=150) == [(0, 150)]


def test_a_run_that_stops_just_past_a_boundary_gets_a_short_final_stage():
    assert curriculum_stages(DEFAULT_CURRICULUM, max_steps=151) == [(0, 150), (150, 151)]


def test_stages_are_contiguous_and_cover_the_whole_run():
    stages = curriculum_stages(DEFAULT_CURRICULUM, max_steps=500)
    assert stages[0][0] == 0
    assert stages[-1][1] == 500
    for (_, end), (next_start, _) in pairwise(stages):
        assert end == next_start


def test_single_stage_schedule_never_splits():
    schedule = CurriculumSchedule(stages=(CurriculumStage(start_step=0, tiers=(1, 2, 3)),))
    assert curriculum_stages(schedule, max_steps=500) == [(0, 500)]


def test_every_stage_reports_the_correct_active_tiers():
    stages = curriculum_stages(DEFAULT_CURRICULUM, max_steps=500)
    tiers_per_stage = [DEFAULT_CURRICULUM.tiers_at(start) for start, _ in stages]
    assert tiers_per_stage == [(1,), (1, 2), (1, 2, 3)]
