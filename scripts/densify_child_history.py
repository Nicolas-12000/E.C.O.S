#!/usr/bin/env python3
"""
Replay a filtered child repo history splitting multi-file commits into smaller ones.
Same final tree at HEAD; more commits for delivery repos. Only used after export_child_repos.sh.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=check)


def commits_in_order(repo: Path) -> list[str]:
    out = run(["git", "rev-list", "--reverse", "HEAD"], repo)
    return [c for c in out.stdout.splitlines() if c]


def commit_subject(repo: Path, sha: str) -> str:
    return run(["git", "log", "-1", "--format=%s", sha], repo).stdout.strip()


def changed_files(repo: Path, parent: str | None, child: str) -> list[str]:
    if parent is None:
        out = run(["git", "diff-tree", "--no-commit-id", "--name-only", "-r", child], repo)
    else:
        out = run(["git", "diff", "--name-only", parent, child], repo)
    return [f for f in out.stdout.splitlines() if f.strip()]


def parent_of(repo: Path, sha: str) -> str | None:
    p = run(["git", "rev-parse", f"{sha}^"], repo, check=False)
    if p.returncode != 0:
        return None
    return p.stdout.strip() or None


def densify(repo: Path, chunk: int) -> int:
    repo = repo.resolve()
    original = commits_in_order(repo)
    if len(original) < 1:
        print(f"[densify] skip {repo.name}: empty", file=sys.stderr)
        return 0

    before = len(original)
    run(["git", "checkout", "--orphan", "history-dense"], repo)
    run(["git", "reset", "--hard"], repo)

    for sha in original:
        parent = parent_of(repo, sha)
        files = changed_files(repo, parent, sha)
        if not files:
            continue
        subject = commit_subject(repo, sha)
        groups = [files[i : i + chunk] for i in range(0, len(files), chunk)]
        for i, group in enumerate(groups, 1):
            for path in group:
                cp = run(["git", "checkout", sha, "--", path], repo, check=False)
                if cp.returncode != 0:
                    run(["git", "rm", "-f", path], repo, check=False)
            run(["git", "add", "-A"], repo)
            status = run(["git", "status", "--porcelain"], repo)
            if not status.stdout.strip():
                continue
            suffix = f" ({i}/{len(groups)})" if len(groups) > 1 else ""
            run(
                ["git", "commit", "-m", f"{subject}{suffix}"],
                repo,
                check=False,
            )

    run(["git", "branch", "-D", "main"], repo, check=False)
    run(["git", "branch", "-m", "main"], repo)
    after = int(run(["git", "rev-list", "--count", "HEAD"], repo).stdout.strip())
    print(f"[densify] {repo.name}: {before} → {after} commits (chunk={chunk})")
    return after


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", type=Path)
    parser.add_argument("--chunk", type=int, default=2)
    args = parser.parse_args()
    densify(args.repo, max(1, args.chunk))


if __name__ == "__main__":
    main()
