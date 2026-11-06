#!/usr/bin/env python3
"""ndv_common.py — shared helpers for ndv_blueprint.py: config, file cache, code index, code-cite
and markdown-heading resolution, type-declaration scan. Extracted from the v1 ndv_check.py; only what
ndv_blueprint.py uses is kept. Python 3.8+, stdlib only."""

import collections
import json
import os
import re
import sys

def to_posix(path):
    """Normalize a path to '/'-separated, no leading './', for stable comparison
    and reporting regardless of host OS."""
    p = path.replace(os.sep, "/")
    if p.startswith("./"):
        p = p[2:]
    return p


class FileCache(object):
    """Caches file content as a list of lines (no line terminators) and as
    joined text, keyed by repo-relative path. Missing/unreadable files read
    as empty (callers treat that as "file not found" via os.path.isfile first)."""

    def __init__(self):
        self._lines = {}

    def lines(self, path):
        if path not in self._lines:
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
            except (IOError, OSError):
                content = ""
            raw = content.split("\n")
            if raw and raw[-1] == "" and content != "":
                raw.pop()
            self._lines[path] = raw
        return self._lines[path]

    def text(self, path):
        return "\n".join(self.lines(path))


HEADING_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")


def load_config(path):
    if not os.path.isfile(path):
        sys.stderr.write("ERROR: config not found: {}\n".format(path))
        sys.exit(2)
    try:
        with open(path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except ValueError as e:
        sys.stderr.write("ERROR: invalid JSON in config {}: {}\n".format(path, e))
        sys.exit(2)
    if not isinstance(cfg, dict):
        sys.stderr.write("ERROR: config {} must be a JSON object\n".format(path))
        sys.exit(2)
    cfg.setdefault("rulesRoot", ".claude/rules")
    cfg.setdefault("kitRulesRoot", ".claude/ndvkit/rules")
    cfg.setdefault("ndvRoot", ".ndv")
    return cfg


class CodeIndex(object):
    """Indexes every file under codeRoots for path resolution."""

    def __init__(self, code_roots):
        self.code_roots = code_roots
        self.all_files = []
        for root in code_roots:
            for dirpath, _dirnames, filenames in os.walk(root):
                for fn in filenames:
                    self.all_files.append(to_posix(os.path.join(dirpath, fn)))
        self.by_basename = collections.defaultdict(list)
        for f in self.all_files:
            self.by_basename[os.path.basename(f)].append(f)

    def resolve(self, cited_path):
        """-> (resolved_path_or_None, status) where status in
        'exact' | 'inexact' | 'ambiguous' | 'missing'."""
        p = cited_path
        if os.path.isfile(p):
            return to_posix(p), "exact"
        for root in self.code_roots:
            cand = to_posix(os.path.join(root, p))
            if os.path.isfile(cand):
                return cand, "exact"
        suffix = "/" + p
        hits = [f for f in self.all_files if f.endswith(suffix)]
        if len(hits) == 1:
            return hits[0], "inexact"
        if len(hits) > 1:
            return None, "ambiguous"
        base = os.path.basename(p)
        hits = self.by_basename.get(base, [])
        if len(hits) == 1:
            return hits[0], "inexact"
        if len(hits) > 1:
            return None, "ambiguous"
        return None, "missing"


SYM_RE = re.compile(
    r"(?P<path>[A-Za-z0-9_./\-]+\.[A-Za-z0-9]+)::(?P<type>[A-Za-z_][A-Za-z0-9_]*)"
    r"(?:\.(?P<member>[A-Za-z_][A-Za-z0-9_]*))?(?::(?P<sline>[0-9]+))?"
)


def github_slug(text):
    s = text.strip().lower()
    s = re.sub(r"[^\w\- ]", "", s, flags=re.UNICODE)
    s = re.sub(r"\s+", "-", s)
    return s


def section_matches(anchor, headings):
    """Best-effort heading match. A numeric (optionally §-prefixed) anchor passes
    against a heading starting with that number; otherwise (or as a deliberate
    extra leniency layered on top of a failed numeric match — this checker
    prefers a false pass over a false break for doc-cite) a normalized
    contains-check or GitHub-slug equality passes."""
    anchor = anchor.strip()
    m = re.match(r"§?\s*([0-9]+(?:\.[0-9]+)*)", anchor)
    if m:
        num = m.group(1)
        pat = re.compile(r"^" + re.escape(num) + r"(\.|\s|$)")
        for h in headings:
            if pat.match(h.strip()):
                return True

    def norm(s):
        return re.sub(r"[^a-z0-9]", "", s.lower())

    an = norm(anchor)
    if an:
        for h in headings:
            hn = norm(h)
            if hn and (an in hn or hn in an):
                return True
    slug_anchor = anchor.lower().lstrip("#")
    for h in headings:
        if github_slug(h) == slug_anchor:
            return True
    return False


TYPE_DECL_PATTERNS = {
    "cs": re.compile(r"\b(?:class|struct|interface|enum|record)\s+([A-Za-z_][A-Za-z0-9_]*)"),
    "go": re.compile(r"\btype\s+([A-Za-z_][A-Za-z0-9_]*)\b"),
}


IDENT_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def strip_comments_and_strings(src):
    """// and /* */ comments, C-style "..." strings (with \\ escapes and $-
    interpolation), C# verbatim @"..." strings, and Go raw `...` strings."""
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    src = re.sub(r"//[^\n]*", " ", src)
    src = re.sub(r'@"(?:[^"]|"")*"', '""', src)
    src = re.sub(r'\$?"(?:\\.|[^"\\\n])*"', '""', src)
    src = re.sub(r"`[^`]*`", "``", src)
    return src
