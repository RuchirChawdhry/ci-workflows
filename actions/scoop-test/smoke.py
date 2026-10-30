"""Real Scoop install smoke test using a disposable local HTTP source."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def prepare_local_manifest(manifest_path: Path, asset: Path, stage: Path, base_url: str) -> Path:
    manifest_path, asset, stage = Path(manifest_path), Path(asset), Path(stage)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not asset.is_file() or asset.stat().st_size == 0:
        raise ValueError("missing or empty test asset")
    actual = hashlib.sha256(asset.read_bytes()).hexdigest()
    if payload.get("hash", "").lower() != actual:
        raise ValueError("release manifest hash does not match actual artifact")
    stage.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(asset, stage / asset.name)
    payload["url"] = f"{base_url.rstrip('/')}/{asset.name}"
    payload.pop("checkver", None)
    payload.pop("autoupdate", None)
    out = stage / "test-manifests" / manifest_path.name
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return out


def run_checked(*args: str, env: dict[str, str]) -> str:
    print("+", *args, flush=True)
    result = subprocess.run(args, env=env, text=True, capture_output=True, timeout=180)
    if result.stdout:
        print(result.stdout, flush=True)
    if result.stderr:
        print(result.stderr, flush=True)
    if result.returncode:
        raise RuntimeError(f"command failed with exit {result.returncode}: {args}")
    return result.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--app-name", required=True)
    parser.add_argument("--help-argument", default="--help")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="scoop-smoke-") as folder:
        root = Path(folder).resolve()
        assets = root / "assets"
        assets.mkdir()
        handler = partial(SimpleHTTPRequestHandler, directory=str(assets))
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            manifest = prepare_local_manifest(
                args.manifest, args.asset, assets, f"http://127.0.0.1:{server.server_port}"
            )
            scoop_dir = root / "scoop"
            env = os.environ.copy()
            env["SCOOP"] = str(scoop_dir)
            env["PATH"] = str(scoop_dir / "shims") + os.pathsep + env.get("PATH", "")
            env["NO_PROXY"] = "localhost,127.0.0.1"
            env["no_proxy"] = env["NO_PROXY"]
            bootstrap = root / "scoop-install.ps1"
            # Install Scoop into a brand-new temporary directory.
            install = (
                '$ErrorActionPreference = "Stop"; '
                f'Invoke-WebRequest https://get.scoop.sh -OutFile "{bootstrap}"; '
                f'& "{bootstrap}" -RunAsAdmin -ScoopDir "{scoop_dir}"; '
                'if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }'
            )
            run_checked("pwsh", "-NoProfile", "-Command", install, env=env)
            run_checked("pwsh", "-NoProfile", "-Command",
                        f'& scoop install "{manifest}"; if ($LASTEXITCODE -ne 0) {{ exit $LASTEXITCODE }}',
                        env=env)
            validated = json.loads(manifest.read_text(encoding="utf-8"))
            exe = scoop_dir / "apps" / args.app_name / validated["version"] / validated["bin"]
            if not exe.is_file():
                raise AssertionError(f"missing installed executable: {exe}")
            run_checked(str(exe), args.help_argument, env=env)
            shim = scoop_dir / "shims" / f'{Path(validated["bin"]).stem}.exe'
            if not shim.exists():
                raise AssertionError(f"missing Scoop command shim: {shim}")
            run_checked(str(shim), args.help_argument, env=env)
            print(f"SCOOP SMOKE PASS: {args.app_name} {validated['version']} executable and shim", flush=True)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    main()
