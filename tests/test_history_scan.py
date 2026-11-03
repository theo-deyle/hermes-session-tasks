"""The history scan counts credential classes and report words, and never prints a match (D-50).

Every fake secret is built at run time from parts, so no token-shaped text sits in this
file or in the repo history. Each test builds a small git repo in `tmp_path`.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "history_scan.py"
CLEAN = 0
CREDENTIAL_HIT = 1
USAGE_ERROR = 2
GIT_TIMEOUT_SECONDS = 30
SCAN_TIMEOUT_SECONDS = 60
AUTHOR_EMAIL = "dev@corp.invalid"
ROW = re.compile(r"^(.*?)\s+(\d+)\s+(\d+)\s+(\d+)$")
LAST_LINE = re.compile(r"^history-scan: commits (\d+), diff lines (\d+), credential hits (\d+)$")
GITHUB_ROW = "GitHub token"
IP_ROW = "internal IPv4 address"
IDENTITY_ROW = "commit identity"
OTHER_EMAIL_ROW = "other email"


def run_git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        timeout=GIT_TIMEOUT_SECONDS,
    )


def make_repo(root: Path, *commits: dict[str, str]) -> Path:
    """Build a repo with one commit per mapping of file name to file text."""
    repo = root / "repo"
    repo.mkdir()
    run_git(repo, "init", "-q")
    for number, files in enumerate(commits, start=1):
        for name, text in files.items():
            (repo / name).write_text(text, encoding="utf-8")
            run_git(repo, "add", name)
        run_git(
            repo,
            "-c",
            "user.name=Test",
            "-c",
            f"user.email={AUTHOR_EMAIL}",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-q",
            "-m",
            f"commit {number}",
        )
    return repo


def scan(repo: Path, *words: str) -> subprocess.CompletedProcess[str]:
    args = [sys.executable, "-I", str(SCRIPT), str(repo)]
    for word in words:
        args += ["--word", word]
    return subprocess.run(
        args, capture_output=True, text=True, timeout=SCAN_TIMEOUT_SECONDS, check=False
    )


def rows(output: str) -> dict[str, tuple[int, int, int]]:
    found: dict[str, tuple[int, int, int]] = {}
    for line in output.splitlines():
        match = ROW.match(line.strip())
        if match is not None:
            found[match.group(1)] = (
                int(match.group(2)),
                int(match.group(3)),
                int(match.group(4)),
            )
    return found


def last_line(output: str) -> str:
    return output.strip().splitlines()[-1]


def test_a_planted_token_is_counted_and_never_printed(tmp_path: Path) -> None:
    token = "gh" + "p_" + "A" * 36
    repo = make_repo(tmp_path, {"notes.txt": f"key = {token}\n"})

    result = scan(repo)

    assert result.returncode == CREDENTIAL_HIT
    assert rows(result.stdout)[GITHUB_ROW] == (1, 1, 1)
    assert token not in result.stdout
    assert token not in result.stderr
    assert "A" * 20 not in result.stdout + result.stderr
    summary = LAST_LINE.match(last_line(result.stdout))
    assert summary is not None
    assert summary.group(3) == "1"


def test_clean_text_gives_no_credential_hit(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, {"readme.txt": "plain text\nmore plain text\n"})

    result = scan(repo)

    assert result.returncode == CLEAN
    summary = LAST_LINE.match(last_line(result.stdout))
    assert summary is not None
    assert summary.group(1) == "1"
    assert summary.group(3) == "0"
    assert rows(result.stdout)[GITHUB_ROW] == (0, 0, 0)


def test_history_is_scanned_not_only_the_last_commit(tmp_path: Path) -> None:
    secret = "gh" + "p_" + "B" * 36
    repo = make_repo(tmp_path, {"a.txt": f"{secret}\n"}, {"a.txt": "removed\n"})

    result = scan(repo)

    assert result.returncode == CREDENTIAL_HIT
    assert rows(result.stdout)[GITHUB_ROW][0] == 2
    assert secret not in result.stdout


def test_an_internal_address_is_a_credential_class_hit(tmp_path: Path) -> None:
    address = ".".join(["192", "168", "1", "20"])
    repo = make_repo(tmp_path, {"net.txt": f"host {address}\n"})

    result = scan(repo)

    assert result.returncode == CREDENTIAL_HIT
    assert rows(result.stdout)[IP_ROW] == (1, 1, 1)
    assert address not in result.stdout


def test_a_secret_like_assignment_is_a_credential_class_hit(tmp_path: Path) -> None:
    value = "x" * 16
    repo = make_repo(tmp_path, {"cfg.txt": "pass" + "word = '" + value + "'\n"})

    result = scan(repo)

    assert result.returncode == CREDENTIAL_HIT
    assert value not in result.stdout


def test_a_word_is_counted_case_insensitively_and_named_in_the_table(tmp_path: Path) -> None:
    repo = make_repo(
        tmp_path,
        {"a.txt": "an Example here\nand an example there\nnothing\n"},
        {"b.txt": "EXAMPLE once\nexamples is not a whole word\n"},
    )

    result = scan(repo, "Example")

    assert result.returncode == CLEAN
    assert rows(result.stdout)["Example"] == (3, 2, 2)


def test_commit_identity_and_other_addresses_are_counted_not_printed(tmp_path: Path) -> None:
    other = "someone@" + "elsewhere.invalid"
    text = f"mine {AUTHOR_EMAIL}\nfree {other}\nskip a@example.invalid\n"
    repo = make_repo(tmp_path, {"mail.txt": text})

    result = scan(repo)

    assert result.returncode == CLEAN
    table = rows(result.stdout)
    assert table[IDENTITY_ROW] == (1, 1, 1)
    assert table[OTHER_EMAIL_ROW] == (1, 1, 1)
    assert AUTHOR_EMAIL not in result.stdout
    assert other not in result.stdout


def test_a_path_that_is_not_a_repo_gives_one_error_line(tmp_path: Path) -> None:
    result = scan(tmp_path)

    assert result.returncode == USAGE_ERROR
    assert result.stdout == ""
    assert len(result.stderr.strip().splitlines()) == 1
    assert result.stderr.startswith("history-scan: error:")
