import json
from types import SimpleNamespace

import pytest
from scripts import prove_budget_ui as proof


def test_freeze_includes_untracked_fixture_and_excludes_environment_and_outputs(
    tmp_path, monkeypatch
):
    names = [
        "backend/src/new.py",
        "data/new.csv",
        "frontend/.env.local",
        "frontend/.env.production",
        "frontend/test-results/secrets.txt",
        "docs/demo.md",
        "scripts/prove_budget_ui.py",
        "compose.proof.yaml",
    ]
    for name in names:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("fixture", encoding="utf-8")
    monkeypatch.setattr(
        proof.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(stdout="\0".join(names).encode()),
    )
    assert proof.source_names(tmp_path) == sorted(
        [
            "backend/src/new.py",
            "data/new.csv",
            "scripts/prove_budget_ui.py",
            "compose.proof.yaml",
        ]
    )


@pytest.mark.parametrize("kind", ["container", "network", "volume"])
def test_cleanup_requires_both_exact_owner_labels(kind):
    labels = {"com.docker.compose.project": "ours", "portfolio.proof": "run"}

    def wrap(values):
        return {"Config": {"Labels": values}} if kind == "container" else {"Labels": values}

    proof.verify_owner(wrap(labels), kind, "ours", "run")
    for key in labels:
        with pytest.raises(RuntimeError, match="ownership"):
            proof.verify_owner(wrap({**labels, key: "other"}), kind, "ours", "run")


def test_active_foreign_container_refuses_before_build_and_never_cleans(tmp_path, monkeypatch):
    root, output = tmp_path / "repo", tmp_path / "private"
    root.mkdir()
    (root / "compose.proof.yaml").write_text("services: {}\n", encoding="utf-8")
    seen = []

    def fake(args, **kwargs):
        seen.append(args)
        if args[:2] == ["git", "ls-files"]:
            value = "compose.proof.yaml\0"
        elif args[:2] == ["git", "rev-parse"]:
            value = "a" * 40
        elif args[:2] == ["docker", "ps"]:
            value = "foreign-id foreign-container"
        else:
            raise AssertionError("Unexpected command: " + str(args))
        return SimpleNamespace(returncode=0, stdout=value.encode(), stderr=b"")

    monkeypatch.setattr(proof.subprocess, "run", fake)
    assert proof.run_proof(root, output, 60) == 1
    record = json.loads(next(output.glob("*/proof.json")).read_text(encoding="utf-8"))
    assert record["status"] == "FAILED" and "running container" in record["error"]
    assert not any("build" in args or "down" in args for args in seen)
