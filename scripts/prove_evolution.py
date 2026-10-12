"""Build a private frozen candidate and verify it in an isolated Compose project.

Run only after all source writers have stopped. No source binds, paid provider,
shared screenshot destinations, host ports, or changes to existing Docker resources.
"""

import argparse
import hashlib
import ipaddress
import json
import os
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_names(root):
    output = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=root,
    )
    names = sorted(set(output.decode().split("\0")) - {""})
    if any((root / name).is_symlink() for name in names):
        raise RuntimeError("Source symlink refused; freeze regular files only")
    return [
        name
        for name in names
        if (root / name).is_file()
        and not any(part.startswith(".env") for part in Path(name).parts)
        and not (root / name).is_symlink()
    ]


def choose_subnet(prefixes):
    occupied = [ipaddress.ip_network(value, strict=False) for value in prefixes]
    for third in range(220, 250):
        candidate = ipaddress.ip_network(f"10.203.{third}.0/24")
        if all(
            not candidate.overlaps(network)
            for network in occupied
            if network.version == 4
        ):
            return str(candidate)
    raise RuntimeError("No free inspected subnet; no Docker daemon changes allowed")


def run(root, output_parent, scan_images=True):
    identity = uuid4().hex[:12]
    project = "pf-loja-assistente-evolucao-20261012-" + identity
    output = output_parent.resolve() / identity
    if output.exists():
        raise RuntimeError("Output directory already exists")
    output.mkdir(parents=True)
    frozen = output / "source"
    artifacts = output / "artifacts"
    for name in ("offline-evaluation", "screenshots", "story", "playwright"):
        (artifacts / name).mkdir(parents=True)
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("COMPOSE_", "DOCKER_", "OPENAI_", "AZURE_OPENAI_"))
    }
    record = {
        "run_id": identity,
        "project": project,
        "started_at_utc": datetime.now(UTC).isoformat(),
        "status": "preparing",
        "commands": [],
        "images": {},
        "paid_calls": 0,
        "runtime_source": "private copy built into images; no application source binds",
        "scan_images_requested": scan_images,
    }

    def save():
        (output / "proof.json").write_text(
            json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    def command(args, timeout=600, cwd=None):
        step = {"argv": args, "phase": record["status"], "exit_code": None}
        index = len(record["commands"])
        record["commands"].append(step)
        save()
        print(f"{record['status']}: command {index} ({' '.join(args[:5])})", flush=True)
        with (output / f"command-{index:02d}.log").open("wb") as stream:
            process = subprocess.run(
                args,
                cwd=cwd or frozen,
                env=environment,
                stdout=stream,
                stderr=subprocess.STDOUT,
                timeout=timeout,
                check=False,
            )
        step["exit_code"] = process.returncode
        save()
        if process.returncode:
            raise RuntimeError(
                f"Command {index} failed; inspect private command-{index:02d}.log"
            )
        return (
            (output / f"command-{index:02d}.log")
            .read_text(encoding="utf-8", errors="replace")
            .strip()
        )

    compose = []
    runtime_started = False
    try:
        names = source_names(root)
        before = {name: digest(root / name) for name in names}
        frozen.mkdir()
        for name in names:
            target = frozen / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / name, target)
        if before != {name: digest(frozen / name) for name in names} or before != {
            name: digest(root / name) for name in names
        }:
            raise RuntimeError("Sources changed during freeze")
        record["sources"] = before
        record["source_identity_sha256"] = hashlib.sha256(
            json.dumps(before, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        record["head"] = command(["git", "rev-parse", "HEAD"], cwd=root, timeout=30)
        record["branch"] = command(
            ["git", "branch", "--show-current"], cwd=root, timeout=30
        )
        command(["git", "diff", "--binary", "HEAD"], cwd=root, timeout=30)
        record["diff_log"] = "command-02.log"
        command(["python", "scripts/verify_evidence.py"], timeout=60)
        record["engine"] = command(
            ["docker", "version", "--format", "{{.Server.Version}}"], timeout=30
        )
        record["projects_before"] = command(
            ["docker", "compose", "ls", "--format", "json"], timeout=30
        )
        record["containers_before"] = command(
            ["docker", "ps", "--format", "{{.ID}} {{.Names}} {{.Image}} {{.Ports}}"],
            timeout=30,
        )
        ids = command(["docker", "network", "ls", "-q"], timeout=30).splitlines()
        prefixes = []
        networks = []
        for network_id in ids:
            # Never inspect Config/Env, ImageConfig, session payloads or cookies.
            data = command(
                [
                    "docker",
                    "network",
                    "inspect",
                    "--format",
                    "{{json .IPAM.Config}}",
                    network_id,
                ],
                timeout=30,
            )
            configs = json.loads(data) or []
            prefixes.extend(item["Subnet"] for item in configs if item.get("Subnet"))
            networks.append({"id": network_id, "ipam": configs})
        if os.name == "nt":
            route_json = command(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    "Get-NetRoute -AddressFamily IPv4 | Select-Object -ExpandProperty DestinationPrefix | ConvertTo-Json",
                ],
                timeout=30,
            )
            routes = json.loads(route_json)
            if isinstance(routes, str):
                routes = [routes]
            prefixes.extend(value for value in routes if value != "0.0.0.0/0")
            record["host_routes"] = routes
        else:
            route_json = command(["ip", "-json", "route"], timeout=30)
            routes = json.loads(route_json)
            prefixes.extend(row["dst"] for row in routes if row.get("dst") != "default")
            record["host_routes"] = routes
        record["networks_before"] = networks
        record["subnet"] = choose_subnet(prefixes)
        record["status"] = "building"
        for component, dockerfile, context, target in (
            ("backend", "backend/Dockerfile", ".", None),
            ("frontend-checks", "frontend/Dockerfile", "frontend", "checks"),
            ("frontend", "frontend/Dockerfile", "frontend", "runtime"),
            ("e2e", "frontend/Dockerfile.e2e", "frontend", None),
        ):
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
                args.extend(["--target", target])
            command(args + [context], timeout=1200)
            record["images"][component] = command(
                ["docker", "image", "inspect", "--format", "{{.Id}}", tag], timeout=30
            )
        command(["docker", "pull", "postgres:17.11-bookworm"], timeout=180)
        record["images"]["db"] = command(
            [
                "docker",
                "image",
                "inspect",
                "--format",
                "{{.Id}}",
                "postgres:17.11-bookworm",
            ],
            timeout=30,
        )
        values = {
            "PROOF_RUN_ID": identity,
            "PROOF_OUTPUT_DIR": artifacts.as_posix(),
            "PROOF_SUBNET": record["subnet"],
            **{
                "PROOF_" + name.upper().replace("-", "_") + "_IMAGE": value
                for name, value in record["images"].items()
            },
        }
        env_file = output / "public-test.env"
        env_file.write_text(
            "\n".join(f"{key}={value}" for key, value in values.items()) + "\n",
            encoding="utf-8",
        )
        compose = [
            "docker",
            "compose",
            "-p",
            project,
            "--env-file",
            str(env_file),
            "-f",
            str(frozen / "compose.evolution.yaml"),
        ]
        command(compose + ["config", "--quiet"], timeout=30)
        record["status"] = "checks"
        runtime_started = True
        command(compose + ["up", "-d", "--wait", "test-db"], timeout=120)
        command(compose + ["run", "--rm", "checks"], timeout=900)
        command(compose + ["run", "--rm", "frontend-checks"], timeout=300)
        record["status"] = "http-browser"
        command(compose + ["up", "-d", "--wait", "frontend"], timeout=180)
        command(
            compose
            + [
                "exec",
                "-T",
                "-e",
                "DEMO_ORIGIN=http://frontend:3102",
                "-e",
                "DEMO_REPORT=/tmp/http-demo.json",
                "backend",
                "python",
                "/app/scripts/demo_check.py",
            ],
            timeout=120,
        )
        command(
            compose
            + ["cp", "backend:/tmp/http-demo.json", str(artifacts / "http-demo.json")],
            timeout=30,
        )
        command(compose + ["run", "--rm", "e2e"], timeout=900)
        if scan_images:
            record["status"] = "image-scans"
            for component in ("backend", "frontend"):
                command(
                    [
                        "docker",
                        "run",
                        "--rm",
                        "-v",
                        "/var/run/docker.sock:/var/run/docker.sock:ro",
                        "aquasec/trivy:0.74.0@sha256:62b1e65e8869bc4b4c6aa4fa2b21595256c7c2f6018a9d9ad61caf87187c1969",
                        "image",
                        "--scanners",
                        "vuln",
                        "--ignorefile",
                        "/dev/null",
                        "--severity",
                        "HIGH,CRITICAL",
                        "--exit-code",
                        "1",
                        record["images"][component],
                    ],
                    timeout=600,
                )
        command(["python", "scripts/verify_evidence.py"], timeout=60)
        record["status"] = "passed"
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        record["status"] = "failed"
        record["error"] = str(error)
    finally:
        if runtime_started:
            try:
                # Inspect only ownership labels before any removal.
                for kind, listing, format_string in (
                    ("container", ["ps", "-aq"], "{{json .Config.Labels}}"),
                    ("network", ["network", "ls", "-q"], "{{json .Labels}}"),
                ):
                    ids = command(
                        [
                            "docker",
                            *listing,
                            "--filter",
                            "label=com.docker.compose.project=" + project,
                        ],
                        timeout=30,
                    ).splitlines()
                    for item in ids:
                        labels = json.loads(
                            command(
                                [
                                    "docker",
                                    kind,
                                    "inspect",
                                    "--format",
                                    format_string,
                                    item,
                                ],
                                timeout=30,
                            )
                        )
                        if (
                            labels.get("portfolio.evolution") != identity
                            or labels.get("com.docker.compose.project") != project
                        ):
                            raise RuntimeError("Ownership mismatch; cleanup refused")
                command(compose + ["down", "--volumes", "--timeout", "10"], timeout=60)
                remaining = command(
                    [
                        "docker",
                        "ps",
                        "-aq",
                        "--filter",
                        "label=com.docker.compose.project=" + project,
                    ],
                    timeout=30,
                )
                record["cleanup"] = "complete" if not remaining else "resources remain"
            except (
                OSError,
                ValueError,
                RuntimeError,
                subprocess.SubprocessError,
            ) as error:
                record["cleanup_error"] = str(error)
                record["status"] = "failed"
        if "sources" in record:
            record["frozen_sources_unchanged"] = all(
                digest(frozen / name) == value
                for name, value in record["sources"].items()
            )
            record["host_sources_unchanged"] = names == source_names(root) and all(
                digest(root / name) == value
                for name, value in record["sources"].items()
            )
            if (
                not record["frozen_sources_unchanged"]
                or not record["host_sources_unchanged"]
            ):
                record["status"] = "failed"
                record["source_changed"] = True
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
    return 0 if record["status"] == "passed" else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="New private output parent, e.g. .runtime/evolution",
    )
    parser.add_argument(
        "--skip-image-scans",
        action="store_true",
        help="Development only; receipt records omitted scans",
    )
    args = parser.parse_args()
    raise SystemExit(
        run(Path(__file__).resolve().parents[1], args.output, not args.skip_image_scans)
    )
