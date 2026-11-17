#!/usr/bin/env python3
"""Tests for html_favicon_checker — stdlib unittest only.

Every HTML document in this file is made up for testing.
No real secret appears anywhere in this file.
"""

import ast
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import html_favicon_checker as checker

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "src/html_favicon_checker.py"


def run_cli(argv):
    """Run main(argv), capture stdout/stderr, return (code, out, err)."""
    out = io.StringIO()
    err = io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        try:
            code = checker.main(argv)
        except SystemExit as exc:
            code = exc.code
    return code, out.getvalue(), err.getvalue()


def write(tmp, name, text, encoding="utf-8"):
    path = Path(tmp) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(text, bytes):
        path.write_bytes(text)
    else:
        path.write_text(text, encoding=encoding)
    return str(path)


def findings_of(text):
    return checker.check_text(text)


class TestFaviconDetection(unittest.TestCase):
    def test_icon_link_passes(self):
        self.assertEqual(
            findings_of('<html><head>'
                        '<link rel="icon" href="/favicon.ico">'
                        '</head></html>'),
            [])

    def test_shortcut_icon_link_passes(self):
        self.assertEqual(
            findings_of('<html><head>'
                        '<link rel="shortcut icon" href="favicon.ico">'
                        '</head></html>'),
            [])

    def test_favicon_href_without_rel_passes(self):
        self.assertEqual(
            findings_of('<html><head>'
                        '<link href="/favicon.ico">'
                        '</head></html>'),
            [])

    def test_icon_link_with_png_href_passes(self):
        self.assertEqual(
            findings_of('<html><head>'
                        '<link rel="icon" href="/icon.png">'
                        '</head></html>'),
            [])

    def test_page_without_any_link_fails(self):
        bad = findings_of('<html><head><title>Home</title></head>'
                          '<body><p>Hello</p></body></html>')
        self.assertEqual(len(bad), 1)
        self.assertEqual(bad[0]["line"], 1)
        self.assertEqual(bad[0]["reason"], "has no favicon link")

    def test_finding_line_is_the_head_line(self):
        text = ('<!doctype html>\n<html lang="en">\n<head>\n'
                '<title>Home</title>\n'
                '<link rel="stylesheet" href="/style.css">\n'
                '</head>\n<body>\n</body>\n</html>\n')
        bad = findings_of(text)
        self.assertEqual(len(bad), 1)
        self.assertEqual(bad[0]["line"], 3)

    def test_finding_line_is_the_html_line_without_head(self):
        text = ('<!doctype html>\n<html lang="en">\n<body>\n'
                '<p>Hello</p>\n</body>\n</html>\n')
        bad = findings_of(text)
        self.assertEqual(len(bad), 1)
        self.assertEqual(bad[0]["line"], 2)

    def test_empty_document_fails_at_line_1(self):
        bad = findings_of("")
        self.assertEqual(len(bad), 1)
        self.assertEqual(bad[0]["line"], 1)

    def test_plain_text_document_fails_at_line_1(self):
        bad = findings_of("Just some words, no markup at all.\n")
        self.assertEqual(len(bad), 1)
        self.assertEqual(bad[0]["line"], 1)

    def test_stylesheet_only_link_fails(self):
        bad = findings_of(
            '<html><head>'
            '<link rel="stylesheet" href="/style.css">'
            '</head></html>')
        self.assertEqual(len(bad), 1)

    def test_apple_touch_icon_only_fails(self):
        bad = findings_of(
            '<html><head>'
            '<link rel="apple-touch-icon" href="/apple.png">'
            '</head></html>')
        self.assertEqual(len(bad), 1)

    def test_icon_link_with_empty_href_fails(self):
        bad = findings_of(
            '<html><head>'
            '<link rel="icon" href="">'
            '</head></html>')
        self.assertEqual(len(bad), 1)

    def test_icon_link_with_blank_href_fails(self):
        bad = findings_of(
            '<html><head>'
            '<link rel="icon" href="   ">'
            '</head></html>')
        self.assertEqual(len(bad), 1)

    def test_uppercase_link_and_rel_pass(self):
        self.assertEqual(
            findings_of('<html><head>'
                        '<LINK REL="ICON" HREF="/favicon.ico">'
                        '</head></html>'),
            [])

    def test_favicon_href_with_query_string_passes(self):
        self.assertEqual(
            findings_of('<html><head>'
                        '<link href="/favicon.ico?v=2">'
                        '</head></html>'),
            [])

    def test_favicon_href_with_fragment_passes(self):
        self.assertEqual(
            findings_of('<html><head>'
                        '<link href="/favicon.ico#v2">'
                        '</head></html>'),
            [])

    def test_link_in_body_passes(self):
        self.assertEqual(
            findings_of('<html><body>'
                        '<link rel="icon" href="/favicon.ico">'
                        '</body></html>'),
            [])

    def test_link_split_across_lines_passes(self):
        text = ('<html>\n<head>\n'
                '<link\n  rel="icon"\n  href="/favicon.ico">\n'
                '</head>\n</html>\n')
        self.assertEqual(findings_of(text), [])

    def test_one_icon_link_among_many_passes(self):
        text = ('<html><head>'
                '<link rel="stylesheet" href="/a.css">'
                '<link rel="preconnect" href="https://example.com">'
                '<link rel="icon" href="/favicon.ico">'
                '</head></html>')
        self.assertEqual(findings_of(text), [])

    def test_rel_with_extra_tokens_passes(self):
        self.assertEqual(
            findings_of('<html><head>'
                        '<link rel="apple-touch-icon icon" '
                        'href="/favicon.ico">'
                        '</head></html>'),
            [])

    def test_favicon_ico_in_subfolder_passes(self):
        self.assertEqual(
            findings_of('<html><head>'
                        '<link href="/assets/favicon.ico">'
                        '</head></html>'),
            [])

    def test_unclosed_tags_elsewhere_do_not_hide_the_check(self):
        text = ('<html><head>\n<title>Home</title>\n'
                '<div><p>Unclosed\n')
        bad = findings_of(text)
        self.assertEqual(len(bad), 1)
        self.assertEqual(bad[0]["line"], 1)


