from finsupplykg.chunk import window_sentences
from finsupplykg.config import SECTIONS_10K, SECTIONS_20F
from finsupplykg.normalize import normalize_text
from finsupplykg.regex_slicer import slice_section


def test_normalize_strips_sec_artifacts():
    raw = "ITEM 4. Supply​ chain non‑breaking ﬁrm’s"
    assert normalize_text(raw) == "ITEM 4. Supply chain non-breaking firm's"


def test_regex_slicer_skips_toc_and_stops_at_next_item():
    body_1a = "The risks below could harm us. We depend on TSMC for wafers. " * 20
    text = normalize_text(
        "Table of Contents\nItem 1. Business 3\nItem 1A. Risk Factors 10\nItem 1B. Unresolved 20\n\n"
        "Item 1. Business\nWe design GPUs.\n\n"
        f"Item 1A. Risk Factors\n{body_1a}\n\n"
        "Item 1B. Unresolved Staff Comments\nNone.\n"
    )
    risk = slice_section(text, SECTIONS_10K[1], SECTIONS_10K)
    assert risk.startswith("Item 1A. Risk Factors")
    assert "TSMC" in risk and "Unresolved" not in risk
    business = slice_section(text, SECTIONS_10K[0], SECTIONS_10K)
    assert "GPUs" in business and "Risk Factors" not in business


def test_regex_slicer_title_only_headings():
    # Intel-style layout: headings without "Item N" prefixes.
    text = normalize_text(
        "Risk Factors\nWe rely on ASML lithography tools. More risk text here.\n\n"
        "Properties\nOur fabs are in Oregon.\n"
    )
    risk = slice_section(text, SECTIONS_10K[1], SECTIONS_10K)
    assert "ASML" in risk and "Oregon" not in risk


def test_regex_slicer_toc_page_numbers_are_boundaries():
    # Intel-style TOC: "Risk Factors 31" must end the TOC's MD&A entry, so the body copy wins.
    mdna_body = "Revenue declined due to lower demand. " * 30
    text = normalize_text(
        "Management's Discussion and Analysis\nRisk Factors 31\nProperties 8, 49\n\n"
        f"Management's Discussion and Analysis\n{mdna_body}\n\n"
        "Risk Factors\nWe depend on suppliers. " + "Risk text. " * 200
    )
    mdna = slice_section(text, SECTIONS_10K[2], SECTIONS_10K)
    assert "Revenue declined" in mdna and "suppliers" not in mdna


def test_normalize_drops_consecutive_duplicate_lines():
    assert normalize_text("Header\nHeader\nHeader\nBody\n\nBody") == "Header\nBody"


def test_regex_slicer_20f():
    text = normalize_text(
        "ITEM 4. INFORMATION ON THE COMPANY\nWe manufacture for Apple and NVIDIA.\n\n"
        "ITEM 4A. UNRESOLVED STAFF COMMENTS\nNone.\n"
    )
    biz = slice_section(text, SECTIONS_20F[1], SECTIONS_20F)
    assert "NVIDIA" in biz and "UNRESOLVED" not in biz


def test_window_overlap():
    sents = [f"s{i} w w w w" for i in range(30)]  # 5 words each
    windows = window_sentences(sents, max_words=50, overlap=7)  # 10 sentences per window
    assert windows[0] == sents[:10]
    assert windows[1][:7] == sents[3:10]  # last 7 sentences repeated
    assert windows[-1][-1] == sents[-1]
    assert all(len(" ".join(w).split()) <= 50 for w in windows)


def test_window_overlap_always_advances():
    sents = ["x " * 100] * 5  # each sentence alone exceeds the budget
    windows = window_sentences(sents, max_words=50, overlap=7)
    assert len(windows) == 5
