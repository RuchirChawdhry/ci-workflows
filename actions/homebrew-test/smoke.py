"""Exercise real Homebrew installation against a disposable local tap."""
from __future__ import annotations
import argparse
import hashlib
import os
import re
import shutil
import subprocess
import tempfile
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

def make_test_formula(formula: Path, archive: Path, stage: Path, base_url: str) -> Path:
    formula, archive, stage = Path(formula), Path(archive), Path(stage)
    text = formula.read_text(encoding="utf-8")
    if not archive.is_file():
        raise ValueError("checksum verification requires the archive file")
    sha = hashlib.sha256(archive.read_bytes()).hexdigest()
    if f'sha256 "{sha}"' not in text:
        raise ValueError("checksum mismatch with original release archive")
    urls = re.findall(r'^  url "([^"]+)"$', text, flags=re.M)
    if len(urls) != 1 or not urls[0].endswith("/" + archive.name):
        raise ValueError("formula must reference the exact release archive")
    stage.mkdir(parents=True, exist_ok=True)
    out = stage / "Formula" / formula.name
    out.parent.mkdir(parents=True, exist_ok=True)
    url = base_url.rstrip("/") + "/" + archive.name
    out.write_text(text.replace('  url "' + urls[0] + '"',
                                '  url "' + url + '"', 1), encoding="utf-8")
    return out

def run(*cmd: str, env=None) -> str:
    print("+", *cmd, flush=True)
    p = subprocess.run(cmd, env=env, text=True, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=240)
    print(p.stdout, flush=True)
    if p.returncode:
        raise RuntimeError(f"Command failed ({p.returncode}): {' '.join(cmd)}")
    return p.stdout.strip()

def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive", type=Path, required=True)
    p.add_argument("--formula", type=Path, required=True)
    p.add_argument("--app-name", required=True)
    p.add_argument("--binary-name", default="")
    args = p.parse_args()
    archive, formula = args.archive.resolve(strict=True), args.formula.resolve(strict=True)
    if shutil.which("brew") is None:
        raise RuntimeError("Homebrew is not installed on this runner")
    env = os.environ.copy()
    env.update(HOMEBREW_NO_AUTO_UPDATE="1", HOMEBREW_NO_ANALYTICS="1",
               HOMEBREW_NO_INSTALL_CLEANUP="1", HOMEBREW_NO_ENV_HINTS="1")
    with tempfile.TemporaryDirectory(prefix="homebrew-smoke-") as directory:
        root = Path(directory)
        assets = root / "assets"
        assets.mkdir()
        shutil.copyfile(archive, assets / archive.name)
        server = ThreadingHTTPServer(("127.0.0.1", 0),
            partial(SimpleHTTPRequestHandler, directory=str(assets)))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        tap = "ci-workflows/smoke"
        formula_name = f"{tap}/{args.app_name}"
        tapped = installed = False
        try:
            test_formula = make_test_formula(formula, archive, root/"tap-publisher",
                f"http://127.0.0.1:{server.server_port}")
            publisher = test_formula.parent.parent
            remote = root / "homebrew-smoke.git"
            run("git", "init", "--bare", str(remote), env=env)
            run("git", "-C", str(remote), "symbolic-ref", "HEAD", "refs/heads/main", env=env)
            run("git", "init", "-b", "main", str(publisher), env=env)
            run("git", "-C", str(publisher), "config", "user.name", "Homebrew CI Test", env=env)
            run("git", "-C", str(publisher), "config", "user.email", "ci@example.invalid", env=env)
            run("git", "-C", str(publisher), "remote", "add", "origin", remote.as_uri(), env=env)
            run("git", "-C", str(publisher), "add", f"Formula/{args.app_name}.rb", env=env)
            run("git", "-C", str(publisher), "commit", "-m", "Test formula", env=env)
            run("git", "-C", str(publisher), "push", "origin", "main", env=env)
            run("brew", "tap", tap, remote.as_uri(), env=env)
            tapped = True
            run("brew", "install", "--formula", formula_name, env=env)
            installed = True
            run("brew", "test", formula_name, env=env)
            prefix = Path(run("brew", "--prefix", formula_name, env=env).splitlines()[-1])
            binary = prefix / "bin" / (args.binary_name or args.app_name)
            if not binary.is_file():
                raise RuntimeError(f"Homebrew executable missing: {binary}")
            run(str(binary), "--help", env=env)
            print(f"HOMEBREW SMOKE PASS: {formula_name}", flush=True)
        finally:
            if installed:
                try: run("brew", "uninstall", "--force", formula_name, env=env)
                except Exception as exc: print("Cleanup warning:", exc, flush=True)
            if tapped:
                try: run("brew", "untap", tap, env=env)
                except Exception as exc: print("Cleanup warning:", exc, flush=True)
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

if __name__ == "__main__":
    main()
