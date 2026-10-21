#!/usr/bin/env python3
"""Run release policy blocks without signing, uploads, network, or YAML dependencies."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = (ROOT / ".github/workflows/build.yml").read_text()
PUBLISH = (ROOT / "ci/publish.sh").read_text()
PLATFORMS = ("win64", "linux64", "macos")


def step(name):
    section = WORKFLOW.split(f"      - name: {name}\n", 1)[1]
    block = section.split("        run: |\n", 1)[1].split("\n      - name:", 1)[0]
    return "\n".join(line[10:] for line in block.splitlines() if line.startswith("          "))


def shell(code, env=None, cwd=None):
    return subprocess.run(
        ["bash", "-euo", "pipefail", "-c", code], cwd=cwd,
        env={**os.environ, **(env or {})}, text=True, capture_output=True,
    )


class ReleasePolicy(unittest.TestCase):
    def test_complete_monotonic_latest(self):
        block = PUBLISH.split("# even the first release", 1)[1].split(
            "# two platforms can update", 1
        )[0].split("\n", 1)[1]
        code = '''
platforms=(win64 linux64 macos)
assets() { printf '%s\\n' "$ASSETS"; }
gh() {
  if [ "$1 $2" = "release view" ]; then
    printf '%s\\n' "$LATEST"
  else
    printf 'EDIT %s\n' "$*" >&2
  fi
}
''' + block
        feeds = "\n".join(f"tele-update-{p}.json" for p in PLATFORMS)
        cases = [
            ("", "", feeds, True),
            ("", "", "tele-update-win64.json", False),
            ("v7.3.1-tele.9", "v7.3.1-tele.9", feeds, True),
            ("v7.3.1-tele.11", "v7.3.1-tele.11", feeds, False),
            ("v7.3.1-tele.10", "v7.3.1-tele.10", feeds, False),
            ("v7.3.1-tele.8", "v7.3.1-tele.9", feeds, False),
            ("external-tag", "external-tag", feeds, False),
        ]
        cases += [("v7.3.1-tele.9", "v7.3.1-tele.9",
                   "\n".join(f"tele-update-{p}.json" for p in PLATFORMS if p != missing), False)
                  for missing in PLATFORMS]
        for latest, previous, assets, promote in cases:
            with self.subTest(latest=latest, previous=previous, assets=assets):
                result = shell(code, {"TAG": "v7.3.1-tele.10", "COUNTER": "10",
                                      "LATEST": latest, "PREVIOUS_TAG": previous, "ASSETS": assets})
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual("EDIT release edit v7.3.1-tele.10 --latest" in result.stderr, promote)

    def test_finished_number(self):
        code = '''
gh() { printf '%s\\n' "$RELEASES"; }
git() { printf '%s\\n' "$REMOTE_TAGS"; }
''' + step("Read the release number").replace("${{ inputs.from_run }}", "123")
        cases = [
            ("", "", "10", True),
            ("v7.3.1-tele.10", "", "10", True),
            ("v7.3.1-tele.11", "", "10", False),
            ("v7.3.1-tele.9", "", "10", True),
            ("v7.3.2-tele.10", "", "10", False),
            ("", "abc\trefs/tags/v7.3.1-tele.11", "10", False),
            ("", "abc\trefs/tags/v7.3.1-tele.10", "10", True),
            ("", "", "invalid", False),
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            for releases, tags, counter, accepted in cases:
                with self.subTest(releases=releases, tags=tags, counter=counter):
                    (path / "number.env").write_text(f"tag=v7.3.1-tele.10\ncounter={counter}\n")
                    result = shell(code, {"RELEASES": releases, "REMOTE_TAGS": tags,
                                          "GH_REPO": "test/repo", "GITHUB_SERVER_URL": "https://example.invalid",
                                          "GITHUB_OUTPUT": str(path / "output")}, path)
                    self.assertEqual(result.returncode == 0, accepted, result.stdout + result.stderr)

    def test_finished_source_inputs(self):
        code = '''
gh() {
  if [[ "$2" == */artifacts* ]]; then
    printf 'release-win64\\nrelease-linux64\\nrelease-macos\\n'
  else
    printf 'success %s\\n' "$SOURCE_SHA"
  fi
}
''' + step("Check the finished run")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)

            def git(*args):
                return subprocess.check_output(
                    ["git", "-c", "user.name=Policy test", "-c", "user.email=test@example.invalid", *args],
                    cwd=path, text=True, stderr=subprocess.DEVNULL,
                ).strip()

            git("init", "--quiet")
            (path / "UPSTREAM").write_text("v7.3.1\n")
            git("add", ".")
            git("commit", "--quiet", "-m", "fixture")
            source = git("rev-parse", "HEAD")
            for changed in ("UPSTREAM", "patches/test.patch", "tele.py", "ci/msvc.cmd",
                            "ci/check_localization.py", "ci/test_publish.py", ".github/workflows/build.yml", "docs/releasing.md"):
                with self.subTest(changed=changed):
                    git("reset", "--hard", source)
                    git("clean", "-fd")
                    file = path / changed
                    file.parent.mkdir(parents=True, exist_ok=True)
                    file.write_text("changed\n")
                    git("add", ".")
                    git("commit", "--quiet", "-m", "changed input")
                    result = shell(code, {"GH_REPO": "test/repo", "RUN": "123", "SOURCE_SHA": source,
                                          "GITHUB_SHA": git("rev-parse", "HEAD")}, path)
                    self.assertEqual(result.returncode == 0, changed.startswith("docs/"),
                                     result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
