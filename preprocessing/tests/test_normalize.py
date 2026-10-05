from finsupplykg.normalize import (
    deduplicate_paragraphs,
    normalize_text,
)

def test_removes_exact_duplicate_long_paragraph():
    paragraph = (
        "NVIDIA relies on third-party manufacturers and suppliers "
        "for several important parts of its semiconductor supply chain."
    )

    text = f"{paragraph}\n\n{paragraph}"

    result = deduplicate_paragraphs(text)

    assert result == paragraph


def test_keeps_short_repeated_text():
    text = "Risk Factors\n\nRisk Factors"

    result = deduplicate_paragraphs(text)

    assert result == text


def test_keeps_similar_but_different_paragraphs():
    paragraph_one = (
        "NVIDIA relies on third-party manufacturers and suppliers "
        "for several important parts of its semiconductor supply chain."
    )

    paragraph_two = (
        "NVIDIA relies on third-party manufacturers and suppliers "
        "for several important parts of its global supply chain."
    )

    text = f"{paragraph_one}\n\n{paragraph_two}"

    result = deduplicate_paragraphs(text)

    assert result == text

def test_removes_filing_page_header():
    text = (
        "The Company relies on several suppliers.\n"
        "Apple Inc. | 2025 Form 10-K | 22\n"
        "These suppliers manufacture components."
    )

    result = normalize_text(text)

    assert "Apple Inc. | 2025 Form 10-K | 22" not in result
    assert "The Company relies on several suppliers." in result
    assert "These suppliers manufacture components." in result