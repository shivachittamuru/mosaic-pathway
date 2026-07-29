from typing import Any

import pytest

from mosaic_pathway.app_support import (
    ERROR_KEY,
    RESULT_KEY,
    GenerationError,
    clear_error,
    clear_pathway,
    read_output_view,
    store_error,
    store_result,
)


@pytest.fixture
def state() -> dict[str, Any]:
    return {}


def test_empty_state_asks_for_the_placeholder(state: dict[str, Any]) -> None:
    view = read_output_view(state)

    assert view.show_placeholder
    assert not view.shows_previous_result
    assert view.result is None
    assert view.error is None


def test_stored_result_replaces_the_placeholder(state: dict[str, Any]) -> None:
    store_result(state, "pathway")  # type: ignore[arg-type]

    view = read_output_view(state)

    assert not view.show_placeholder
    assert view.result == "pathway"
    assert view.error is None


def test_a_new_result_clears_the_previous_error(state: dict[str, Any]) -> None:
    store_error(state, "Something failed.", ValueError("boom"))
    store_result(state, "pathway")  # type: ignore[arg-type]

    assert ERROR_KEY not in state


def test_a_failure_keeps_the_previous_result(state: dict[str, Any]) -> None:
    store_result(state, "pathway")  # type: ignore[arg-type]
    store_error(state, "Something failed.", ValueError("boom"))

    view = read_output_view(state)

    assert view.shows_previous_result
    assert view.result == "pathway"
    assert view.error == GenerationError(
        message="Something failed.", detail="ValueError: boom"
    )


def test_a_first_failure_shows_no_previous_result(state: dict[str, Any]) -> None:
    store_error(state, "Something failed.", ValueError("boom"))

    view = read_output_view(state)

    assert not view.show_placeholder
    assert not view.shows_previous_result
    assert view.result is None


def test_clear_error_keeps_the_result(state: dict[str, Any]) -> None:
    store_result(state, "pathway")  # type: ignore[arg-type]
    store_error(state, "Something failed.", ValueError("boom"))

    clear_error(state)

    assert state[RESULT_KEY] == "pathway"
    assert ERROR_KEY not in state


def test_clear_pathway_removes_result_and_error(state: dict[str, Any]) -> None:
    store_result(state, "pathway")  # type: ignore[arg-type]
    store_error(state, "Something failed.", ValueError("boom"))

    clear_pathway(state)

    assert read_output_view(state).show_placeholder


def test_clearing_an_empty_state_is_safe(state: dict[str, Any]) -> None:
    clear_error(state)
    clear_pathway(state)

    assert state == {}
