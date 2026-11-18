"""Validate that the hand-in matches the institutional PAIII criterion structure.

The source workbook is kept outside git. This test validates the public
criterion-to-evidence map, not a score assigned by the institution.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "docs/RUBRICA_OFICIAL_PAIII_2026.md"
CODES = [
    "R6.1-Cr1", "R6.1-Cr2", "R6.1-Cr3", "R6.1-Cr4",
    "R6.2-Cr5", "R6.2-Cr6", "R6.2-Cr7", "R6.2-Cr8",
    "RA1-F1", "RA1-F2", "RA1-F3", "RA1-F4", "RA1-F5",
    "RA1-Referencias", "RA2-F1", "RA2-F2", "RA2-F3", "RA2-F4",
    "RA2-F5", "RA2-F6", "RA2-F7", "R7.1-Cr1", "R7.1-Cr2",
    "R7.1-Cr3", "R7.2-Cr4", "R7.2-Cr5", "R7.2-Cr6",
]


def test_all_27_official_criteria_have_one_public_evidence_mapping():
    text = MATRIX.read_text(encoding="utf-8")
    table_rows = [line for line in text.splitlines() if line.startswith("| ") and " | " in line]
    for code in CODES:
        found = [r for r in table_rows if r.startswith(f"| {code} |")]
        assert len(found) == 1, (code, len(found))
        cells = [p.strip() for p in found[0].strip("|").split("|")]
        assert len(cells) == 6, (code, cells)
        assert len(cells[2]) > 25, code  # institutional Level 4 descriptor
        assert cells[4] in {"PARCIAL", "DEMOSTRADO CON LIMITACIONES", "REQUIERE EVALUACIÓN HUMANA"}
        for ref in cells[3].split(";"):
            assert (ROOT / ref.strip()).exists(), (code, ref)


def test_no_grade_is_claimed_and_external_rubric_is_not_tracked():
    body = MATRIX.read_text(encoding="utf-8")
    assert "no concede nivel 4" in body
    assert not (ROOT / "Rubrica_PAIII_2026(2).xlsx").exists()
