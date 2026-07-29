import json
from pathlib import Path

import pytest

from mosaic_pathway.slice4_evaluation import CASES_DIR, load_cases

EXPECTED_CASE_IDS = {
    "college-exploration",
    "educator-parent-unlearning",
    "gentle-transition",
    "limited-time-and-budget",
    "neurodivergent-teen-autonomy",
    "recovery-from-school-harm",
}


def test_shipped_cases_are_valid_and_cover_every_scenario() -> None:
    cases = load_cases()

    assert {case.case_id for case in cases} == EXPECTED_CASE_IDS
    assert [case.case_id for case in cases] == sorted(case.case_id for case in cases)
    assert all(case.intake.children for case in cases)


def test_case_ids_match_their_filenames() -> None:
    for case in load_cases():
        assert (CASES_DIR / f"{case.case_id}.json").is_file()


def test_duplicate_case_ids_are_rejected(tmp_path: Path) -> None:
    payload = json.loads((CASES_DIR / "gentle-transition.json").read_text("utf-8"))

    for name in ("first.json", "second.json"):
        (tmp_path / name).write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="Duplicate case IDs"):
        load_cases(tmp_path)


def test_a_missing_directory_raises_a_setup_error(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="was not found"):
        load_cases(tmp_path / "absent")


def test_an_empty_directory_raises_a_setup_error(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="No evaluation cases"):
        load_cases(tmp_path)
