import hashlib
import json
from pathlib import Path

import pytest
from scripts import verify_evidence as verifier


def dump(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value) + "\n", encoding="utf-8", newline="\n")


@pytest.fixture
def historical(tmp_path):
    source = "backend/src/historical.py"
    contents = {
        source: "# avaliação histórica\r\nvalue = 1\r\n".encode(),
        "evals/cases/development-v1.json": b'{"development": true}\n',
        "evals/cases/final-v1.json": b'{"final": true}\n',
    }
    hashes = {name: hashlib.sha256(data).hexdigest() for name, data in contents.items()}
    freeze = {
        "source": {source: hashes[source]},
        "development_sha256": hashes["evals/cases/development-v1.json"],
        "final_sha256": hashes["evals/cases/final-v1.json"],
    }
    dump(tmp_path / verifier.HISTORICAL_FREEZE, freeze)
    manifest = {
        "version": 1,
        "kind": "historical-evaluation-snapshot",
        "freeze_file": verifier.HISTORICAL_FREEZE,
        "snapshot_root": verifier.HISTORICAL_ROOT,
        "evaluation_runs": list(verifier.RUNS),
        "freeze_sha256": hashlib.sha256(
            (tmp_path / verifier.HISTORICAL_FREEZE).read_bytes()
        ).hexdigest(),
        "origin": {"method": "git archive", "recovery_commit": verifier.RECOVERY_COMMIT},
        "files": {},
    }
    for name, content in contents.items():
        for base in (tmp_path, tmp_path / verifier.HISTORICAL_ROOT):
            destination = base / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
        manifest["files"][name] = {
            "sha256": hashes[name],
            "bytes": len(content),
            "git_blob_sha1": hashlib.sha1(f"blob {len(content)}\0".encode() + content).hexdigest(),
        }
    dump(tmp_path / verifier.HISTORICAL_MANIFEST, manifest)
    return tmp_path, freeze, manifest, source


def test_historical_bytes_verified_independently_and_workspace_drift_is_explicit(historical):
    root, freeze, _, source = historical
    assert verifier.verify_historical_sources(root, freeze)["changed_or_missing_frozen_paths"] == []
    (root / source).write_text("value = 2\n", encoding="utf-8")
    (root / "backend/src/new_budget.py").write_text("value = 3\n", encoding="utf-8")
    report = verifier.verify_historical_sources(root, freeze)
    assert report == {
        "snapshot_files": 3,
        "changed_or_missing_frozen_paths": [source],
        "new_python_paths_in_frozen_scope": ["backend/src/new_budget.py"],
    }


@pytest.mark.parametrize("mutation", ["append", "normalize_newlines"])
def test_changed_historical_bytes_fail_even_when_workspace_still_matches(historical, mutation):
    root, freeze, _, source = historical
    path = root / verifier.HISTORICAL_ROOT / source
    content = path.read_bytes()
    path.write_bytes(
        content + b"# changed\n" if mutation == "append" else content.replace(b"\r\n", b"\n")
    )
    with pytest.raises(ValueError, match="Historical SHA-256 mismatch"):
        verifier.verify_historical_sources(root, freeze)


@pytest.mark.parametrize("mutation", ["missing", "extra"])
def test_exact_snapshot_inventory_and_no_fallback(historical, mutation):
    root, freeze, _, source = historical
    base = root / verifier.HISTORICAL_ROOT
    if mutation == "missing":
        (base / source).unlink()
    else:
        (base / "extra.py").write_text("not frozen\n", encoding="utf-8")
    with pytest.raises(ValueError, match="file inventory differs"):
        verifier.verify_historical_sources(root, freeze)


@pytest.mark.parametrize(
    "field,value", [("kind", "current-workspace"), ("snapshot_root", "../outside")]
)
def test_explicit_historical_association_cannot_redirect_snapshot(historical, field, value):
    root, freeze, manifest, _ = historical
    manifest[field] = value
    dump(root / verifier.HISTORICAL_MANIFEST, manifest)
    with pytest.raises(ValueError, match="association differs"):
        verifier.verify_historical_sources(root, freeze)


@pytest.mark.parametrize("field", ["sha256", "git_blob_sha1"])
def test_manifest_cannot_relabel_a_digest_or_git_blob(historical, field):
    root, freeze, manifest, source = historical
    manifest["files"][source][field] = "0" * len(manifest["files"][source][field])
    dump(root / verifier.HISTORICAL_MANIFEST, manifest)
    with pytest.raises(ValueError, match="digest differs|Git blob identity differs"):
        verifier.verify_historical_sources(root, freeze)


def test_association_requires_the_exact_original_freeze(historical):
    root, freeze, manifest, _ = historical
    manifest["freeze_sha256"] = "0" * 64
    dump(root / verifier.HISTORICAL_MANIFEST, manifest)
    with pytest.raises(ValueError, match="freeze identity differs"):
        verifier.verify_historical_sources(root, freeze)


def test_missing_manifest_never_falls_back_to_workspace(historical):
    root, freeze, _, _ = historical
    (root / verifier.HISTORICAL_MANIFEST).unlink()
    with pytest.raises(FileNotFoundError):
        verifier.verify_historical_sources(root, freeze)
