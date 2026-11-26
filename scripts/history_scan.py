"""Scan the whole git history for credential classes and report words. It prints counts only.

usage: python3 -I scripts/history_scan.py <repo> [--word W ...]

The scan streams `git log --all -p` and tests every added and removed line. It prints one
table row per pattern (name, lines, commits, files) and one last line with the totals. It
never prints a matched text, a file name, a file content line or an address.

Exit codes: 0 no credential-class hit, 1 at least one credential-class hit, 2 usage or read error.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path

CLEAN = 0
CREDENTIAL_HIT = 1
USAGE_ERROR = 2
GIT_QUICK_TIMEOUT_SECONDS = 60
COMMIT_MARK = "@@COMMIT "
HUNK_MARK = "@@"
DIFF_MARK = "diff --git "
NAME_WIDTH = 44

Matcher = Callable[[str], bool]


@dataclass(frozen=True)
class Pattern:
    name: str
    matches: Matcher
    credential: bool


@dataclass
class Tally:
    lines: int = 0
    commits: set[str] = field(default_factory=set)
    files: set[str] = field(default_factory=set)


def regex_matcher(expression: str) -> Matcher:
    compiled = re.compile(expression)
    return lambda text: compiled.search(text) is not None


# Each credential expression needs a token character class right after the prefix, so the
# source text of this table does not match itself.
CREDENTIAL_EXPRESSIONS: tuple[tuple[str, str], ...] = (
    ("GitHub token", r"\b(?:ghp_|gho_|ghs_|ghu_|github_pat_)[A-Za-z0-9_]{20,}"),
    ("GitLab token", r"glpat-[A-Za-z0-9_-]{15,}"),
    ("sk- API key", r"\bsk-[A-Za-z0-9_-]{20,}"),
    ("AWS access key id", r"\bAKIA[0-9A-Z]{16}\b"),
    ("Slack token", r"\bxox[baprs]-[A-Za-z0-9-]{10,}"),
    ("private key block", r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    ("JWT", r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}"),
    (
        "authorization header literal",
        r"(?i)authorization['\"]?\s*[:=]\s*['\"]?(?:bearer|token|basic)\s+[A-Za-z0-9._-]{16,}",
    ),
    (
        "secret-like assignment",
        r"(?i)\b(?:password|passwd|secret|api[_-]?key|access[_-]?token|client[_-]?secret)\b"
        r"\s*[:=]\s*['\"][^'\"\s$%{<]{12,}['\"]",
    ),
    (
        "internal IPv4 address",
        r"\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}"
        r"|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}"
        r"|100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.\d{1,3}\.\d{1,3})\b",
    ),
)
GUID_EXPRESSION = r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b"
EMAIL = re.compile(r"[A-Za-z0-9._+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")
SKIPPED_EMAIL = re.compile(
    r"^(?:noreply@anthropic\.com|[^@]+@example\.[a-z]+|[^@]+@users\.noreply\.github\.com)$"
)


def word_matcher(word: str) -> Matcher:
    """Match the whole word, case-insensitive. Letters and digits next to it break the match."""
    return regex_matcher(rf"(?i)(?<![A-Za-z0-9]){re.escape(word)}(?![A-Za-z0-9])")


def email_matchers(identities: frozenset[str]) -> tuple[Matcher, Matcher]:
    """Return (holds a commit identity, holds another address)."""

    def addresses(text: str) -> list[str]:
        return [found.group(0).lower() for found in EMAIL.finditer(text)]

    def has_identity(text: str) -> bool:
        return any(address in identities for address in addresses(text))

    def has_other(text: str) -> bool:
        return any(
            address not in identities and SKIPPED_EMAIL.match(address) is None
            for address in addresses(text)
        )

    return has_identity, has_other


def build_patterns(identities: frozenset[str], words: Iterable[str]) -> list[Pattern]:
    patterns = [Pattern(name, regex_matcher(rx), True) for name, rx in CREDENTIAL_EXPRESSIONS]
    has_identity, has_other = email_matchers(identities)
    patterns.append(Pattern("GUID", regex_matcher(GUID_EXPRESSION), False))
    patterns.append(Pattern("commit identity", has_identity, False))
    patterns.append(Pattern("other email", has_other, False))
    patterns.extend(Pattern(word, word_matcher(word), False) for word in words)
    return patterns


def git_lines(repo: Path, *args: str) -> list[str]:
    done = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        errors="replace",
        timeout=GIT_QUICK_TIMEOUT_SECONDS,
        check=False,
    )
    if done.returncode != 0:
        raise OSError("git could not read the history")
    return done.stdout.splitlines()


def commit_identities(repo: Path) -> frozenset[str]:
    lines = git_lines(repo, "log", "--all", "--format=%ae%n%ce")
    return frozenset(line.strip().lower() for line in lines if line.strip())


@dataclass
class ScanResult:
    commits: int
    diff_lines: int
    tallies: dict[str, Tally]


def scan_history(repo: Path, patterns: list[Pattern]) -> ScanResult:
    """Stream the history. Count per pattern: lines, commits and files."""
    tallies = {pattern.name: Tally() for pattern in patterns}
    command = ["git", "-C", str(repo), "log", "--all", "-p", "--no-color", "-U0"]
    command.append(f"--format={COMMIT_MARK}%H")
    commits = 0
    diff_lines = 0
    commit = ""
    path = ""
    in_header = False
    with subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, errors="replace"
    ) as process:
        assert process.stdout is not None
        for raw in process.stdout:
            line = raw.rstrip("\n")
            if line.startswith(COMMIT_MARK):
                commit = line[len(COMMIT_MARK) :]
                commits += 1
                in_header = False
            elif line.startswith(DIFF_MARK):
                path = line.rsplit(" b/", 1)[-1]
                in_header = True
            elif in_header and line.startswith(HUNK_MARK):
                in_header = False
            elif not in_header and line[:1] in ("+", "-"):
                diff_lines += 1
                for pattern in patterns:
                    if pattern.matches(line[1:]):
                        tally = tallies[pattern.name]
                        tally.lines += 1
                        tally.commits.add(commit)
                        tally.files.add(path)
    if process.returncode != 0:
        raise OSError("git could not read the history")
    return ScanResult(commits, diff_lines, tallies)


def credential_hits(result: ScanResult, patterns: list[Pattern]) -> int:
    return sum(result.tallies[p.name].lines for p in patterns if p.credential)


def format_report(result: ScanResult, patterns: list[Pattern], refs: int) -> list[str]:
    out = [f"refs {refs}", f"{'pattern':<{NAME_WIDTH}} {'lines':>8} {'commits':>8} {'files':>6}"]
    for pattern in patterns:
        tally = result.tallies[pattern.name]
        out.append(
            f"{pattern.name:<{NAME_WIDTH}} {tally.lines:>8} {len(tally.commits):>8} {len(tally.files):>6}"
        )
    out.append(
        f"history-scan: commits {result.commits}, diff lines {result.diff_lines}, "
        f"credential hits {credential_hits(result, patterns)}"
    )
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Count credential classes and words in git history."
    )
    parser.add_argument("repo", type=Path)
    parser.add_argument("--word", action="append", default=[], help="count this word (repeatable)")
    args = parser.parse_args(argv)
    repo: Path = args.repo
    try:
        git_lines(repo, "rev-parse", "--git-dir")
        patterns = build_patterns(commit_identities(repo), args.word)
        refs = len(git_lines(repo, "for-each-ref"))
        result = scan_history(repo, patterns)
    except (OSError, subprocess.SubprocessError):
        print("history-scan: error: cannot read a git history at the given path", file=sys.stderr)
        return USAGE_ERROR
    report = format_report(result, patterns, refs)
    print("\n".join(report))
    return CREDENTIAL_HIT if credential_hits(result, patterns) else CLEAN


if __name__ == "__main__":
    sys.exit(main())