class TestSkipping(unittest.TestCase):
    def test_icon_link_in_comment_only_fails(self):
        text = ('<html><head>\n'
                '<!-- <link rel="icon" href="/favicon.ico"> -->\n'
                '</head></html>\n')
        bad = findings_of(text)
        self.assertEqual(len(bad), 1)
        self.assertEqual(bad[0]["line"], 1)

    def test_icon_link_in_script_string_only_fails(self):
        text = ('<html><head>\n<script>\n'
                "var markup = '<link rel=\"icon\" "
                "href=\"/favicon.ico\">';\n"
                '</script>\n</head></html>\n')
        bad = findings_of(text)
        self.assertEqual(len(bad), 1)

    def test_icon_link_in_style_block_only_fails(self):
        text = ('<html><head>\n<style>\n'
                '.fake { content: "<link rel=\\"icon\\" '
                'href=\\"/favicon.ico\\">"; }\n'
                '</style>\n</head></html>\n')
        bad = findings_of(text)
        self.assertEqual(len(bad), 1)

    def test_real_icon_link_after_script_passes(self):
        text = ('<html><head>\n<script>var x = 1;</script>\n'
                '<link rel="icon" href="/favicon.ico">\n'
                '</head></html>\n')
        self.assertEqual(findings_of(text), [])

    def test_real_icon_link_after_comment_passes(self):
        text = ('<html><head>\n'
                '<!-- <link rel="icon" href="/fake.ico"> -->\n'
                '<link rel="icon" href="/favicon.ico">\n'
                '</head></html>\n')
        self.assertEqual(findings_of(text), [])


