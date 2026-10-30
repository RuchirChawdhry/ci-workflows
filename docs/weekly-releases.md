# Weekly snapshot releases

The repository publishes a release **only when the delivered files have changed**
since the previous published weekly snapshot. No manual version bump or SemVer
calculation is necessary.

**Schedule:** Sundays at 09:00 Asia/Kolkata (03:30 UTC). A manual
`workflow_dispatch` from `main` performs the same conditional release.
Scheduled GitHub Actions can be delayed and public-repository schedules may be
disabled by GitHub after 60 days of repository inactivity.

## Release naming

- Tag: `weekly-2026-11-01`
- Asset: `ci-workflows-weekly-2026-11-01.zip`
- Checksum: `SHA256SUMS.txt`

A release points to the exact `main` commit used to build it. Only one snapshot
is published per UTC date. Tags are not moved; consumers wanting immutable
references can use an exact weekly tag or full commit SHA.

## ZIP contents

All tracked files under:

```text
.github/workflows/
actions/
assets/
README.md
LICENSE
```

Tests, documentation outside the README, scripts, and website sources are **not
part of the bundle**. The exact folder hierarchy is retained. Because the ZIP
does not contain `docs/`, links in README that point to repository documentation
work on GitHub rather than in a fully offline copy.

The release process compares the **Git tree contents at these paths** between
the previous published weekly tag and `main`, not the total number of commits.
Changes to tests or the website alone, and changes reverted before the next
weekly check, do not generate an unnecessary release.

## Validation

A PR-only `weekly-release-smoke.yml` workflow builds and checks a candidate
ZIP and uploads it as a normal Actions artifact without releasing anything.
The publishing workflow re-runs the repository contract suite, builds with
`git archive`, verifies entries against the tracked files, checks archive
integrity and SHA-256, and only then creates the GitHub Release.

Tag creation and publishing require the scoped `contents: write` job token.
The repository's release process should use protected or immutable release
tags to prevent older snapshots from being silently replaced.

The first release happens at the first eligible scheduled/manual run. If there
is no previous weekly release, it produces the initial ZIP. If the contents
are unchanged, there is no new release. If a release already exists under
the current UTC date, the workflow skips publishing again that day.

**No GitHub Release will be created by the PR smoke workflow.**
