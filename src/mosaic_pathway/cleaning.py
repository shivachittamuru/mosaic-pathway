"""Deterministic cleaning of extracted source paragraphs."""

import re

WHITESPACE_PATTERN = re.compile(r"\s+")

# Exact (case-insensitive) lines that are navigation, login, cookie, or footer
# chrome from the website export. Keep this list explicit and easy to edit.
NOISE_LINES: frozenset[str] = frozenset(
    {
        "about",
        "about us",
        "accept",
        "accept all",
        "accept all cookies",
        "accept cookies",
        "back to top",
        "blog",
        "contact",
        "contact us",
        "cookie policy",
        "cookie preferences",
        "cookie settings",
        "facebook",
        "follow us",
        "home",
        "instagram",
        "linkedin",
        "log in",
        "log out",
        "login",
        "logout",
        "manage cookies",
        "menu",
        "my account",
        "newsletter",
        "next",
        "previous",
        "privacy policy",
        "read more",
        "register",
        "search",
        "share this",
        "sign in",
        "sign up",
        "skip to content",
        "skip to main content",
        "subscribe",
        "terms and conditions",
        "terms of service",
        "terms of use",
        "twitter",
        "youtube",
    }
)

# Footer and pagination lines that vary slightly between pages.
NOISE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^page \d+( of \d+)?$"),
    re.compile(r"^\d+\s*/\s*\d+$"),
    re.compile(r"^(copyright\s+)?(©|\(c\))\s*\d{4}.*$"),
    re.compile(r"^all rights reserved\.?$"),
    re.compile(r"^we use cookies\b.*$"),
)


def normalize_whitespace(text: str) -> str:
    """Collapse all whitespace runs into single spaces and trim the result."""

    return WHITESPACE_PATTERN.sub(" ", text.replace("\xa0", " ")).strip()


def is_noise_line(text: str) -> bool:
    """Return whether a normalized paragraph is known navigation or footer noise."""

    candidate = text.casefold().strip(" .|·—–-")

    if candidate in NOISE_LINES:
        return True

    return any(pattern.match(candidate) for pattern in NOISE_PATTERNS)


def remove_consecutive_duplicates(paragraphs: list[str]) -> list[str]:
    """Drop paragraphs that repeat the paragraph immediately before them."""

    result: list[str] = []

    for paragraph in paragraphs:
        if result and paragraph == result[-1]:
            continue

        result.append(paragraph)

    return result


def clean_paragraphs(paragraphs: list[str]) -> list[str]:
    """Normalize, filter, and de-duplicate raw extracted paragraphs."""

    normalized = [normalize_whitespace(paragraph) for paragraph in paragraphs]
    kept = [
        paragraph
        for paragraph in normalized
        if paragraph and not is_noise_line(paragraph)
    ]

    return remove_consecutive_duplicates(kept)
