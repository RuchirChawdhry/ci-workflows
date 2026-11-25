"""Exercise the reusable wiki publisher against a real local Git repository."""
import os
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/wiki-publish.yml"


def load():
    return yaml.load(WORKFLOW.read_text(), Loader=yaml.BaseLoader)


def git(cwd, *args):
    return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()


def test_workflow_contract():
    workflow = load()
    assert set(workflow["on"]) == {"workflow_call"}
    assert workflow["on"]["workflow_call"]["secrets"]["WIKI_TOKEN"]["required"] == "false"
    assert workflow["permissions"] == {"contents": "write"}
    job = workflow["jobs"]["publish"]
    assert "github.event.repository.default_branch" in job["if"]
    assert "github.event_name == 'push'" in job["if"]
    assert "github.event_name == 'workflow_dispatch'" in job["if"]
    assert job["concurrency"] == {"group": "publish-wiki", "cancel-in-progress": "false"}
    assert job["steps"][0]["with"]["persist-credentials"] == "false"
    assert job["steps"][1]["env"]["WIKI_TOKEN"] == "${{ secrets.WIKI_TOKEN || github.token }}"


@pytest.fixture
def publisher(tmp_path):
    remote = tmp_path / "owner" / "project.wiki.git"
    remote.parent.mkdir()
    seed = tmp_path / "seed"
    seed.mkdir()
    git(seed, "init", "-b", "main")
    git(seed, "config", "user.name", "Test")
    git(seed, "config", "user.email", "test@example.org")
    (seed / "Home.md").write_text("old")
    (seed / "Unmanaged.md").write_text("preserve")
    git(seed, "add", ".")
    git(seed, "commit", "-m", "Initialize wiki")
    git(seed, "clone", "--bare", str(seed), str(remote))
    source = tmp_path / "source"
    source.mkdir()
    (source / "wiki").mkdir()
    summary = tmp_path / "summary"
    env = dict(os.environ, WIKI_TOKEN="local-test-only", GITHUB_SERVER_URL=tmp_path.as_uri(),
               GITHUB_REPOSITORY="owner/project", GITHUB_SHA="test-revision",
               GITHUB_STEP_SUMMARY=str(summary), GIT_TERMINAL_PROMPT="0")
    script = load()["jobs"]["publish"]["steps"][1]["run"]

    def run():
        runner = tmp_path / ("runner-" + str(len(list(tmp_path.glob("runner-*")))))
        runner.mkdir()
        return subprocess.run(["bash", "-c", script], cwd=source,
                              env=dict(env, RUNNER_TEMP=str(runner)),
                              capture_output=True, text=True)

    return source / "wiki", remote, summary, run


def test_sync_preserves_unmanaged_pages_and_is_idempotent(publisher):
    source, remote, summary, run = publisher
    (source / "Home.md").write_text("new")
    (source / "Guide.md").write_text("guide")
    result = run()
    assert result.returncode == 0, result.stderr
    assert git(remote, "show", "HEAD:Home.md") == "new"
    assert git(remote, "show", "HEAD:Guide.md") == "guide"
    assert git(remote, "show", "HEAD:Unmanaged.md") == "preserve"
    head = git(remote, "rev-parse", "HEAD")
    result = run()
    assert result.returncode == 0, result.stderr
    assert git(remote, "rev-parse", "HEAD") == head
    assert "Wiki already up to date." in summary.read_text()


def test_missing_home_and_symlinks_fail_before_publish(publisher):
    source, remote, _, run = publisher
    head = git(remote, "rev-parse", "HEAD")
    assert run().returncode != 0
    (source / "Home.md").write_text("new")
    (source / "Linked.md").symlink_to(source / "Home.md")
    result = run()
    assert result.returncode != 0
    assert "not symlinks" in result.stdout
    assert git(remote, "rev-parse", "HEAD") == head
