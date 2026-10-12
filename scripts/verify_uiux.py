"""Verify the paired UI/UX receipt without Docker, credentials or network."""

import hashlib
import json
from pathlib import Path


def verify(root: Path) -> None:
    evidence = root / "docs/evidence/uiux-20261012"
    receipt = json.loads((evidence / "index.json").read_text(encoding="utf-8"))
    for name, expected in receipt["files"].items():
        target = (root / name).resolve()
        if not target.is_relative_to(root.resolve()):
            raise ValueError("Artifact outside repository")
        actual = hashlib.sha256(target.read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f"Artifact hash mismatch: {name}")
    for name, expected in receipt["runtime_sources"].items():
        actual = hashlib.sha256((root / name).read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f"Runtime source changed: {name}")
    before = json.loads((evidence / "before-chromium-report.json").read_text())
    after = json.loads((evidence / "after-chromium-report.json").read_text())
    widths = {320, 390, 768, 1024, 1440}
    for report in (before, after):
        if report["status"] != "captured" or report["paid_calls"] != 0:
            raise ValueError("Incomplete capture or paid-provider execution")
        if len(report["states"]) != 25:
            raise ValueError("Expected five states at five widths")
        if {state["width"] for state in report["states"]} != widths:
            raise ValueError("Viewport matrix changed")
    previous = {row["width"]: row for row in before["journeys"] if "result" in row}
    current = {row["width"]: row for row in after["journeys"] if "result" in row}
    if previous != current:
        raise ValueError("Paired domain data, plans or fixtures differ")
    for state in after["states"]:
        if state["metrics"]["horizontal_overflow"]:
            raise ValueError("Candidate has global horizontal overflow")
        if state["axe_summary"]["violations"]:
            raise ValueError("Candidate has automatic accessibility violations")
    probe = next(row for row in after["journeys"] if "radio_visible" in row)
    if not probe["radio_visible"] or not probe["confirm_visible"]:
        raise ValueError("Clarification hidden by collapsed editor")
    print("UI/UX receipt verified: paired domain data, 25 states, hashes and visible clarification")


if __name__ == "__main__":
    verify(Path(__file__).resolve().parents[1])
