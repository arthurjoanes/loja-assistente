from pathlib import Path

import pytest
from scripts.prove_evolution import choose_subnet, source_names


def test_subnet_selection_respects_existing_docker_and_host_routes() -> None:
    assert choose_subnet(["10.203.220.0/24", "172.29.160.0/20"]) == "10.203.221.0/24"
    with pytest.raises(RuntimeError, match="No free"):
        choose_subnet(["10.203.0.0/16"])


def test_freeze_includes_new_source_and_excludes_credential_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "new.py").write_text("print('synthetic')", encoding="utf-8")
    (tmp_path / ".env").write_text("synthetic", encoding="utf-8")
    (tmp_path / ".env.example").write_text("synthetic", encoding="utf-8")
    (tmp_path / "tracked.py").write_text("print('tracked')", encoding="utf-8")
    monkeypatch.setattr(
        "scripts.prove_evolution.subprocess.check_output",
        lambda *args, **kwargs: b"tracked.py\0new.py\0.env\0.env.example\0",
    )
    assert source_names(tmp_path) == ["new.py", "tracked.py"]
