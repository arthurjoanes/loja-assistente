"""Freeze local sources, prove budget/API and demo UI, then remove only this run's resources.

No credentials are copied and the runtime network is internal, with no published ports.
Outputs are private until reviewed; this script does not publish, commit or change the source tree.
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def source_names(root):
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    allowed = {"backend", "frontend", "evals", "data", "scripts"}
    names = []
    for name in sorted(set(result.stdout.decode().split("\0")) - {""}):
        parts = Path(name).parts
        if parts[0] not in allowed and name not in {
            ".dockerignore",
            ".gitattributes",
            "compose.proof.yaml",
        }:
            continue
        if any(
            part.startswith(".env")
            or part
            in {
                ".env",
                "node_modules",
                ".next",
                "__pycache__",
                ".runtime",
                "test-results",
                "playwright-report",
                "local",
            }
            for part in parts
        ):
            continue
        item = root / name
        if item.is_symlink():
            raise RuntimeError("Source symlink refused: " + name)
        if item.is_file():
            names.append(name)
    return names


def verify_owner(info, kind, project, identity):
    labels = (
        info.get("Config", {}).get("Labels", {}) if kind == "container" else info.get("Labels", {})
    )
    if (
        labels.get("com.docker.compose.project") != project
        or labels.get("portfolio.proof") != identity
    ):
        raise RuntimeError("Resource ownership mismatch; refusing cleanup")


def run_proof(
    root, output_parent, deadline_seconds, allow_concurrent_workloads=False, frontend_only=False
):
    identity = uuid4().hex
    project = "pf-la-proof-" + identity[:12]
    output = output_parent.resolve() / identity
    if output.exists() or output_parent.resolve().is_relative_to(root.resolve()):
        raise RuntimeError("Output must be a new directory outside the source repository")
    output.mkdir(parents=True)
    frozen = output / "source"
    artifacts = output / "artifacts"
    for name in (
        "offline-evaluation",
        "screenshots",
        "story",
        "playwright",
        "budget-observations",
    ):
        (artifacts / name).mkdir(parents=True)
    started = time.monotonic()
    deadline = started + deadline_seconds
    cleanup_deadline = None
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("COMPOSE_", "DOCKER_", "OPENAI_", "AZURE_OPENAI_"))
    }
    record = {
        "run_id": identity,
        "project": project,
        "status": "PREPARING",
        "started_at_utc": datetime.now(UTC).isoformat(),
        "deadline_seconds": deadline_seconds,
        "cleanup_margin_seconds": 90,
        "runtime_limits": {
            "db_mib": 512,
            "checks_mib": 1024,
            "ui_backend_mib": 768,
            "frontend_mib": 512,
            "playwright_mib": 1536,
            "workers": 1,
        },
        "network": "internal; no host ports; no paid provider; synthetic credentials only",
        "allow_concurrent_workloads": allow_concurrent_workloads,
        "measurement_scope": "Functional assertions only; no performance or benchmark claim",
        "backend_checks_executed": not frontend_only,
        "validation_scope": "frontend only; no claim of rerunning backend checks"
        if frontend_only
        else "backend and frontend",
        "commands": [],
        "images": {},
    }

    def save():
        write_json(output / "proof.json", record)

    def command(args, *, timeout=300, cleanup=False, cwd=None):
        remaining = (cleanup_deadline if cleanup else deadline) - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("Operational deadline exceeded; cleanup still required")
        index = len(record["commands"])
        log = output / f"command-{index:02d}.log"
        step = {
            "argv": args,
            "phase": record["status"],
            "log": log.name,
            "started_at_utc": datetime.now(UTC).isoformat(),
        }
        record["commands"].append(step)
        save()
        print(f"{record['status']}: {' '.join(args[:8])} [log {log.name}]", flush=True)
        begin = time.monotonic()
        try:
            stream = args[:2] == ["docker", "build"] or (
                args[:2] == ["docker", "compose"]
                and any(part in args for part in ("run", "up", "logs"))
            )
            with log.open("wb") as logfile:
                result = subprocess.run(
                    args,
                    cwd=cwd or frozen,
                    env=environment,
                    stdout=logfile if stream else subprocess.PIPE,
                    stderr=subprocess.STDOUT if stream else subprocess.PIPE,
                    check=False,
                    timeout=min(timeout, remaining),
                )
                if not stream:
                    logfile.write(result.stdout + result.stderr)
            step["returncode"] = result.returncode
            if result.returncode:
                raise RuntimeError(
                    f"Command {index} failed ({result.returncode}); inspect {log.name}"
                )
            return "" if stream else result.stdout.decode("utf-8", errors="replace").strip()
        except subprocess.TimeoutExpired as exc:
            if not stream:
                log.write_bytes((exc.stdout or b"") + (exc.stderr or b""))
            step["timeout"] = True
            raise
        finally:
            step["seconds"] = round(time.monotonic() - begin, 3)
            save()

    def resources():
        found = {}
        for kind, listing in (
            ("container", ["ps", "-aq"]),
            ("network", ["network", "ls", "-q"]),
            ("volume", ["volume", "ls", "-q"]),
        ):
            ids = command(
                [
                    "docker",
                    *listing,
                    "--filter",
                    "label=com.docker.compose.project=" + project,
                ],
                timeout=20,
                cleanup=True,
            ).split()
            for item in ids:
                info = json.loads(
                    command(["docker", kind, "inspect", item], timeout=20, cleanup=True)
                )[0]
                verify_owner(info, kind, project, identity)
            found[kind] = ids
        return found

    compose = [
        "docker",
        "compose",
        "-p",
        project,
        "-f",
        str(frozen / "compose.proof.yaml"),
    ]

    def cleanup_owned(*, final=False):
        nonlocal cleanup_deadline
        if not final:
            cleanup_deadline = time.monotonic() + 90
        record["cleanup_before"] = resources()
        command(
            compose + ["down", "--volumes", "--remove-orphans", "--timeout", "10"],
            timeout=45,
            cleanup=True,
        )
        record["cleanup_after"] = resources()
        if any(record["cleanup_after"].values()):
            raise RuntimeError("Owned resources remain after cleanup")

    runtime_started = False
    try:
        frozen.mkdir()
        names = source_names(root)
        before = {name: digest(root / name) for name in names}
        for name in names:
            target = frozen / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / name, target)
        copied = {name: digest(frozen / name) for name in names}
        if before != copied or before != {name: digest(root / name) for name in names}:
            raise RuntimeError("Source changed during freeze")
        record["source"] = before
        record["source_identity_sha256"] = hashlib.sha256(
            json.dumps(before, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        record["git_head_at_freeze"] = command(["git", "rev-parse", "HEAD"], cwd=root, timeout=15)
        record["active_containers_before"] = command(
            ["docker", "ps", "--format", "{{.ID}} {{.Names}}"], timeout=20
        )
        if record["active_containers_before"] and not allow_concurrent_workloads:
            raise RuntimeError("A running container exists; reserve an idle runtime window first")
        record["status"] = "BUILDING"
        builds = [
            ("backend", "backend/Dockerfile", ".", None),
            ("frontend-checks", "frontend/Dockerfile", "frontend", "checks"),
            ("frontend", "frontend/Dockerfile", "frontend", "runtime"),
            ("e2e", "frontend/Dockerfile.e2e", "frontend", None),
        ]
        for component, dockerfile, context, target in builds:
            tag = project + ":" + component
            args = [
                "docker",
                "build",
                "--progress",
                "plain",
                "-f",
                dockerfile,
                "-t",
                tag,
            ]
            if target:
                args += ["--target", target]
            command(args + [context], timeout=900)
            image_id = command(
                ["docker", "image", "inspect", "--format", "{{.Id}}", tag], timeout=20
            )
            record["images"][component] = image_id
            environment["PROOF_" + component.upper().replace("-", "_") + "_IMAGE"] = image_id
        command(["docker", "image", "inspect", "postgres:17.11-bookworm"], timeout=20)
        db_id = command(
            [
                "docker",
                "image",
                "inspect",
                "--format",
                "{{.Id}}",
                "postgres:17.11-bookworm",
            ],
            timeout=20,
        )
        record["images"]["db"] = db_id
        environment.update(
            PROOF_DB_IMAGE=db_id,
            PROOF_RUN_ID=identity,
            PROOF_OUTPUT_DIR=artifacts.as_posix(),
        )
        command(compose + ["config", "--quiet"], timeout=20)
        runtime_started = True
        if not frontend_only:
            record["status"] = "BACKEND_CHECKS"
            command(compose + ["up", "-d", "--wait", "db"], timeout=100)
            command(
                compose + ["run", "--rm", "--no-deps", "--name", project + "-checks", "checks"],
                timeout=450,
            )
            cleanup_owned()
        record["status"] = "FRONTEND_CHECKS"
        command(
            compose
            + [
                "run",
                "--rm",
                "--no-deps",
                "--name",
                project + "-frontend-checks",
                "frontend-checks",
            ],
            timeout=240,
        )
        record["status"] = "UI_JOURNEYS"
        command(compose + ["up", "-d", "--wait", "frontend"], timeout=180)
        command(
            compose + ["run", "--rm", "--no-deps", "--name", project + "-e2e", "e2e"],
            timeout=600,
        )
        record["status"] = "VALIDATED_CLEANUP_PENDING"
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
        record["status"] = "FAILED"
        record["error"] = str(error)
    finally:
        if runtime_started:
            cleanup_deadline = time.monotonic() + 90
            try:
                command(compose + ["logs", "--no-color"], timeout=20, cleanup=True)
            except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
                record["log_collection_error"] = str(error)
            try:
                cleanup_owned(final=True)
            except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
                record["cleanup_error"] = str(error)
                record["status"] = "FAILED"
        if not runtime_started:
            cleanup_deadline = time.monotonic() + 20
        try:
            record["active_containers_after"] = command(
                ["docker", "ps", "--format", "{{.ID}} {{.Names}}"], timeout=20, cleanup=True
            )
        except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
            record["active_containers_after_error"] = str(error)
        if "source" in record:
            record["frozen_source_unchanged"] = all(
                (frozen / name).is_file() and digest(frozen / name) == value
                for name, value in record["source"].items()
            )
            record["original_source_changed_names"] = [
                name
                for name, value in record["source"].items()
                if not (root / name).is_file() or digest(root / name) != value
            ]
            record["original_source_added_names"] = sorted(
                set(source_names(root)) - set(record["source"])
            )
            if not record["frozen_source_unchanged"]:
                record["status"] = "FAILED"
        if record["status"] == "VALIDATED_CLEANUP_PENDING":
            record["status"] = "PASSED"
        record["elapsed_seconds"] = round(time.monotonic() - started, 3)
        record["finished_at_utc"] = datetime.now(UTC).isoformat()
        save()
        print(
            json.dumps(
                {
                    "run_id": identity,
                    "status": record["status"],
                    "record": str(output / "proof.json"),
                }
            ),
            flush=True,
        )
    return 0 if record["status"] == "PASSED" else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--frontend-only",
        action="store_true",
        help="Skip backend checks after an independently recorded pass; never reports them as rerun",
    )
    parser.add_argument(
        "--allow-concurrent-workloads",
        action="store_true",
        help="Explicit functional-only run alongside recorded foreign containers; never stops them",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Private directory outside the repository",
    )
    parser.add_argument(
        "--deadline",
        type=int,
        default=2400,
        help="Operational seconds; cleanup has a separate 90-second margin",
    )
    args = parser.parse_args()
    if not 60 <= args.deadline <= 3600:
        parser.error("deadline must be 60..3600 seconds")
    raise SystemExit(
        run_proof(
            Path(__file__).resolve().parents[1],
            args.output,
            args.deadline,
            args.allow_concurrent_workloads,
            args.frontend_only,
        )
    )
