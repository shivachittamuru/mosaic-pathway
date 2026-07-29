from mosaic_pathway.cleaning import (
    clean_paragraphs,
    is_noise_line,
    normalize_whitespace,
    remove_consecutive_duplicates,
)


def test_normalize_whitespace_collapses_runs_and_newlines() -> None:
    assert normalize_whitespace("  Trust\n\tthe   process \xa0 ") == "Trust the process"


def test_clean_paragraphs_removes_blank_paragraphs() -> None:
    assert clean_paragraphs(["", "   ", "Real content here"]) == ["Real content here"]


def test_known_noise_lines_are_removed() -> None:
    paragraphs = [
        "Home",
        "Log in",
        "Privacy Policy",
        "We use cookies to improve your experience.",
        "© 2024 Mosaic",
        "Page 3 of 12",
        "Families learn at their own pace.",
    ]

    assert clean_paragraphs(paragraphs) == ["Families learn at their own pace."]


def test_useful_short_headings_are_preserved() -> None:
    paragraphs = ["Deschooling", "Rhythms", "Why It Works", "Getting Started"]

    assert clean_paragraphs(paragraphs) == paragraphs


def test_is_noise_line_ignores_case_and_trailing_punctuation() -> None:
    assert is_noise_line("SIGN UP")
    assert is_noise_line("Read more.")
    assert not is_noise_line("Reading together")


def test_remove_consecutive_duplicates_keeps_later_repeats() -> None:
    paragraphs = [
        "A repeated line",
        "A repeated line",
        "Another line",
        "A repeated line",
    ]

    assert remove_consecutive_duplicates(paragraphs) == [
        "A repeated line",
        "Another line",
        "A repeated line",
    ]


def test_clean_paragraphs_removes_consecutive_duplicates_after_normalization() -> None:
    paragraphs = ["Trust   the process", "Trust the process", "A different thought"]

    assert clean_paragraphs(paragraphs) == ["Trust the process", "A different thought"]
