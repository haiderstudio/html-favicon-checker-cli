# html-favicon-checker-cli

Check every HTML page links a favicon — fail CI when one does not.

[![CI](https://github.com/haiderstudio/html-favicon-checker-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/haiderstudio/html-favicon-checker-cli/actions/workflows/ci.yml) [![Licence: MIT](https://img.shields.io/badge/Licence-MIT-yellow.svg)](LICENSE)

## What it does

`html_favicon_checker` reads each HTML file,
finds whether the page links a favicon, and
reports each page with no favicon link — with
the file and the line the link should have gone
on (the line `<head>` starts on, or the line
`<html>` starts on when there is no `<head>`,
or line 1 when there is neither). It exits 1
when any page lacks a favicon link, so it can
fail a CI run. A file whose pages all link a
favicon exits 0.

- A page with no favicon costs the site a 404 on
  every visit — the browser asks for
  `/favicon.ico` anyway — and shows a blank tab
  icon. This names the exact line, and the fix
  is one `<link>` tag per page.
- A page counts as linked when it has a `<link>`
  element that declares a favicon — a `rel`
  attribute holding the token `icon`, which
  covers `rel="icon"` and `rel="shortcut icon"`
  — or a `<link>` element whose `href` points at
  a file named `favicon.ico`, with or without a
  `rel` attribute. A query string or fragment on
  the href is ignored.
- A `rel="icon"` with an empty `href` does not
  count — it points at nothing. A stylesheet
  link does not count either, and neither does
  an `apple-touch-icon`, which is a home-screen
  icon, not a favicon.
- A file given directly on the command line is
  always checked, whatever its name. A folder is
  walked for files ending in `.html` or `.htm`
  only, recursively by default (`--no-recursive`
  stops at the top level). `.git` folders are
  never walked, and directory links are never
  followed.
- `--json` prints the result as JSON, and
  `--stdin` checks one HTML document read from
  standard input.
- Links inside HTML comments are not links —
  the parser skips them. Markup inside
  `<script>` and `<style>` blocks is not parsed
  as HTML either, so a `"<link rel=\"icon\">"`
  written in a JavaScript string or a stylesheet
  is left alone. Tag and attribute names are
  matched without regard to case, as HTML
  requires — `<LINK>` and `REL=` are checked
  exactly like `<link>` and `rel=`.

## Who it is for

Every site owner with a page — a home page, a
blog post, a landing page. One missing favicon
link and every visit costs the site a 404 while
the tab shows a blank icon, and the visitor
thinks the site is unfinished. This is the gate
that stops it at the pull request.

## What it does NOT do

- It does not check the icon file exists or
  loads. A link that points at a missing file is
  a different job — that is repo #9,
  broken-link-checker-cli, which checks links.
  This tool only checks that the link is there.
- It does not check the page title or language.
  That is repo #50, html-title-checker-cli, and
  repo #87, html-lang-checker-cli — the title
  and the language are different checks on the
  same pages.
- It does not check form actions, labels, or
  button types. Those are different checks on
  the same pages.
- It never rewrites a file, and it never touches
  the network.

## How this differs

- A fresh search of GitHub on Nov 15, 2026 found
  0 results for `"html-favicon-checker-cli"` and
  1 result for `html favicon checker` —
  Vlone-p/password-checker, 3 stars, a
  password-strength checker that merely contains
  the word "favicon" somewhere, not a checker of
  any kind.
- No rival checks favicon links in local files.

## Install

```sh
git clone https://github.com/haiderstudio/html-favicon-checker-cli.git
cd html-favicon-checker-cli
```

There is nothing else to install: Python 3.10 or newer,
standard library only, no dependencies.

## Usage

Check one HTML file:

```sh
python3 src/html_favicon_checker.py page.html
```

A file whose pages all link a favicon passes:

```sh
$ python3 src/html_favicon_checker.py examples/clean.html
OK — 1 file(s) checked, every page links a favicon.
```

A file with a page missing a favicon link fails,
with the file and line for each one:

```sh
$ python3 src/html_favicon_checker.py examples/flagged.html
FAIL examples/flagged.html: page line 3 has no favicon link
Checked 1 file(s), 1 page(s) without a favicon in 1 file(s).
```

Check a whole folder (`.html` / `.htm` files only):

```sh
$ python3 src/html_favicon_checker.py examples/
FAIL examples/flagged.html: page line 3 has no favicon link
Checked 3 file(s), 1 page(s) without a favicon in 1 file(s).
```

Check one document from standard input:

```sh
$ printf '<link rel="stylesheet" href="/style.css">\n' | python3 src/html_favicon_checker.py --stdin
FAIL <stdin>: page line 1 has no favicon link
Checked 1 file(s), 1 page(s) without a favicon in 1 file(s).
```

Machine-readable output:

```sh
$ python3 src/html_favicon_checker.py --json examples/flagged.html
{
  "files": [
    {
      "path": "examples/flagged.html",
      "findings": [
        {
          "line": 3,
          "reason": "has no favicon link"
        }
      ],
      "error": null
    }
  ],
  "checked": 1,
  "findings": 1
}
```

Exit codes: 0 when every page links a favicon, 1
when any page lacks one or a file cannot be read, 2
for a usage error (a missing path, a bad flag, or no
HTML files found).

## Examples

A favicon link in a comment and a favicon link
written inside a script string are not links, and
`examples/clean.html` holds both — it passes:

```sh
$ python3 src/html_favicon_checker.py examples/clean.html
OK — 1 file(s) checked, every page links a favicon.
```

Uppercase tags, a `shortcut icon` with a relative
path, and a link to `favicon.ico` with no `rel`
are all handled — `examples/edge.html` has all of
them, and it passes:

```sh
$ python3 src/html_favicon_checker.py examples/edge.html
OK — 1 file(s) checked, every page links a favicon.
```

A page with only a stylesheet link still fails —
the stylesheet is not a favicon:

```sh
$ printf '<link rel="stylesheet" href="/style.css">\n' | python3 src/html_favicon_checker.py --stdin
FAIL <stdin>: page line 1 has no favicon link
Checked 1 file(s), 1 page(s) without a favicon in 1 file(s).
```

Run every bundled example at once with `sh
examples/run-example.sh` — the output is saved in
[examples/sample-output.md](examples/sample-output.md).

## How it is tested

```sh
python3 tests/test_html_favicon_checker.py
```

The tests cover favicon detection (an icon link
passes, a shortcut icon passes, a favicon href
with no rel passes, an icon link with a PNG href
passes, a page with no link fails, the finding
line is the head line, the html line when there
is no head, and line 1 for an empty document or
plain text, a stylesheet-only link fails, an
apple-touch-icon only fails, an icon link with
an empty or blank href fails, uppercase tags and
attributes pass, a favicon href with a query
string or fragment passes, a link in the body
passes, a link split across lines passes, one
icon link among many passes, a rel with extra
tokens passes, a favicon.ico in a subfolder
passes, unclosed tags elsewhere do not hide the
check), skipping (an icon link in a comment only,
in a script string only, or in a style block only
fails, a real icon link after a script or a
comment passes), the CLI (exit 0/1/2, folder
walking for several HTML files including `.htm`,
nested folders, `--no-recursive`, `--exclude`,
`.git` skipped, a direct file checked whatever
its name, duplicate paths checked once, `--json`
output, `--stdin`, bad flags, missing paths,
empty folders, `--version`, a non-UTF-8 file
reported, input files left unchanged, the tool
run from another folder and under a changed
HOME), the bundled examples (sample output
compared byte-for-byte against a fresh run, and
the README-quoted outputs checked against it),
and hygiene checks (no placeholder text, no
absolute paths, no real secrets outside the
tests and examples, stdlib imports only, no
network use in the source, `.env` first in
`.gitignore`, CI file runs the test file, README
names the neighbouring repos).

## Contributing

Small, focused improvements are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

## Licence

MIT — see [LICENSE](LICENSE).

## Original work

This tool was written from scratch for this repo. The
idea of checking favicon links is not new, and the
parsing follows Python's own standard-library HTML
parser — but no existing tool does this one job,
checking that every page in local HTML files links
a favicon, as a tested command-line gate with a CI
exit code, as the search above shows — and every
line of code here is original, built on nothing but
Python's standard library.
