"""Verify the published evidence using only local files and the Python standard library."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/evidence"
RUNS = (
    "20260921T121119Z-883376fa",
    "20260921T121149Z-c53a402a",
    "20260921T121255Z-a9c11d1f",
)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def verify_hash(relative: str, expected: str) -> None:
    path = (ROOT / relative).resolve()
    require(path.is_relative_to(ROOT), "Manifest path escapes the repository")
    require(path.is_file(), f"Missing evidence/source: {relative}")
    require(hashlib.sha256(path.read_bytes()).hexdigest() == expected, f"SHA-256 mismatch: {relative}")


def main() -> None:
    manifest = read_json(EVIDENCE / "publication-manifest.json")
    for relative, digest in manifest["artifacts"].items():
        verify_hash(relative, digest)

    freeze = read_json(EVIDENCE / "azure-live/freeze-azure-luna-r1.json")
    for relative, digest in freeze["source"].items():
        verify_hash(relative, digest)
    verify_hash("evals/cases/development-v1.json", freeze["development_sha256"])
    verify_hash("evals/cases/final-v1.json", freeze["final_sha256"])

    totals = {"calls": 0, "input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    cost = Decimal(0)
    seen_calls: set[str] = set()
    final_summary = None
    for run_id in RUNS:
        directory = ROOT / "evals/reports" / run_id
        summary = read_json(directory / "summary.json")
        rows = [json.loads(line) for line in (directory / "cases.jsonl").read_text(encoding="utf-8-sig").splitlines() if line.strip()]
        require(summary["run_id"] == run_id and summary["exit_code"] == 0, f"Run failed: {run_id}")
        require(summary["source"] == freeze["source"], f"Run source differs: {run_id}")
        require(summary["source_and_cases_unchanged"], f"Run reports source changes: {run_id}")
        expected_case_hash = freeze["final_sha256"] if summary["stage"] == "final" else freeze["development_sha256"]
        require(summary["case_sha256"] == expected_case_hash, f"Case set differs: {run_id}")
        for mode, metrics in summary["summaries"].items():
            subset = [row for row in rows if row["mode"] == mode]
            require(len(subset) == metrics["executed"], f"Execution count differs: {run_id}/{mode}")
            require(sum(row["assessment"]["passed"] for row in subset) == metrics["passed"], f"Pass count differs: {run_id}/{mode}")
            require(len({(row["id"], row["repetition"]) for row in subset}) == len(subset), f"Duplicate case: {run_id}/{mode}")
            if mode == "llm":
                require(sum(bool(row["provider"]) for row in subset) == metrics["provider_invoked_cases"], f"Provider count differs: {run_id}")
                require(sum(not row["provider"] for row in subset) == metrics["local_guard_cases"], f"Guard count differs: {run_id}")
        calls = [call for row in rows for call in row["provider"]]
        require(len(calls) == summary["live_model_calls"], f"Call count differs: {run_id}")
        for call in calls:
            require(call["call_id"] not in seen_calls, "Duplicate provider call across runs")
            seen_calls.add(call["call_id"])
            require(call["status"] == "completed" and call["attempts"] == 1, f"Unexpected provider status: {run_id}")
            require(bool(call["provider_request_id"]) and bool(call["response_id"]), f"Missing provider IDs: {run_id}")
            require(call["input_tokens"] + call["output_tokens"] == call["total_tokens"], f"Token arithmetic differs: {run_id}")
        for key in ("input_tokens", "output_tokens", "total_tokens"):
            actual = sum(call[key] for call in calls)
            require(actual == summary["measured_usage"][key], f"Usage differs: {run_id}/{key}")
            totals[key] += actual
        require(summary["measured_usage"]["unknown_usage_calls"] == 0, f"Unknown usage: {run_id}")
        stage_cost = (Decimal(sum(call["input_tokens"] for call in calls)) * Decimal("0.25") + Decimal(sum(call["output_tokens"] for call in calls)) * Decimal("1.20")) / Decimal(1000000)
        require(stage_cost == Decimal(summary["estimated_known_usage_usd"]), f"Estimated cost differs: {run_id}")
        cost += stage_cost
        totals["calls"] += len(calls)
        if summary["stage"] == "final":
            final_summary = summary
            llm = [row for row in rows if row["mode"] == "llm"]
            require(len({row["id"] for row in llm}) == 24 and len(llm) == 48, "Final sample differs")
            failures = [(row["id"], row["repetition"]) for row in llm if not row["assessment"]["passed"]]
            require(failures == [("final-bf-04", 2)], "Preserved final failure differs")
            for row in llm:
                require(not any(row["assessment"][key] for key in ("authorization_violation", "unsafe_acceptance", "financial_divergence")), "Critical final failure")

    require(final_summary is not None and final_summary["status"] == "live_final_approved", "Final approval missing")
    require(totals == {"calls": 55, "input_tokens": 45307, "output_tokens": 3481, "total_tokens": 48788}, "Aggregate consumption differs")
    require(cost == Decimal("0.01550395"), "Aggregate estimated cost differs")
    subprocess.run([sys.executable, "-X", "utf8", str(ROOT / "scripts/render_evidence.py"), "--check"], cwd=ROOT, check=True)
    print(f"OK: {len(manifest['artifacts'])} evidence hashes; {len(freeze['source'])} frozen source files; 2 case sets.")
    metrics = final_summary["summaries"]
    counts = "; ".join(f"{mode} {metrics[mode]['passed']}/{metrics[mode]['executed']}" for mode in ("llm", "demo", "structured"))
    print(f"OK: {counts}; preserved failure final-bf-04 repetition 2.")
    print(f"OK: {totals['calls']} Azure calls; {totals['total_tokens']} tokens; estimated USD {cost} (not an invoice).")
    print("Offline file verification only; no Azure calls, database queries or semantic re-evaluation.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as exc:
        print(f"Evidence verification failed: {exc}", file=sys.stderr)
        sys.exit(1)