class TestCLI(unittest.TestCase):
    def test_clean_file_exit_0(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write(tmp, "page.html",
                         '<html><head><link rel="icon" '
                         'href="/favicon.ico"></head></html>\n')
            code, out, err = run_cli([path])
            self.assertEqual(code, 0)
            self.assertIn("every page links a favicon", out)
            self.assertEqual(err, "")

    def test_flagged_file_exit_1_with_file_and_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write(tmp, "page.html",
                         '<html><head><title>T</title></head></html>\n')
            code, out, err = run_cli([path])
            self.assertEqual(code, 1)
            self.assertIn("page line 1", out)
            self.assertIn("has no favicon link", out)
            self.assertIn(path, out)

    def test_folder_walk_finds_html_files_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, "a.html",
                  '<link rel="icon" href="/favicon.ico">\n')
            write(tmp, "b.htm", '<html><head></head></html>\n')
            write(tmp, "notes.txt", '<html><head></head></html>\n')
            code, out, err = run_cli([tmp])
            self.assertEqual(code, 1)
            self.assertIn("Checked 2 file(s)", out)
            self.assertIn("b.htm", out)
            self.assertNotIn("notes.txt", out)

    def test_folder_walk_skips_nested_with_no_recursive(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, "a.html",
                  '<link rel="icon" href="/favicon.ico">\n')
            write(tmp, "sub/b.html", '<html><head></head></html>\n')
            code, out, err = run_cli([tmp, "--no-recursive"])
            self.assertEqual(code, 0)
            self.assertIn("1 file(s) checked", out)
            code, out, err = run_cli([tmp])
            self.assertEqual(code, 1)
            self.assertIn("Checked 2 file(s)", out)

    def test_exclude_skips_a_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, "a.html",
                  '<link rel="icon" href="/favicon.ico">\n')
            write(tmp, "b.html", '<html><head></head></html>\n')
            code, out, err = run_cli([tmp, "--exclude", "b.html"])
            self.assertEqual(code, 0)
            self.assertIn("1 file(s) checked", out)

    def test_git_folder_skipped_in_walk(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, "a.html",
                  '<link rel="icon" href="/favicon.ico">\n')
            write(tmp, ".git/b.html", '<html><head></head></html>\n')
            code, out, err = run_cli([tmp])
            self.assertEqual(code, 0)
            self.assertIn("1 file(s) checked", out)

    def test_direct_file_checked_whatever_its_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write(tmp, "template.txt",
                         '<html><head></head></html>\n')
            code, out, err = run_cli([path])
            self.assertEqual(code, 1)
            self.assertIn("template.txt", out)

    def test_duplicate_paths_checked_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write(tmp, "a.html",
                         '<link rel="icon" href="/favicon.ico">\n')
            code, out, err = run_cli([path, path])
            self.assertEqual(code, 0)
            self.assertIn("1 file(s) checked", out)

    def test_json_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write(tmp, "a.html",
                         '<html><head></head></html>\n')
            code, out, err = run_cli(["--json", path])
            self.assertEqual(code, 1)
            data = json.loads(out)
            self.assertEqual(data["checked"], 1)
            self.assertEqual(data["findings"], 1)
            self.assertEqual(data["files"][0]["path"], path)
            self.assertEqual(
                data["files"][0]["findings"][0]["line"], 1)
            self.assertEqual(
                data["files"][0]["findings"][0]["reason"],
                "has no favicon link")
            self.assertIsNone(data["files"][0]["error"])

    def test_stdin_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [sys.executable, str(SRC), "--stdin"],
                input='<link rel="icon" href="/favicon.ico">\n',
                cwd=tmp, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0)
            self.assertIn("every page links a favicon",
                          result.stdout)

    def test_stdin_dirty(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [sys.executable, str(SRC), "--stdin"],
                input='<html><head></head></html>\n',
                cwd=tmp, capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn("FAIL <stdin>: page line 1", result.stdout)

    def test_stdin_with_paths_is_usage_error(self):
        code, out, err = run_cli(["--stdin", "page.html"])
        self.assertEqual(code, 2)

    def test_no_paths_is_usage_error(self):
        code, out, err = run_cli([])
        self.assertEqual(code, 2)

    def test_missing_path_exit_2(self):
        code, out, err = run_cli(["/nonexistent/path/xyz"])
        self.assertEqual(code, 2)
        self.assertIn("no such file or folder", err)

    def test_empty_folder_exit_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, out, err = run_cli([tmp])
            self.assertEqual(code, 2)
            self.assertIn("no HTML files found", err)

    def test_bad_flag_exit_2(self):
        code, out, err = run_cli(["--nope"])
        self.assertEqual(code, 2)

    def test_version(self):
        code, out, err = run_cli(["--version"])
        self.assertEqual(code, 0)
        self.assertIn("html_favicon_checker 1.0.0", out)

    def test_non_utf8_file_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write(tmp, "a.html", b"\xff\xfe<html></html>\n")
            code, out, err = run_cli([path])
            self.assertEqual(code, 1)
            self.assertIn("not valid UTF-8", out)

    def test_input_files_left_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write(tmp, "a.html",
                         '<html><head></head></html>\n')
            before = Path(path).read_text()
            run_cli([path])
            self.assertEqual(Path(path).read_text(), before)

    def test_cli_runs_from_another_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, "a.html",
                  '<link rel="icon" href="/favicon.ico">\n')
            result = subprocess.run(
                [sys.executable, str(SRC), "a.html"],
                cwd=tmp, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0)
            self.assertIn("every page links a favicon",
                          result.stdout)

    def test_cli_runs_under_fake_home(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write(tmp, "a.html",
                         '<link rel="icon" href="/favicon.ico">\n')
            old_home = os.environ.get("HOME")
            os.environ["HOME"] = tmp
            try:
                code, out, err = run_cli([path])
            finally:
                if old_home is None:
                    del os.environ["HOME"]
                else:
                    os.environ["HOME"] = old_home
            self.assertEqual(code, 0)


class TestExamples(unittest.TestCase):
    def test_run_example_output_matches_sample(self):
        result = subprocess.run(
            ["sh", "examples/run-example.sh"],
            cwd=REPO, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        expected = (REPO / "examples/sample-output.md").read_text()
        self.assertEqual(result.stdout, expected)

    def test_readme_quotes_match_real_runs(self):
        readme = (REPO / "README.md").read_text()
        clean = subprocess.run(
            [sys.executable, "src/html_favicon_checker.py",
             "examples/clean.html"],
            cwd=REPO, capture_output=True, text=True)
        self.assertEqual(clean.returncode, 0)
        self.assertIn(clean.stdout.strip(), readme)
        flagged = subprocess.run(
            [sys.executable, "src/html_favicon_checker.py",
             "examples/flagged.html"],
            cwd=REPO, capture_output=True, text=True)
        self.assertEqual(flagged.returncode, 1)
        self.assertIn(flagged.stdout.strip(), readme)
        folder = subprocess.run(
            [sys.executable, "src/html_favicon_checker.py",
             "examples/"],
            cwd=REPO, capture_output=True, text=True)
        self.assertEqual(folder.returncode, 1)
        self.assertIn("Checked 3 file(s), 1 page(s) without a favicon "
                      "in 1 file(s).", folder.stdout)
        self.assertIn("Checked 3 file(s), 1 page(s) without a favicon "
                      "in 1 file(s).", readme)
        edge = subprocess.run(
            [sys.executable, "src/html_favicon_checker.py",
             "examples/edge.html"],
            cwd=REPO, capture_output=True, text=True)
        self.assertEqual(edge.returncode, 0)
        self.assertIn(edge.stdout.strip(), readme)
        js = subprocess.run(
            [sys.executable, "src/html_favicon_checker.py",
             "--json", "examples/flagged.html"],
            cwd=REPO, capture_output=True, text=True)
        self.assertEqual(js.returncode, 1)
        self.assertIn(js.stdout.strip(), readme)
        stdin_bad = subprocess.run(
            [sys.executable, "src/html_favicon_checker.py",
             "--stdin"],
            input='<link rel="stylesheet" href="/style.css">\n',
            cwd=REPO, capture_output=True, text=True)
        self.assertEqual(stdin_bad.returncode, 1)
        self.assertIn(stdin_bad.stdout.strip(), readme)


class TestHygiene(unittest.TestCase):
    def _repo_files(self, skip_tests=True, skip_examples=True):
        for root, dirs, files in os.walk(REPO):
            dirs[:] = [d for d in dirs
                       if d not in (".git", "__pycache__")
                       and not (skip_tests and d == "tests")
                       and not (skip_examples and d == "examples")]
            for name in files:
                if name.endswith(".pyc"):
                    continue
                yield Path(root) / name

    def test_no_placeholder_text(self):
        banned = ["TODO", "coming soon", "lorem", "FIXME", "XXX"]
        hits = []
        for path in self._repo_files(skip_tests=True,
                                     skip_examples=False):
            text = path.read_text(errors="ignore")
            for word in banned:
                if word in text:
                    hits.append("%s: %s" % (path.name, word))
        self.assertEqual(hits, [])

    def test_no_absolute_paths(self):
        hits = []
        for path in self._repo_files(skip_tests=True,
                                     skip_examples=False):
            text = path.read_text(errors="ignore")
            for marker in ("/home/", "/Users/", "C:\\"):
                if marker in text:
                    hits.append("%s: %s" % (path.name, marker))
        self.assertEqual(hits, [])

    def test_no_real_secrets_outside_tests_and_examples(self):
        # The source holds no key values at all; the tests
        # and examples hold fake values only, so they are
        # excluded from this scan.
        patterns = [
            re.compile(r"AKIA[0-9A-Z]{16}"),
            re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
            re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
            re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
            re.compile(r"AIza[0-9A-Za-z_-]{35}"),
            re.compile(r"[rs]k_(?:live|test)_[A-Za-z0-9]{16,}"),
            re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}"),
            re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.eyJ"),
        ]
        hits = []
        for path in self._repo_files():
            text = path.read_text(errors="ignore")
            for pattern in patterns:
                if pattern.search(text):
                    hits.append("%s: %s" % (path.name, pattern.pattern))
        self.assertEqual(hits, [])

    def test_stdlib_imports_only(self):
        stdlib = set(sys.stdlib_module_names)
        for target in (REPO / "src/html_favicon_checker.py",
                       REPO / "tests/test_html_favicon_checker.py"):
            tree = ast.parse(target.read_text())
            imported = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported.update(a.name.split(".")[0]
                                    for a in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported.add(node.module.split(".")[0])
            self.assertFalse(
                imported - stdlib - {"html_favicon_checker"},
                (target.name, imported))
            self.assertNotIn("yaml", imported)

    def test_no_network_use_in_src(self):
        src = (REPO / "src/html_favicon_checker.py").read_text()
        for marker in ("urllib.request", "requests", "socket",
                       "http.client", "urlopen", "urlretrieve"):
            self.assertNotIn(marker, src, marker)

    def test_gitignore_lists_env_first(self):
        lines = (REPO / ".gitignore").read_text().splitlines()
        self.assertEqual(lines[0], ".env")

    def test_ci_runs_this_test_file(self):
        ci = (REPO / ".github/workflows/ci.yml").read_text()
        self.assertIn("tests/test_html_favicon_checker.py", ci)
        self.assertIn("ubuntu-latest", ci)
        self.assertIn("3.12", ci)
        self.assertIn("actions/checkout", ci)
        self.assertIn("setup-python", ci)
        self.assertIn("push", ci)
        self.assertIn("pull_request", ci)

    def test_readme_names_the_neighbouring_repos(self):
        readme = (REPO / "README.md").read_text()
        self.assertIn("html-title-checker-cli", readme)
        self.assertIn("html-lang-checker-cli", readme)
        self.assertIn("broken-link-checker-cli", readme)


if __name__ == "__main__":
    unittest.main()
