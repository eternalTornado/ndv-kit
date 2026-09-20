#!/usr/bin/env python3
"""ndv_check.py — deterministic, read-only-by-default checker for ndvkit pipeline
artifacts (TDD / Specs / ModuleMatrix / rules / CLAUDE.md).

Runs from the HOST repo root. Config-driven, stack-agnostic: every root/path used
below comes from ``ndvkit.config.json`` — nothing about a specific project is
hard-coded. Python 3.8+, stdlib only.

Checks:
  code-cite      -- `<path>::<Type>[.<Member>][:<line>]` and legacy `<path>.<ext>:<N>`
                     cites into codeRoots still resolve and still land.
  doc-cite       -- cites into rulesRoot/kitRulesRoot/tddRoot/specsRoot/gddRoot
                     markdown docs still resolve (file, #section, :line).
  contract-gap   -- Contract surface / Consumer obligations tables in
                     requirement.md/specify.md carry a real Owner/Consumer FR id
                     that exists in the owning module's requirement.md.
  deps (opt-in)  -- modules.json deps[]/plannedDeps[] vs the actual type-reference
                     graph found in code under codeRoots.

Modes (each runs standalone -- no citation/contract/deps checks are run; exit
0 on success, 2 on usage/config error):
  --refresh-status [MODULE ...]  -- derive modules.json status per module from
                     code/tasks/audit-report/plan/requirement evidence;
                     dry-run unless combined with --write (which also
                     regenerates modules.md).
  --render        -- write <matrixRoot>/modules.md from modules.json
                     (deterministic; modules.json stays the source of truth).
  --inventory     -- read-only artifact coverage matrix + estate counts, for
                     brownfield onboarding.

See the CLI --help (bottom of file) for flags. Exit codes: 0 = clean (no
broken-cite / contract-gap finding, or a mode above completed), 1 = at least
one broken-cite/contract-gap finding, 2 = usage/config error.
"""

import argparse
import collections
import glob
import json
import os
import re
import sys


# ===========================================================================
# Constants
# ===========================================================================

# Known "this looks like source code" extensions. Used to (a) scope the legacy
# `<path>.<ext>:<N>` line-anchor grammar (symbol cites `::` work for ANY
# extension) and (b) scope the `deps` check to files this tool considers code
# (so Unity .meta/.asset/.prefab noise under codeRoots never shows up there).
SOURCE_EXTS = set("cs go ts tsx js jsx py java kt swift c cc cpp h hpp rs lua gd".split())

# Generic language keywords only (no project-specific words) — used to drop
# noise when collecting "identifiers named beside a legacy line anchor".
KEYWORD_STOPWORDS = set("""
public private protected internal static readonly virtual override abstract
sealed partial const void true false null nil none True False class struct
interface enum record namespace using import package return break continue
this base self new var let func function def lambda async await yield try
catch finally throw throws switch case default if else for foreach while do
in is as out ref params get set event delegate type chan select go defer map
string int long float double bool byte char object dynamic then end local
nonlocal global elif pass raise except with from
""".split())

FR_ID_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]*-(?:FR|NFR)-\d+")

STATUS_KINDS = {
    "broken-cite": {"file-not-found", "ambiguous-path", "symbol-miss", "line-out-of-range",
                    "symbol-moved", "symbol-gone", "doc-missing", "section-not-found",
                    "doc-line-out-of-range"},
    "contract-gap": {"no-owner-fr-column", "no-owner-fr", "owner-fr-not-found",
                      "owner-not-registered"},
}


# ===========================================================================
# Finding
# ===========================================================================

class Finding(object):
    """One reportable observation. `kind` defaults to `status` for statuses
    that have no finer sub-classification (see STATUS_KINDS)."""
    __slots__ = ("artifact", "line", "cite", "status", "kind", "detail")

    def __init__(self, artifact, line, cite, status, kind=None, detail=""):
        self.artifact = artifact
        self.line = line
        self.cite = cite
        self.status = status
        self.kind = kind if kind else status
        self.detail = detail

    def to_dict(self):
        return {
            "artifact": self.artifact, "line": self.line, "cite": self.cite,
            "status": self.status, "kind": self.kind, "detail": self.detail,
        }


# ===========================================================================
# Small utilities
# ===========================================================================

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


STRAIGHT_QUOTE_RE = re.compile(r'"[^"\n]*"')
JSON_ESCAPED_QUOTE_RE = re.compile(r'\\"[^"\n]*?\\"')
CURLY_QUOTE_RE = re.compile(r"\u201c[^\u201d\n]*\u201d")


def find_quote_spans(line, is_json=False):
    """Literal quote spans on a line ("…" or "…") — text quoted verbatim from
    another source (e.g. GDD prose), not the artifact's own citation. In a JSON
    artifact the raw '"' characters delimit the JSON string itself (any nested
    literal quote in the value's prose is escaped as \\"…\\"), so plain '"..."'
    would wrongly treat the whole field value as one giant quote span."""
    spans = []
    straight_pat = JSON_ESCAPED_QUOTE_RE if is_json else STRAIGHT_QUOTE_RE
    for pat in (straight_pat, CURLY_QUOTE_RE):
        spans.extend((m.start(), m.end()) for m in pat.finditer(line))
    return spans


def in_any_span(pos, spans):
    return any(a <= pos < b for a, b in spans)


def mask_spans(line, spans):
    """Blank out the given [start,end) spans with spaces, preserving length/offsets."""
    chars = list(line)
    for a, b in spans:
        for i in range(a, min(b, len(chars))):
            chars[i] = " "
    return "".join(chars)


HEADING_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")


def headings_of(lines):
    """[(line_no, level, text), ...] for every markdown heading."""
    out = []
    for i, l in enumerate(lines):
        m = HEADING_RE.match(l)
        if m:
            out.append((i + 1, len(m.group(1)), m.group(2)))
    return out


# ===========================================================================
# Config
# ===========================================================================

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
    return cfg


def glob_md(root):
    if not root or not os.path.isdir(root):
        return []
    return sorted(to_posix(p) for p in glob.glob(os.path.join(root, "**", "*.md"), recursive=True))


def gather_artifacts(cfg, notes):
    """Returns (code_cite_artifacts, doc_cite_artifacts, matrix_path). Degrades
    gracefully (with a note) when a root or modules.json is absent — never scans
    audit reports or the kit's own folder, since none of those live under the
    configured tddRoot/specsRoot/rulesRoot in a sane host layout."""
    tdd_md = glob_md(cfg.get("tddRoot"))
    if not cfg.get("tddRoot") or not os.path.isdir(cfg.get("tddRoot") or ""):
        notes.append("tddRoot missing or not configured — TDD artifacts skipped")
    specs_md = glob_md(cfg.get("specsRoot"))
    if not cfg.get("specsRoot") or not os.path.isdir(cfg.get("specsRoot") or ""):
        notes.append("specsRoot missing or not configured — Specs artifacts skipped")

    matrix_path = None
    if cfg.get("matrixRoot"):
        cand = to_posix(os.path.join(cfg["matrixRoot"], "modules.json"))
        if os.path.isfile(cand):
            matrix_path = cand
        else:
            notes.append("{} not found — modules.json-dependent checks degrade".format(cand))
    else:
        notes.append("matrixRoot not configured — modules.json-dependent checks degrade")

    code_cite_artifacts = sorted(set(tdd_md + specs_md + ([matrix_path] if matrix_path else [])))

    doc_cite_artifacts = list(code_cite_artifacts)
    if os.path.isfile("CLAUDE.md"):
        doc_cite_artifacts.append("CLAUDE.md")
    doc_cite_artifacts += glob_md(cfg.get("rulesRoot"))
    doc_cite_artifacts = sorted(set(doc_cite_artifacts))

    return code_cite_artifacts, doc_cite_artifacts, matrix_path


def load_modules(matrix_path, cache):
    """Returns (modules_list_or_None, module_ids_set_or_None)."""
    if not matrix_path:
        return None, None
    try:
        data = json.loads(cache.text(matrix_path))
    except ValueError:
        return None, None
    modules = data.get("modules") if isinstance(data, dict) else None
    if not isinstance(modules, list):
        return None, None
    ids = set(m["id"] for m in modules if isinstance(m, dict) and "id" in m)
    return modules, ids


# ===========================================================================
# Code path resolution (shared by code-cite, deps, reanchor)
# ===========================================================================

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


# ===========================================================================
# Check: code-cite
# ===========================================================================

SYM_RE = re.compile(
    r"(?P<path>[A-Za-z0-9_./\-]+\.[A-Za-z0-9]+)::(?P<type>[A-Za-z_][A-Za-z0-9_]*)"
    r"(?:\.(?P<member>[A-Za-z_][A-Za-z0-9_]*))?(?::(?P<sline>[0-9]+))?"
)

_ext_alt = "|".join(sorted(SOURCE_EXTS, key=len, reverse=True))
LEG_RE = re.compile(
    r"(?P<path>[A-Za-z0-9_./\-]+\.(?:" + _ext_alt + r")):(?P<start>[0-9]+)"
    r"(?:-(?P<end>[0-9]+))?(?P<extra>(?:,\s*[0-9]+(?:-[0-9]+)?)*)"
)

IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{3,}")
TICK_RE = re.compile(r"`([^`\n]+)`")


def _looks_pathy(token):
    return "/" in token or bool(re.search(r"\.[A-Za-z0-9]{1,5}(:\d|$)", token))


BESIDE_WINDOW = 160


def identifiers_beside(line, pos):
    """Identifiers named beside a legacy anchor near `pos` on the artifact line:
    inside backticks, excluding backtick spans that are themselves a path/cite,
    >=4 chars, minus generic keyword stopwords (nothing project-specific).
    Scoped to a proximity window rather than the whole line — a markdown table
    row is short enough that this rarely matters, but a modules.json field is
    often one giant paragraph-length line, and a backtick token from an
    unrelated sentence 300 chars away is not "named beside" this cite."""
    idents = set()
    for tick in TICK_RE.finditer(line):
        if tick.start() < pos - BESIDE_WINDOW or tick.start() > pos + BESIDE_WINDOW:
            continue
        content = tick.group(1)
        if _looks_pathy(content):
            continue
        idents |= set(IDENT_RE.findall(content))
    return idents - KEYWORD_STOPWORDS


def parse_ranges(start, end, extra):
    ranges = [(int(start), int(end) if end else int(start))]
    for a, b in re.findall(r"([0-9]+)(?:-([0-9]+))?", extra or ""):
        ranges.append((int(a), int(b) if b else int(a)))
    return ranges


def check_code_cite(artifacts, code_index, cache, touched=None, legacy_sink=None, inexact_sym_sink=None):
    """For every code cite found in `artifacts`, verify the path resolves under
    codeRoots and the symbol/line still lands. `touched`, if given, restricts
    findings to cites that RESOLVE to one of those repo-relative files (used
    for the post-implement cite sweep). `legacy_sink`, if given, additionally
    collects clean legacy-line-anchor detail for --reanchor. `inexact_sym_sink`,
    if given, additionally collects symbol cites resolved only via inexact
    (suffix/basename) path match whose Type/Member word-match cleanly, as
    ready-made `{artifact,line,old,new}` --reanchor path-normalization proposals."""
    findings = []
    touched_set = set(to_posix(t) for t in touched) if touched else None

    for art in artifacts:
        lines = cache.lines(art)
        is_json = art.endswith(".json")
        for lineno, raw_line in enumerate(lines, start=1):
            quote_spans = find_quote_spans(raw_line, is_json=is_json)
            sym_matches = list(SYM_RE.finditer(raw_line))
            masked = mask_spans(raw_line, [(m.start(), m.end()) for m in sym_matches])
            leg_matches = list(LEG_RE.finditer(masked))

            for m in sym_matches:
                cite_text = m.group(0)
                resolved, status = code_index.resolve(m.group("path"))
                if touched_set is not None and resolved not in touched_set:
                    continue
                if in_any_span(m.start(), quote_spans):
                    findings.append(Finding(art, lineno, cite_text, "quoted-anchor"))
                    continue
                if status == "missing":
                    findings.append(Finding(art, lineno, cite_text, "broken-cite", "file-not-found"))
                    continue
                if status == "ambiguous":
                    findings.append(Finding(art, lineno, cite_text, "broken-cite", "ambiguous-path"))
                    continue
                if status == "inexact":
                    findings.append(Finding(art, lineno, cite_text, "inexact-path"))
                text = cache.text(resolved)
                missing = [s for s in (m.group("type"), m.group("member"))
                           if s and not re.search(r"\b" + re.escape(s) + r"\b", text)]
                if missing:
                    findings.append(Finding(art, lineno, cite_text, "broken-cite", "symbol-miss",
                                             "missing: " + ",".join(missing)))
                elif status == "inexact" and inexact_sym_sink is not None:
                    new_cite = cite_text.replace(m.group("path"), resolved, 1)
                    if new_cite != cite_text:
                        inexact_sym_sink.append({"artifact": art, "line": lineno,
                                                  "old": cite_text, "new": new_cite})

            for m in leg_matches:
                cite_text = m.group(0)
                resolved, status = code_index.resolve(m.group("path"))
                if touched_set is not None and resolved not in touched_set:
                    continue
                if in_any_span(m.start(), quote_spans):
                    findings.append(Finding(art, lineno, cite_text, "quoted-anchor"))
                    continue
                if status == "missing":
                    findings.append(Finding(art, lineno, cite_text, "broken-cite", "file-not-found"))
                    continue
                if status == "ambiguous":
                    findings.append(Finding(art, lineno, cite_text, "broken-cite", "ambiguous-path"))
                    continue
                inexact = status == "inexact"
                if inexact:
                    findings.append(Finding(art, lineno, cite_text, "inexact-path"))

                file_lines = cache.lines(resolved)
                ranges = parse_ranges(m.group("start"), m.group("end"), m.group("extra"))
                out_of_range = any(a > len(file_lines) or b > len(file_lines) for a, b in ranges)
                if out_of_range:
                    findings.append(Finding(art, lineno, cite_text, "broken-cite", "line-out-of-range",
                                             "file has {} lines".format(len(file_lines))))
                    continue

                beside = identifiers_beside(raw_line, m.start())
                verdict = "legacy-line-anchor"
                if beside:
                    seg = "\n".join("\n".join(file_lines[a - 1:b]) for a, b in ranges)
                    seg_idents = set(IDENT_RE.findall(seg))
                    if beside.isdisjoint(seg_idents):
                        whole_idents = set(IDENT_RE.findall("\n".join(file_lines)))
                        verdict = "symbol-moved" if beside & whole_idents else "symbol-gone"
                if verdict == "legacy-line-anchor":
                    findings.append(Finding(art, lineno, cite_text, "legacy-line-anchor"))
                    if legacy_sink is not None:
                        legacy_sink.append({"artifact": art, "line": lineno, "cite": cite_text,
                                             "path": resolved, "ranges": ranges})
                else:
                    findings.append(Finding(art, lineno, cite_text, "broken-cite", verdict))
    return findings


# ===========================================================================
# Check: doc-cite
# ===========================================================================

TICK_SPAN_RE = re.compile(r"`([^`\n]+)`")


def build_doc_regexes(roots):
    """roots: {role: path}. Longest root matches first so e.g. rulesRoot never
    shadows a longer, more specific kitRulesRoot (or vice versa) for any config."""
    ordered = sorted((v for v in roots.values() if v), key=len, reverse=True)
    if not ordered:
        return None, None
    alt = "|".join(re.escape(r) for r in ordered)
    # Inside backticks: GDD file names may contain spaces.
    tick_re = re.compile(
        r"(?<![A-Za-z0-9_./\-])(?P<path>(?:" + alt + r")/[^\n]*?\.md)"
        r"(?P<suffix>#[^\n]*|:[0-9]+(?:-[0-9]+)?)?"
    )
    # Outside backticks: assume no spaces in the path.
    bare_re = re.compile(
        r"(?<![A-Za-z0-9_./\-])(?P<path>(?:" + alt + r")/[A-Za-z0-9_./\-]*?\.md)"
        r"(?P<suffix>#[A-Za-z0-9_./\-]*|:[0-9]+(?:-[0-9]+)?)?"
    )
    return tick_re, bare_re


def iter_doc_cites(line, tick_re, bare_re):
    """Yield (start, end, path, suffix) for every doc cite on the line, inside
    or outside backticks."""
    out = []
    spans = []
    for tm in TICK_SPAN_RE.finditer(line):
        content = tm.group(1)
        base = tm.start(1)
        for cm in tick_re.finditer(content):
            out.append((base + cm.start(), base + cm.end(), cm.group("path"), cm.group("suffix")))
        spans.append((tm.start(), tm.end()))
    blanked = mask_spans(line, spans)
    for cm in bare_re.finditer(blanked):
        out.append((cm.start(), cm.end(), cm.group("path"), cm.group("suffix")))
    return out


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


def check_doc_cite(artifacts, doc_roots, cache):
    findings = []
    tick_re, bare_re = build_doc_regexes(doc_roots)
    if tick_re is None:
        return findings
    for art in artifacts:
        lines = cache.lines(art)
        for lineno, raw in enumerate(lines, start=1):
            for _start, _end, path, suffix in iter_doc_cites(raw, tick_re, bare_re):
                if PLACEHOLDER_RE.search(path):
                    continue  # doc prose illustrating a naming pattern (`docs/TDD/<Feature>/tdd.md`), not a real cite
                cite_text = path + (suffix or "")
                if not os.path.isfile(path):
                    findings.append(Finding(art, lineno, cite_text, "broken-cite", "doc-missing"))
                    continue
                if suffix and suffix.startswith("#"):
                    anchor = suffix[1:].strip()
                    target_headings = [h for _, _, h in headings_of(cache.lines(path))]
                    if anchor and not section_matches(anchor, target_headings):
                        findings.append(Finding(art, lineno, cite_text, "broken-cite", "section-not-found"))
                elif suffix and suffix.startswith(":"):
                    m = re.match(r":([0-9]+)(?:-([0-9]+))?", suffix)
                    n = int(m.group(1))
                    n2 = int(m.group(2)) if m.group(2) else n
                    total = len(cache.lines(path))
                    if n > total or n2 > total:
                        findings.append(Finding(art, lineno, cite_text, "broken-cite",
                                                 "doc-line-out-of-range",
                                                 "file has {} lines".format(total)))
    return findings


# ===========================================================================
# Check: contract-gap
# ===========================================================================

CONTRACT_HEADING_RE = re.compile(r"^#{1,6}\s*(Contract surface|Consumer obligations)\b", re.IGNORECASE)
PLACEHOLDER_RE = re.compile(r"<[^`\n<>]+>")
SEP_CELL_RE = re.compile(r"^:?-{1,}:?$")
MODULE_TOKEN_RE = re.compile(r"[`*_]*([A-Za-z][A-Za-z0-9_]*)")


def split_table_row(line):
    """Split a markdown table row on '|', ignoring '|' inside a backtick span or
    a quote span (this corpus has real rows that embed a quoted excerpt
    containing literal pipes)."""
    cells_raw = []
    buf = []
    in_tick = False
    in_quote = False
    for ch in line:
        if ch == "`" and not in_quote:
            in_tick = not in_tick
            buf.append(ch)
        elif ch == '"' and not in_tick:
            in_quote = not in_quote
            buf.append(ch)
        elif ch == "“" and not in_tick:
            in_quote = True
            buf.append(ch)
        elif ch == "”" and not in_tick:
            in_quote = False
            buf.append(ch)
        elif ch == "|" and not in_tick and not in_quote:
            cells_raw.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    cells_raw.append("".join(buf))
    cells = [c.strip() for c in cells_raw]
    if cells and cells[0] == "":
        cells = cells[1:]
    if cells and cells[-1] == "":
        cells = cells[:-1]
    return cells


def is_separator_row(cells):
    return bool(cells) and all(SEP_CELL_RE.match(c.strip()) for c in cells)


def find_first_table(lines, start, end):
    """First markdown table in lines[start:end) (0-indexed, end exclusive).
    -> (header_line_no_1indexed, header_cells, [(row_line_no_1indexed, cells), ...]) or None."""
    i = start
    while i < end - 1:
        if "|" in lines[i]:
            header_cells = split_table_row(lines[i])
            if i + 1 < end and "|" in lines[i + 1]:
                sep_cells = split_table_row(lines[i + 1])
                if is_separator_row(sep_cells):
                    rows = []
                    j = i + 2
                    while j < end:
                        line = lines[j]
                        if not line.strip() or "|" not in line:
                            break
                        rows.append((j + 1, split_table_row(line)))
                        j += 1
                    return i + 1, header_cells, rows
        i += 1
    return None


def section_bounds(lines, heading_idx, heading_level):
    n = len(lines)
    for i in range(heading_idx + 1, n):
        m = HEADING_RE.match(lines[i])
        if m and len(m.group(1)) <= heading_level:
            return heading_idx + 1, i
    return heading_idx + 1, n


def find_col(header_cells, name):
    for i, c in enumerate(header_cells):
        if c.strip().lower() == name.lower():
            return i
    return None


def is_na_row(cells):
    joined = " ".join(c.strip() for c in cells if c.strip())
    return bool(re.match(r"(?i)^n/a\b", joined))


def extract_module_token(cell):
    m = MODULE_TOKEN_RE.match(cell.strip())
    return m.group(1) if m else None


def evaluate_contract_table(fpath, header_line, header_cells, rows, is_consumer, module_ids, specs_root, cache):
    findings = []
    mod_col_name = "Consumer module" if is_consumer else "Owning module"
    fr_col_name = "Consumer FR" if is_consumer else "Owner FR"
    mod_idx = find_col(header_cells, mod_col_name)
    fr_idx = find_col(header_cells, fr_col_name)

    if not rows:
        return findings

    def is_placeholder_row(cells):
        return any(PLACEHOLDER_RE.search(c) for c in cells)

    body_rows = [(ln, cells) for ln, cells in rows if not is_placeholder_row(cells)]
    if not body_rows:
        return findings
    if all(is_na_row(cells) for _ln, cells in body_rows):
        return findings

    if fr_idx is None:
        findings.append(Finding(fpath, header_line, " | ".join(header_cells), "contract-gap",
                                 "no-owner-fr-column", "row count: {}".format(len(rows))))
        return findings

    for ln, cells in body_rows:
        fr_cell = cells[fr_idx] if fr_idx < len(cells) else ""
        mod_cell = cells[mod_idx] if (mod_idx is not None and mod_idx < len(cells)) else ""
        ids = FR_ID_RE.findall(fr_cell)

        if fr_cell.strip().lower().startswith("stopgap"):
            findings.append(Finding(fpath, ln, fr_cell.strip(), "contract-stopgap"))
            continue
        if not ids:
            findings.append(Finding(fpath, ln, fr_cell.strip() or "(empty)", "contract-gap", "no-owner-fr"))
            continue

        token = extract_module_token(mod_cell) if mod_idx is not None else None
        if mod_idx is not None and module_ids is not None:
            if token is None or token not in module_ids:
                findings.append(Finding(fpath, ln, mod_cell.strip(), "contract-gap",
                                         "owner-not-registered", "token={}".format(token)))
        if token and specs_root:
            target = to_posix(os.path.join(specs_root, token, "requirement.md"))
            target_text = cache.text(target) if os.path.isfile(target) else None
            for rid in ids:
                if target_text is None or not re.search(r"\b" + re.escape(rid) + r"\b", target_text):
                    findings.append(Finding(fpath, ln, rid, "contract-gap", "owner-fr-not-found",
                                             "not found in " + target))
    return findings


def check_contract_gap(specs_root, cache, module_ids, artifact_filter=None):
    """Locates a Contract surface / Consumer obligations table under each
    matching heading of every <specsRoot>/<MODULE>/{requirement,specify}.md and
    validates its Owner/Consumer FR column. Only the first table per matching
    heading is inspected (this kit's templates carry exactly one).
    `artifact_filter`, if given, restricts which requirement.md/specify.md
    files are inspected (the --artifact CLI flag)."""
    findings = []
    if not specs_root or not os.path.isdir(specs_root):
        return findings
    for module_dir in sorted(os.listdir(specs_root)):
        mdir = os.path.join(specs_root, module_dir)
        if not os.path.isdir(mdir):
            continue
        for fname in ("requirement.md", "specify.md"):
            fpath = to_posix(os.path.join(mdir, fname))
            if not os.path.isfile(fpath):
                continue
            if artifact_filter is not None and fpath not in artifact_filter:
                continue
            lines = cache.lines(fpath)
            for idx, line in enumerate(lines):
                m = CONTRACT_HEADING_RE.match(line)
                if not m:
                    continue
                is_consumer = m.group(1).lower().startswith("consumer")
                level = len(re.match(r"^#{1,6}", line).group(0))
                start, end = section_bounds(lines, idx, level)
                table = find_first_table(lines, start, end)
                if not table:
                    continue
                header_line, header_cells, rows = table
                findings.extend(evaluate_contract_table(
                    fpath, header_line, header_cells, rows, is_consumer, module_ids, specs_root, cache))
    return findings


# ===========================================================================
# Check: deps (opt-in, stack-specific)
# ===========================================================================

TYPE_DECL_PATTERNS = {
    "cs": re.compile(r"\b(?:class|struct|interface|enum|record)\s+([A-Za-z_][A-Za-z0-9_]*)"),
    "go": re.compile(r"\btype\s+([A-Za-z_][A-Za-z0-9_]*)\b"),
}

IDENT_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
MODULE_ID_LINE_RE = re.compile(r'"id"\s*:\s*"([^"]+)"')


def strip_comments_and_strings(src):
    """// and /* */ comments, C-style "..." strings (with \\ escapes and $-
    interpolation), C# verbatim @"..." strings, and Go raw `...` strings."""
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    src = re.sub(r"//[^\n]*", " ", src)
    src = re.sub(r'@"(?:[^"]|"")*"', '""', src)
    src = re.sub(r'\$?"(?:\\.|[^"\\\n])*"', '""', src)
    src = re.sub(r"`[^`]*`", "``", src)
    return src


def module_of_path(path, module_paths):
    """module_paths: [(module_id, owned_path, is_file)]. Longest-prefix wins;
    a single-file entry matches only that exact file."""
    best_id, best_len = None, -1
    for mid, owned, is_file in module_paths:
        if is_file:
            if path == owned and len(owned) > best_len:
                best_id, best_len = mid, len(owned)
        else:
            if (path == owned or path.startswith(owned + "/")) and len(owned) > best_len:
                best_id, best_len = mid, len(owned)
    return best_id


def locate_module_lines(matrix_path, cache):
    result = {}
    for i, line in enumerate(cache.lines(matrix_path), start=1):
        m = MODULE_ID_LINE_RE.search(line)
        if m and m.group(1) not in result:
            result[m.group(1)] = i
    return result


def check_deps(code_roots, modules, matrix_path, cache):
    """Actual A->B edge = a file owned by module A references an identifier
    equal to a type declared by module B (types owned by >1 module are
    ambiguous, ignored). Compared against modules[].deps/plannedDeps. Only
    files whose extension is in SOURCE_EXTS are considered "code" at all;
    among those, extensions without a type-decl regex are reported once as
    deps-unsupported rather than silently skipped."""
    findings = []
    if modules is None or matrix_path is None:
        return findings

    module_paths = []
    for m in modules:
        owned = m.get("paths") or [m.get("path")]
        for p in owned:
            if p:
                module_paths.append((m["id"], to_posix(p), os.path.isfile(p)))

    all_files = []
    for root in code_roots:
        for dirpath, _dirnames, filenames in os.walk(root):
            for fn in filenames:
                all_files.append(to_posix(os.path.join(dirpath, fn)))

    by_ext = collections.defaultdict(list)
    unsupported_exts = set()
    for f in all_files:
        ext = f.rsplit(".", 1)[-1].lower() if "." in f else ""
        if ext not in SOURCE_EXTS:
            continue
        if ext in TYPE_DECL_PATTERNS:
            by_ext[ext].append(f)
        else:
            unsupported_exts.add(ext)

    owned_types = collections.defaultdict(set)
    cleaned = {}
    file_module = {}
    for ext, files in by_ext.items():
        pat = TYPE_DECL_PATTERNS[ext]
        for f in files:
            mid = module_of_path(f, module_paths)
            file_module[f] = mid
            src = strip_comments_and_strings(cache.text(f))
            cleaned[f] = src
            if mid:
                owned_types[mid].update(pat.findall(src))

    type_to_modules = collections.defaultdict(set)
    for mid, types in owned_types.items():
        for t in types:
            type_to_modules[t].add(mid)
    ambiguous_types = set(t for t, mids in type_to_modules.items() if len(mids) > 1)

    actual = collections.defaultdict(lambda: collections.defaultdict(set))
    for f, src in cleaned.items():
        mid = file_module.get(f)
        if not mid:
            continue
        ids_in_file = set(IDENT_TOKEN_RE.findall(src))
        for other_mid, types in owned_types.items():
            if other_mid == mid:
                continue
            hit = (ids_in_file & types) - ambiguous_types
            if hit:
                actual[mid][other_mid] |= hit

    module_line = locate_module_lines(matrix_path, cache)

    for m in modules:
        mid = m["id"]
        declared = set(m.get("deps", []))
        planned = set(m.get("plannedDeps", []))
        actual_deps = set(actual[mid].keys())
        for other in sorted(actual_deps - declared):
            detail = "types: " + ", ".join(sorted(actual[mid][other]))
            if other in planned:
                detail += " — planned edge now in code, promote"
            findings.append(Finding(matrix_path, module_line.get(mid), mid + " -> " + other,
                                     "dep-undeclared", detail=detail))
        for other in sorted(declared - actual_deps):
            findings.append(Finding(matrix_path, module_line.get(mid), mid + " -> " + other,
                                     "dep-declared-not-in-code"))

    if unsupported_exts:
        findings.append(Finding(matrix_path, None, "", "deps-unsupported", detail=(
            "extensions with no type-decl regex, skipped: " + ", ".join(sorted(unsupported_exts)))))
    return findings


# ===========================================================================
# --reanchor: legacy line anchor -> symbol cite
# ===========================================================================

MODIFIER_WORDS = set("""
public private protected internal static readonly virtual override abstract
sealed partial async unsafe extern new const volatile event in out ref this
""".split())

REJECT_KEYWORDS = set("""
if for foreach while switch using lock catch fixed checked unchecked try
else do finally case default when namespace return break continue throw
yield goto
""".split())

ACCESSOR_RE = re.compile(r"^(get|set|add|remove|init)\s*;?$")
CS_TYPE_RE = re.compile(r"\b(class|struct|interface|enum|record)\s+([A-Za-z_][A-Za-z0-9_]*)")


def strip_attributes(header):
    return re.sub(r"\[[^\[\]]*\]", " ", header)


def _last_ident(text):
    m = re.search(r"([A-Za-z_]\w*)$", text.strip())
    return m.group(1) if m else None


def paren_owner_name(rest):
    """Identifier immediately before the first top-level '(' in `rest`, i.e. the
    declared name of a method/constructor/indexer header — but only if that
    identifier is NOT itself a member-access target (`x.Method(` is a call, not
    a declaration)."""
    idx = rest.find("(")
    if idx == -1:
        return None
    before = rest[:idx].rstrip()
    before = re.sub(r"<[^<>]*>$", "", before).rstrip()
    if not before or before.endswith("."):
        return None
    m = re.search(r"([A-Za-z_]\w*)$", before)
    if not m:
        return None
    if m.start() > 0 and before[m.start() - 1] == ".":
        return None
    return m.group(1)


def prep_header(header):
    h = strip_attributes(header)
    words = h.split()
    i = 0
    while i < len(words) and words[i] in MODIFIER_WORDS:
        i += 1
    rest_words = words[i:]
    if not rest_words or rest_words[0] in REJECT_KEYWORDS:
        return None, None
    return rest_words, " ".join(rest_words)


def classify_header_cs_brace(header):
    """Classify the text since the last terminator, for a brace it opens.
    -> ('type', name) | ('member', name) | ('other', None)."""
    tm = CS_TYPE_RE.search(strip_attributes(header))
    if tm:
        return "type", tm.group(2)
    rest_words, rest = prep_header(header)
    if rest is None:
        return "other", None
    if ACCESSOR_RE.match(rest):
        return "other", None
    if "=>" in rest or "=" in rest:
        return "other", None
    name = paren_owner_name(rest)
    if name:
        return "member", name
    if "(" in rest or ")" in rest:
        return "other", None
    last = rest_words[-1]
    if re.match(r"^[A-Za-z_]\w*$", last):
        return "member", last
    return "other", None


def classify_header_cs_semi(header):
    """Classify a `;`-terminated, brace-less statement at type-body level:
    a plain field, an auto field with initializer, or an expression-bodied
    member. -> name or None. "=>" / "=" are checked BEFORE a bare "(" search,
    since a field initializer like `owned_skins = new();` contains a paren
    that belongs to the initializer expression, not to the declared name."""
    rest_words, rest = prep_header(header)
    if rest is None:
        return None
    if "=>" in rest:
        before = rest.split("=>")[0]
        return paren_owner_name(before) if "(" in before else _last_ident(before)
    if "=" in rest:
        before = rest.split("=")[0]
        return paren_owner_name(before) if "(" in before else _last_ident(before)
    if "(" in rest:
        return paren_owner_name(rest)
    last = rest_words[-1].rstrip(",;")
    return last if re.match(r"^[A-Za-z_]\w*$", last) else None


def scan_cs_symbols(lines):
    """Heuristic brace-depth walk over cleaned (.cs comments/strings blanked)
    lines. -> [('type', Name, start, end), ('member', 'Type.Member', start, end)].
    A field/property/expression-bodied member with no brace body becomes a
    zero-width region at its own declaration line; a nested member inside an
    already-open member (e.g. a local function) stays attributed to the outer
    member rather than creating its own symbol."""
    frames = []
    stack = []
    type_stack = []
    header_buf = []
    header_start = [None]

    def has_member_context():
        for fr in reversed(stack):
            if fr["kind"] in ("type", "member"):
                return fr["kind"] == "member"
        return False

    def header_text():
        return "".join(header_buf)

    def reset_header():
        del header_buf[:]
        header_start[0] = None

    for lineno, raw in enumerate(lines, start=1):
        for ch in raw:
            if ch == "{":
                header = header_text()
                kind, name = classify_header_cs_brace(header)
                if kind == "member" and has_member_context():
                    kind, name = "other", None
                stack.append({"kind": kind, "name": name,
                              "start": header_start[0] if header_start[0] else lineno,
                              "type_name": type_stack[-1] if type_stack else None})
                if kind == "type":
                    type_stack.append(name)
                reset_header()
            elif ch == "}":
                if stack:
                    frame = stack.pop()
                    if frame["kind"] == "type":
                        if type_stack and type_stack[-1] == frame["name"]:
                            type_stack.pop()
                        frames.append(("type", frame["name"], frame["start"], lineno))
                    elif frame["kind"] == "member" and frame["type_name"]:
                        frames.append(("member", frame["type_name"] + "." + frame["name"],
                                       frame["start"], lineno))
                reset_header()
            elif ch == ";":
                if type_stack and not has_member_context():
                    name = classify_header_cs_semi(header_text())
                    if name:
                        frames.append(("member", type_stack[-1] + "." + name, lineno, lineno))
                reset_header()
            else:
                if not ch.isspace():
                    if header_start[0] is None:
                        header_start[0] = lineno
                    header_buf.append(ch)
                elif header_buf and header_buf[-1] != " ":
                    header_buf.append(" ")
    return frames


def _brace_match_line(lines, start_idx):
    depth, started = 0, False
    for idx in range(start_idx, len(lines)):
        for ch in lines[idx]:
            if ch == "{":
                depth += 1
                started = True
            elif ch == "}":
                depth -= 1
                if started and depth == 0:
                    return idx + 1
    return len(lines)


GO_METHOD_RE = re.compile(r"^\s*func\s*\(\s*\w+\s+\*?([A-Za-z_]\w*)\s*\)\s*([A-Za-z_]\w*)\s*\(")
GO_FUNC_RE = re.compile(r"^\s*func\s+([A-Za-z_]\w*)\s*\(")
GO_TYPE_RE = re.compile(r"^\s*type\s+([A-Za-z_]\w*)\s+(?:struct|interface)\s*\{")
GO_FIELD_RE = re.compile(r"^\s*([A-Za-z_]\w*)\s+\S")


def scan_go_symbols(lines):
    """Best-effort Go scan: `func (r *T) Name(` -> T.Name, `func Name(` -> Name,
    `type T struct { ... }` fields -> T.Field. Go funcs are not lexically
    nested in their receiver's type block, so this is line-oriented rather
    than a shared brace-stack with the C# scanner."""
    frames = []
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        m = GO_METHOD_RE.match(line)
        if m:
            end = _brace_match_line(lines, i)
            frames.append(("member", m.group(1) + "." + m.group(2), i + 1, end))
            i = end
            continue
        m = GO_FUNC_RE.match(line)
        if m:
            end = _brace_match_line(lines, i)
            frames.append(("member", m.group(1), i + 1, end))
            i = end
            continue
        m = GO_TYPE_RE.match(line)
        if m:
            type_name = m.group(1)
            end = _brace_match_line(lines, i)
            frames.append(("type", type_name, i + 1, end))
            for j in range(i + 1, end - 1):
                fm = GO_FIELD_RE.match(lines[j])
                if fm and "{" not in lines[j] and "}" not in lines[j]:
                    frames.append(("member", type_name + "." + fm.group(1), j + 1, j + 1))
            i = end
            continue
        i += 1
    return frames


SCANNERS = {"cs": scan_cs_symbols, "go": scan_go_symbols}


ATTR_ONLY_RE = re.compile(r"^\[[^\[\]]*\]\s*")
BRACE_ONLY_RE = re.compile(r"^[{}]+[;,]?$")


def is_decorative_line(cleaned_line):
    """True for a line that carries no citable content of its own: blank,
    comment-only (already blanked by strip_comments_and_strings), attribute-only
    (`[Foo]`, possibly several back to back), or brace-only (`{` / `}` alone).
    Used by group_reanchor_symbols to decide whether a line a range "hits", but
    that carries no member of its own, should still count as evidence that the
    range touches the type at large."""
    s = cleaned_line.strip()
    if not s:
        return True
    while True:
        stripped = ATTR_ONLY_RE.sub("", s).strip()
        if stripped == s:
            break
        s = stripped
    if not s:
        return True
    return bool(BRACE_ONLY_RE.match(s))


def group_reanchor_symbols(ranges, member_regions, type_regions, cleaned_lines):
    """Per cite (all its ranges together), grouped by type: a type's hits
    collapse to bare `Type` when the cite hits no member of it, hits more than
    2 distinct members of it, or hits a type-level line of it that is not a
    member declaration -- ignoring blank/comment/attribute/brace-only lines
    that sit strictly between two hit members (a decorative separator, not
    evidence the cite means "the type at large"); a decorative line outside
    that inner span (e.g. the type's own header/opening/closing brace) still
    counts, since it is the type's own structural boundary. Otherwise the 1-2
    hit members are listed. -> ordered list of 'Type' / 'Type.Member' strings,
    no duplicates, in source (type-scan) order."""
    all_lines = sorted(set(ln for a, b in ranges for ln in range(a, b + 1)))
    if not all_lines:
        return []

    members_by_type = collections.defaultdict(list)
    for name, s, e in member_regions:
        members_by_type[name.split(".", 1)[0]].append((name, s, e))

    out = []
    seen_types = set()
    for tname, tstart, tend in type_regions:
        if tname in seen_types:
            continue
        hit = [ln for ln in all_lines if tstart <= ln <= tend]
        if not hit:
            continue
        seen_types.add(tname)

        hit_members, member_spans = [], []
        for mname, ms, me in members_by_type.get(tname, []):
            if mname not in hit_members and any(ms <= ln <= me for ln in hit):
                hit_members.append(mname)
                member_spans.append((ms, me))

        if not hit_members:
            out.append(tname)
            continue

        covered = set(ln for ln in hit if any(ms <= ln <= me for ms, me in member_spans))
        uncovered = [ln for ln in hit if ln not in covered]
        interior_lo = min(ms for ms, me in member_spans)
        interior_hi = max(me for ms, me in member_spans)
        significant = [ln for ln in uncovered
                       if ln < interior_lo or ln > interior_hi
                       or not is_decorative_line(cleaned_lines[ln - 1])]

        if len(hit_members) > 2 or significant:
            out.append(tname)
        else:
            out.extend(hit_members)
    return out


def build_reanchor_proposals(legacy_details, cache, touched):
    """For every collected legacy-line-anchor, propose `path::Symbol[, ...]`
    per group_reanchor_symbols. -> (proposals, unsupported_findings).
    proposals: [{artifact,line,old,new}]."""
    proposals = []
    unsupported = []
    if not legacy_details:
        return proposals, unsupported
    touched_set = set(to_posix(t) for t in touched) if touched else None

    region_cache = {}
    for item in legacy_details:
        path = item["path"]
        if touched_set is not None and path not in touched_set:
            continue
        ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
        scanner = SCANNERS.get(ext)
        if scanner is None:
            unsupported.append(Finding(item["artifact"], item["line"], item["cite"], "reanchor-unsupported"))
            continue
        if path not in region_cache:
            cleaned_lines = [strip_comments_and_strings(l) for l in cache.lines(path)]
            frames = scanner(cleaned_lines)
            region_cache[path] = (
                [(n, s, e) for k, n, s, e in frames if k == "member"],
                [(n, s, e) for k, n, s, e in frames if k == "type"],
                cleaned_lines,
            )
        member_regions, type_regions, cleaned_lines = region_cache[path]

        symbols = group_reanchor_symbols(item["ranges"], member_regions, type_regions, cleaned_lines)

        if not symbols:
            unsupported.append(Finding(item["artifact"], item["line"], item["cite"], "reanchor-unsupported"))
            continue

        text = cache.text(path)
        verified = []
        ok = True
        for sym in symbols:
            for part in sym.split("."):
                if not re.search(r"\b" + re.escape(part) + r"\b", text):
                    ok = False
                    break
            if not ok:
                break
            verified.append(path + "::" + sym)
        if not ok:
            unsupported.append(Finding(item["artifact"], item["line"], item["cite"], "reanchor-unsupported"))
            continue

        new_text = ", ".join(verified)
        proposals.append({"artifact": item["artifact"], "line": item["line"],
                           "old": item["cite"], "new": new_text})
    return proposals, unsupported


def apply_reanchor_writes(proposals):
    """Exact text-span replacement on each proposal's line, byte-preserving
    everything else (own newline style kept via splitlines(keepends=True)).
    For modules.json, verifies the result still parses as JSON before writing;
    on failure that artifact's edits are dropped entirely (original untouched)."""
    by_artifact = collections.defaultdict(list)
    for p in proposals:
        by_artifact[p["artifact"]].append(p)
    applied = []
    for artifact, props in by_artifact.items():
        with open(artifact, "rb") as f:
            raw = f.read()
        text = raw.decode("utf-8", errors="replace")
        raw_lines = text.splitlines(keepends=True)
        local_applied = []
        for p in sorted(props, key=lambda x: x["line"]):
            idx = p["line"] - 1
            if 0 <= idx < len(raw_lines) and p["old"] in raw_lines[idx]:
                raw_lines[idx] = raw_lines[idx].replace(p["old"], p["new"], 1)
                local_applied.append(p)
        if not local_applied:
            continue
        new_text = "".join(raw_lines)
        if artifact.endswith(".json"):
            try:
                json.loads(new_text)
            except ValueError:
                continue
        with open(artifact, "wb") as f:
            f.write(new_text.encode("utf-8"))
        applied.extend(local_applied)
    return applied


# ===========================================================================
# --refresh-status / --render / --inventory: shared primitives
# ===========================================================================

def matrix_json_path(cfg):
    root = cfg.get("matrixRoot")
    if not root:
        return None
    return to_posix(os.path.join(root, "modules.json"))


def parse_frontmatter(lines):
    """Simple line-based parse of a leading '---' YAML frontmatter block (no
    yaml lib). Tolerates a quoted value ('...' or "...") and a trailing
    `# comment`. Returns {} when the file has no frontmatter block."""
    if not lines or lines[0].strip() != "---":
        return {}
    fm = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        m = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*)$', line)
        if not m:
            continue
        key, raw_val = m.group(1), m.group(2).strip()
        if raw_val[:1] in ("'", '"'):
            qm = re.match(r"""(['"])(.*?)\1""", raw_val)
            val = qm.group(2) if qm else raw_val
        else:
            val = raw_val.split(" #", 1)[0].strip()
        fm[key] = val
    return fm


def frontmatter_of(path, cache):
    if not path or not os.path.isfile(path):
        return {}
    return parse_frontmatter(cache.lines(path))


VERDICT_HEADING_RE = re.compile(r"^#{1,6}\s*Verdict\b", re.IGNORECASE)
VERDICT_TOKEN_RE = re.compile(r"\b(PASS-WITH-FINDINGS|PASS|FAIL)\b")


def extract_verdict(lines, frontmatter):
    """Frontmatter `verdict:` wins when present (trusted verbatim, whatever it
    says). Else, legacy fallback: scan the lines after a `## Verdict` heading
    (stopping at the next heading) for the first PASS-WITH-FINDINGS / PASS /
    FAIL token. -> verdict string, or None when unreadable (callers treat None
    as "not FAIL")."""
    fv = frontmatter.get("verdict")
    if fv:
        return fv.strip()
    for i, line in enumerate(lines):
        if VERDICT_HEADING_RE.match(line):
            for l2 in lines[i + 1:]:
                if HEADING_RE.match(l2):
                    break
                m = VERDICT_TOKEN_RE.search(l2)
                if m:
                    return m.group(1)
            break
    return None


def find_module_reports(module_id, audit_root, cache):
    """Direct children of `audit_root` named '<module_id>-*.md' whose
    frontmatter marks them as a module audit report (job: code-audit + mode:
    module, or legacy job: module-audit). Disambiguates ids where one prefixes
    another (e.g. UI vs UI-Shop) via frontmatter `module:` when present, else
    requires the remainder after '<module_id>-' to start with a digit (the
    report's own date-stamp convention). -> [(path, frontmatter, lines), ...]."""
    if not audit_root or not os.path.isdir(audit_root):
        return []
    prefix = module_id + "-"
    out = []
    for name in sorted(os.listdir(audit_root)):
        if not (name.startswith(prefix) and name.endswith(".md")):
            continue
        full = to_posix(os.path.join(audit_root, name))
        if not os.path.isfile(full):
            continue
        lines = cache.lines(full)
        fm = parse_frontmatter(lines)
        job, mode = fm.get("job"), fm.get("mode")
        if not ((job == "code-audit" and mode == "module") or job == "module-audit"):
            continue
        fm_module = fm.get("module")
        if fm_module:
            if fm_module != module_id:
                continue
        elif not name[len(prefix):len(prefix) + 1].isdigit():
            continue
        out.append((full, fm, lines))
    return out


def module_audit_status(module_id, audit_root, cache):
    """-> (verdict_or_None, report_path_or_None) for the LATEST module audit
    report matching `module_id` (see find_module_reports). Latest = greatest
    frontmatter `date` (ISO string compare); a report with no date falls back
    to comparing its filename."""
    reports = find_module_reports(module_id, audit_root, cache)
    if not reports:
        return None, None
    path, fm, lines = max(reports, key=lambda r: r[1].get("date") or os.path.basename(r[0]))
    return extract_verdict(lines, fm), path


TASK_LINE_RE = re.compile(r"^\s*- \[.\]")
UNCHECKED_TASK_RE = re.compile(r"^\s*- \[ \]")


def count_tasks(lines):
    """-> (open_count, total_count) of markdown checkbox task lines."""
    total = sum(1 for l in lines if TASK_LINE_RE.match(l))
    open_n = sum(1 for l in lines if UNCHECKED_TASK_RE.match(l))
    return open_n, total


def spec_folder_of(module, specs_root):
    sf = module.get("spec")
    if sf:
        return to_posix(sf)
    if specs_root:
        return to_posix(os.path.join(specs_root, module["id"]))
    return None


def module_has_source(module):
    """(a) of the --refresh-status `implemented` row: at least one file whose
    extension is in SOURCE_EXTS exists under any of module['paths'] (fallback
    [module['path']]) -- an entry may be a folder or a single file."""
    entries = module.get("paths") or ([module.get("path")] if module.get("path") else [])
    for entry in entries:
        if not entry:
            continue
        entry = to_posix(entry)
        if os.path.isfile(entry):
            ext = entry.rsplit(".", 1)[-1].lower() if "." in entry else ""
            if ext in SOURCE_EXTS:
                return True
        elif os.path.isdir(entry):
            for _dirpath, _dirnames, filenames in os.walk(entry):
                for fn in filenames:
                    ext = fn.rsplit(".", 1)[-1].lower() if "." in fn else ""
                    if ext in SOURCE_EXTS:
                        return True
    return False


def tasks_status(spec_folder, cache):
    """-> (satisfied_bool, evidence_str) for (b) of the `implemented` row:
    <spec folder>/tasks.md missing counts as satisfied; present counts open
    (unchecked, `^\\s*- \\[ \\]`) task lines."""
    if not spec_folder:
        return True, "absent"
    path = to_posix(os.path.join(spec_folder, "tasks.md"))
    if not os.path.isfile(path):
        return True, "absent"
    open_n, _total_n = count_tasks(cache.lines(path))
    if open_n == 0:
        return True, "all-checked"
    return False, "{}-open".format(open_n)


def derive_module_status(module, cfg, cache):
    """First-matching-row status derivation for --refresh-status: implemented
    (source + tasks + audit-not-FAIL) > planned (plan.md approved: true) >
    specced (requirement.md exists) > proposed. -> (status, evidence_line)."""
    mid = module["id"]
    specs_root = cfg.get("specsRoot")
    spec_folder = spec_folder_of(module, specs_root)

    has_source = module_has_source(module)
    tasks_ok, tasks_evi = tasks_status(spec_folder, cache)
    verdict, report_path = module_audit_status(mid, cfg.get("auditReportRoot"), cache)
    audit_ok = verdict != "FAIL"
    audit_evi = "none" if report_path is None else "{}@{}".format(
        verdict if verdict is not None else "unreadable", report_path)

    plan_path = to_posix(os.path.join(spec_folder, "plan.md")) if spec_folder else None
    approved = frontmatter_of(plan_path, cache).get("approved", "").strip().lower() == "true"
    req_path = to_posix(os.path.join(spec_folder, "requirement.md")) if spec_folder else None
    has_req = bool(req_path and os.path.isfile(req_path))

    if has_source and tasks_ok and audit_ok:
        status = "implemented"
    elif approved:
        status = "planned"
    elif has_req:
        status = "specced"
    else:
        status = "proposed"

    evidence = "source={} tasks={} audit={} plan={} requirement={}".format(
        "yes" if has_source else "no", tasks_evi, audit_evi,
        "approved" if approved else "no", "yes" if has_req else "no")
    return status, evidence


def find_enclosing_object(text, anchor_pos):
    """Smallest {...} JSON object in `text` that contains `anchor_pos`, quote-
    aware (a string value may itself contain '{' or '}'). -> (start, end)
    char offsets ([start,end), '}' included) or None."""
    stack = []
    in_str = False
    escape = False
    best = None
    for i, ch in enumerate(text):
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            stack.append(i)
        elif ch == "}":
            if not stack:
                continue
            start = stack.pop()
            if start <= anchor_pos <= i and (best is None or (i - start) < (best[1] - best[0])):
                best = (start, i + 1)
    return best


def replace_status_value(text, module_id, new_status):
    """Targeted, byte-preserving replacement of one module object's "status"
    JSON value. -> new_text, or None when not (uniquely) possible: the
    `"id": "<module_id>"` line isn't found exactly once, its enclosing object
    can't be located, or that object carries no "status" key."""
    id_pat = re.compile(r'"id"\s*:\s*' + re.escape(json.dumps(module_id)))
    matches = list(id_pat.finditer(text))
    if len(matches) != 1:
        return None
    obj = find_enclosing_object(text, matches[0].start())
    if obj is None:
        return None
    obj_start, obj_end = obj
    obj_text = text[obj_start:obj_end]
    m = re.search(r'"status"\s*:\s*("(?:[^"\\]|\\.)*")', obj_text)
    if not m:
        return None
    new_obj_text = obj_text[:m.start(1)] + json.dumps(new_status) + obj_text[m.end(1):]
    return text[:obj_start] + new_obj_text + text[obj_end:]


def apply_status_writes(matrix_path, changes):
    """Apply --refresh-status --write: for each (module_id, new_status) in
    `changes`, attempt replace_status_value in turn. If ANY change can't be
    made that way, ALL targeted edits are abandoned and the whole file is
    instead rewritten via json.dump(indent=2, ensure_ascii=False) with every
    changed module's status updated in memory first. -> reformatted_bool."""
    with open(matrix_path, "rb") as f:
        raw = f.read()
    original_text = raw.decode("utf-8", errors="replace")
    text = original_text
    ok = True
    for module_id, new_status in changes:
        new_text = replace_status_value(text, module_id, new_status)
        if new_text is None:
            ok = False
            break
        text = new_text
    if ok:
        with open(matrix_path, "wb") as f:
            f.write(text.encode("utf-8"))
        return False

    data = json.loads(original_text)
    by_id = {m["id"]: m for m in data.get("modules", []) if isinstance(m, dict) and "id" in m}
    for module_id, new_status in changes:
        if module_id in by_id:
            by_id[module_id]["status"] = new_status
    with open(matrix_path, "wb") as f:
        f.write((json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    return True


def run_refresh_status(args, cfg, cache):
    matrix_root = cfg.get("matrixRoot")
    if not matrix_root:
        sys.stderr.write("ERROR: matrixRoot not configured\n")
        return 2
    matrix_path = matrix_json_path(cfg)
    if not os.path.isfile(matrix_path):
        sys.stderr.write("ERROR: modules.json not found: {}\n".format(matrix_path))
        return 2
    modules, module_ids = load_modules(matrix_path, cache)
    if modules is None:
        sys.stderr.write("ERROR: {} did not parse as {{\"modules\": [...]}}\n".format(matrix_path))
        return 2

    if args.refresh_status:
        requested = sorted(set(args.refresh_status))
        unknown = [m for m in requested if m not in module_ids]
        if unknown:
            sys.stderr.write("ERROR: unknown module id(s): {}\n".format(", ".join(unknown)))
            return 2
        target_ids = requested
    else:
        target_ids = sorted(module_ids)

    by_id = {m["id"]: m for m in modules if isinstance(m, dict) and "id" in m}
    results = []
    for mid in target_ids:
        module = by_id.get(mid)
        if module is None:
            continue
        new_status, evidence = derive_module_status(module, cfg, cache)
        old_status = module.get("status", "")
        results.append((mid, old_status, new_status, evidence))

    changes = [(mid, new) for mid, old, new, _ in results if new != old]

    reformatted = False
    render_path = None
    if args.write:
        if changes:
            reformatted = apply_status_writes(matrix_path, changes)
        fresh_cache = FileCache()
        try:
            data = json.loads(fresh_cache.text(matrix_path))
        except ValueError:
            data = None
        if isinstance(data, dict) and isinstance(data.get("modules"), list):
            render_path = render_modules_md(cfg, data)

    if args.json:
        report = {
            "mode": "refresh-status",
            "matrixPath": matrix_path,
            "modules": [{"id": mid, "old": old, "new": new, "changed": new != old, "evidence": evidence}
                        for mid, old, new, evidence in results],
            "written": bool(args.write and changes),
            "reformatted": reformatted,
            "renderedModulesMd": render_path,
        }
        json.dump(report, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
    else:
        for mid, old, new, evidence in results:
            if new != old:
                sys.stdout.write("{}: {} -> {}\n".format(mid, old if old else "(none)", new))
            else:
                sys.stdout.write("{}: unchanged ({})\n".format(mid, new))
            sys.stdout.write("  " + evidence + "\n")
        if args.write:
            if changes:
                sys.stdout.write("\nwrote {} status change(s) to {}\n".format(len(changes), matrix_path))
                if reformatted:
                    sys.stdout.write(
                        "note: targeted replacement was not possible for one or more modules "
                        "-- {} was reformatted (json.dump)\n".format(matrix_path))
            else:
                sys.stdout.write("\nno status changes to write\n")
            if render_path:
                sys.stdout.write("wrote {}\n".format(render_path))
    return 0


def escape_cell(s):
    return (s or "").replace("|", "\\|")


def render_modules_md(cfg, data):
    """Deterministic modules.md renderer for --render (and --refresh-status
    --write). Never writes a "now" timestamp -- re-rendering unchanged `data`
    must produce a byte-identical file. `data` is the parsed modules.json
    dict. -> path written."""
    matrix_root = cfg.get("matrixRoot")
    out_path = to_posix(os.path.join(matrix_root, "modules.md"))
    project = data.get("project") or ""
    generated = data.get("generated") or ""
    modules = [m for m in (data.get("modules") or []) if isinstance(m, dict)]

    counts = collections.Counter(m.get("status") or "proposed" for m in modules)
    status_line = "Status: implemented {} · planned {} · specced {} · proposed {}".format(
        counts.get("implemented", 0), counts.get("planned", 0),
        counts.get("specced", 0), counts.get("proposed", 0))

    by_layer = collections.defaultdict(list)
    for m in modules:
        by_layer[m.get("layer", 0)].append(m)

    def rel_link(target):
        if not target:
            return None
        return to_posix(os.path.relpath(target, matrix_root))

    def layer_key(l):
        return (0, l) if isinstance(l, (int, float)) and not isinstance(l, bool) else (1, str(l))

    lines = [
        "# Module matrix — {}".format(project),
        "",
        "> Generated by `ndv_check.py --render` from `modules.json` (generated: {}). "
        "Do not hand-edit — edit modules.json via /ndv-module-matrix.".format(generated),
        "",
        status_line,
        "",
    ]

    for layer in sorted(by_layer.keys(), key=layer_key):
        lines.append("## Layer {}".format(layer))
        lines.append("")
        lines.append("| Module | Status | Deps | Planned deps | Code | TDD | Spec |")
        lines.append("|---|---|---|---|---|---|---|")
        for m in sorted(by_layer[layer], key=lambda x: x.get("id", "")):
            mid = m.get("id", "")
            name = m.get("name")
            label = "`{}`".format(escape_cell(mid))
            if name and name != mid:
                label += " " + escape_cell(name)
            status = escape_cell(m.get("status") or "—")
            deps = [d for d in (m.get("deps") or []) if d]
            deps_cell = ", ".join("`{}`".format(escape_cell(d)) for d in deps) if deps else "—"
            planned = [d for d in (m.get("plannedDeps") or []) if d]
            planned_cell = ", ".join("`{}`".format(escape_cell(d)) for d in planned) if planned else "—"
            path = m.get("path")
            code_cell = "[{}]({})".format(escape_cell(path), rel_link(path)) if path else "—"
            tdd = m.get("tdd")
            tdd_cell = "[tdd]({})".format(rel_link(tdd)) if tdd else "—"
            spec = m.get("spec")
            spec_cell = "[spec]({})".format(rel_link(spec)) if spec else "—"
            lines.append("| {} | {} | {} | {} | {} | {} | {} |".format(
                label, status, deps_cell, planned_cell, code_cell, tdd_cell, spec_cell))
        lines.append("")

    content = "\n".join(lines).rstrip("\n") + "\n"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)
    return out_path


def run_render(args, cfg, cache):
    matrix_root = cfg.get("matrixRoot")
    if not matrix_root:
        sys.stderr.write("ERROR: matrixRoot not configured\n")
        return 2
    matrix_path = matrix_json_path(cfg)
    if not os.path.isfile(matrix_path):
        sys.stderr.write("ERROR: modules.json not found: {}\n".format(matrix_path))
        return 2
    try:
        data = json.loads(cache.text(matrix_path))
    except ValueError as e:
        sys.stderr.write("ERROR: invalid JSON in {}: {}\n".format(matrix_path, e))
        return 2
    if not isinstance(data, dict) or not isinstance(data.get("modules"), list):
        sys.stderr.write("ERROR: {} did not parse as {{\"modules\": [...]}}\n".format(matrix_path))
        return 2
    out_path = render_modules_md(cfg, data)
    if args.json:
        json.dump({"mode": "render", "written": out_path}, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
    else:
        sys.stdout.write("wrote {}\n".format(out_path))
    return 0


def build_module_paths(modules):
    """[(module_id, owned_path, is_file)] from modules[].paths (fallback
    [path]) -- same construction check_deps uses internally, kept separate
    here so this read-only mode never shares mutable state with it."""
    module_paths = []
    for m in modules or []:
        if not isinstance(m, dict) or "id" not in m:
            continue
        owned = m.get("paths") or [m.get("path")]
        for p in owned:
            if p:
                module_paths.append((m["id"], to_posix(p), os.path.isfile(p)))
    return module_paths


def immediate_subdirs(root):
    if not root or not os.path.isdir(root):
        return []
    out = []
    for name in sorted(os.listdir(root)):
        full = to_posix(os.path.join(root, name))
        if os.path.isdir(full):
            out.append((name, full))
    return out


def contains_source_file(folder):
    for _dirpath, _dirnames, filenames in os.walk(folder):
        for fn in filenames:
            ext = fn.rsplit(".", 1)[-1].lower() if "." in fn else ""
            if ext in SOURCE_EXTS:
                return True
    return False


ESTATE_DOC_ROOTS = ("gddRoot", "tddRoot", "specsRoot", "matrixRoot", "rulesRoot", "auditReportRoot")


def estate_rows(cfg):
    """[(label, path_or_None, exists_bool, count, unit), ...] -- one row per
    single doc root (count = recursive *.md files) plus one row per codeRoots
    entry (count = recursive files with an extension in SOURCE_EXTS)."""
    rows = []
    for label in ESTATE_DOC_ROOTS:
        root = cfg.get(label)
        exists = bool(root) and os.path.isdir(root)
        rows.append((label, root, exists, len(glob_md(root)) if exists else 0, "*.md"))
    for root in (cfg.get("codeRoots") or []):
        root_p = to_posix(root)
        exists = os.path.isdir(root_p)
        count = 0
        if exists:
            for _dirpath, _dirnames, filenames in os.walk(root_p):
                for fn in filenames:
                    ext = fn.rsplit(".", 1)[-1].lower() if "." in fn else ""
                    if ext in SOURCE_EXTS:
                        count += 1
        rows.append(("codeRoot", root_p, exists, count, "source files"))
    return rows


def coverage_row_cells(label, mid, spec_folder, code_display, registered, tdd_path, cfg, cache, matrix_path):
    """9 coverage-matrix cells for one row (Module, Code, Matrix entry, TDD,
    requirement, specify, plan, tasks, Audit report). `label` is the display
    name used when there's no module id (spec-only / unregistered rows).
    `code_display`, if given, is shown verbatim in the Code cell."""
    module_cell = "`{}`".format(escape_cell(mid)) if mid else escape_cell(label)
    code_cell = "✔ {}".format(escape_cell(code_display)) if code_display else "—"
    matrix_cell = "✔ {}".format(escape_cell(matrix_path)) if registered and matrix_path else "—"
    tdd_cell = ("✔ {}".format(escape_cell(tdd_path))
                if tdd_path and os.path.isfile(tdd_path) else "—")

    if spec_folder:
        req_path = to_posix(os.path.join(spec_folder, "requirement.md"))
        specify_path = to_posix(os.path.join(spec_folder, "specify.md"))
        plan_path = to_posix(os.path.join(spec_folder, "plan.md"))
        tasks_path = to_posix(os.path.join(spec_folder, "tasks.md"))
        req_cell = "✔ {}".format(escape_cell(req_path)) if os.path.isfile(req_path) else "—"
        specify_cell = "✔ {}".format(escape_cell(specify_path)) if os.path.isfile(specify_path) else "—"
        approved = frontmatter_of(plan_path, cache).get("approved", "").strip().lower() == "true"
        if os.path.isfile(plan_path):
            plan_cell = ("✔ {} (approved)".format(escape_cell(plan_path)) if approved
                         else "✔ {}".format(escape_cell(plan_path)))
        else:
            plan_cell = "—"
        if os.path.isfile(tasks_path):
            open_n, total_n = count_tasks(cache.lines(tasks_path))
            annot = ("approved, " if approved else "") + "{}/{} open".format(open_n, total_n)
            tasks_cell = "✔ {} ({})".format(escape_cell(tasks_path), annot)
        else:
            tasks_cell = "—"
    else:
        req_cell = specify_cell = plan_cell = tasks_cell = "—"

    audit_cell = "—"
    if mid:
        verdict, report_path = module_audit_status(mid, cfg.get("auditReportRoot"), cache)
        if report_path:
            audit_cell = "✔ {} ({})".format(
                escape_cell(report_path), verdict if verdict is not None else "unreadable")

    return [module_cell, code_cell, matrix_cell, tdd_cell, req_cell, specify_cell, plan_cell, tasks_cell, audit_cell]


def run_inventory(args, cfg, cache):
    notes = []
    matrix_path = matrix_json_path(cfg)
    modules = []
    if matrix_path and os.path.isfile(matrix_path):
        loaded_modules, _ids = load_modules(matrix_path, cache)
        if loaded_modules is None:
            notes.append("{} present but did not parse as {{\"modules\": [...]}} "
                         "-- module rows degrade to spec/code-only coverage".format(matrix_path))
        else:
            modules = loaded_modules
    else:
        notes.append("{} -- module rows degrade to spec/code-only coverage".format(
            "modules.json not found: " + matrix_path if matrix_path else "matrixRoot not configured"))

    specs_root = cfg.get("specsRoot")
    module_paths = build_module_paths(modules)
    module_specs = set()
    for m in modules:
        if isinstance(m, dict) and "id" in m:
            sf = spec_folder_of(m, specs_root)
            if sf:
                module_specs.add(sf)

    rows = []
    for m in sorted((mm for mm in modules if isinstance(mm, dict) and "id" in mm), key=lambda x: x["id"]):
        mid = m["id"]
        spec_folder = spec_folder_of(m, specs_root)
        code_display = m.get("path") or next((p for p in (m.get("paths") or []) if p), None)
        if not module_has_source(m):
            code_display = None  # same criterion as --refresh-status: a folder without source is not code
        rows.append(coverage_row_cells(mid, mid, spec_folder, code_display, True, m.get("tdd"),
                                        cfg, cache, matrix_path))

    for name, full in immediate_subdirs(specs_root):
        if full in module_specs:
            continue
        rows.append(coverage_row_cells("(spec only) " + name, None, full, None, False, None,
                                        cfg, cache, matrix_path))

    for root in [to_posix(r) for r in (cfg.get("codeRoots") or [])]:
        for name, full in immediate_subdirs(root):
            if not contains_source_file(full):
                continue
            if module_of_path(full, module_paths) is not None:
                continue
            rows.append(coverage_row_cells("(unregistered) " + full, None, None, full, False, None,
                                            cfg, cache, matrix_path))

    estate = estate_rows(cfg)

    if args.json:
        report = {
            "mode": "inventory",
            "estate": [{"root": label, "path": path, "exists": exists, "count": count, "unit": unit}
                       for label, path, exists, count, unit in estate],
            "coverageColumns": ["Module", "Code", "Matrix entry", "TDD", "requirement",
                                 "specify", "plan", "tasks", "Audit report"],
            "coverage": rows,
            "notes": notes,
        }
        json.dump(report, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
    else:
        out = sys.stdout
        out.write("# Artifact coverage\n\n")
        out.write("## Estate\n\n")
        out.write("| Root | Path | Exists | Count |\n")
        out.write("|---|---|---|---|\n")
        for label, path, exists, count, unit in estate:
            out.write("| {} | {} | {} | {} {} |\n".format(
                label, path or "—", "yes" if exists else "no", count, unit))
        out.write("\n## Coverage\n\n")
        out.write("| Module | Code | Matrix entry | TDD | requirement | specify | plan | tasks | Audit report |\n")
        out.write("|---|---|---|---|---|---|---|---|---|\n")
        for cells in rows:
            out.write("| " + " | ".join(cells) + " |\n")
        if notes:
            out.write("\n## notes\n\n")
            for n in notes:
                out.write("- " + n + "\n")
    return 0


# ===========================================================================
# Reporting
# ===========================================================================

CHECK_ORDER = ["doc-cite", "code-cite", "contract-gap", "deps"]


def print_text_report(findings_by_check, reanchor_proposals, reanchor_unsupported, notes, out):
    for check in CHECK_ORDER:
        if check not in findings_by_check:
            continue
        findings = findings_by_check[check]
        out.write("\n== {} ({} findings) ==\n".format(check, len(findings)))
        by_artifact = collections.defaultdict(list)
        for f in findings:
            by_artifact[f.artifact].append(f)
        out.write("{:<60} {}\n".format("artifact", "counts by status"))
        for art in sorted(by_artifact):
            counts = collections.Counter(f.status for f in by_artifact[art])
            summary = ", ".join("{}={}".format(k, v) for k, v in sorted(counts.items()))
            out.write("  {:<58} {}\n".format(art, summary))
        for art in sorted(by_artifact):
            out.write("-- {}\n".format(art))
            for f in sorted(by_artifact[art], key=lambda x: (x.line if x.line else 0)):
                loc = "{}:{}".format(art, f.line if f.line is not None else "-")
                label = f.status if f.kind == f.status else "{}/{}".format(f.status, f.kind)
                line = "  {:<50} {:<28} {}".format(loc, label, f.cite)
                if f.detail:
                    line += "  — " + f.detail
                out.write(line + "\n")

    if reanchor_proposals or reanchor_unsupported:
        out.write("\n== reanchor ({} proposals, {} unsupported) ==\n".format(
            len(reanchor_proposals), len(reanchor_unsupported)))
        for p in sorted(reanchor_proposals, key=lambda x: (x["artifact"], x["line"])):
            out.write("{}:{}: {} → {}\n".format(p["artifact"], p["line"], p["old"], p["new"]))
        for f in sorted(reanchor_unsupported, key=lambda x: (x.artifact, x.line or 0)):
            out.write("{}:{}: reanchor-unsupported  {}\n".format(f.artifact, f.line, f.cite))

    if notes:
        out.write("\n== notes ==\n")
        for n in notes:
            out.write("  " + n + "\n")

    all_findings = [f for fs in findings_by_check.values() for f in fs]
    broken = sum(1 for f in all_findings if f.status == "broken-cite")
    gaps = sum(1 for f in all_findings if f.status == "contract-gap")
    info = sum(1 for f in all_findings if f.status not in ("broken-cite", "contract-gap"))
    out.write("\nSUMMARY: {} broken-cite, {} contract-gap, {} informational, {} reanchor proposals\n".format(
        broken, gaps, info, len(reanchor_proposals)))


def build_json_report(findings_by_check, reanchor_proposals, reanchor_unsupported, notes):
    all_findings = [f for fs in findings_by_check.values() for f in fs] + reanchor_unsupported
    broken = sum(1 for f in all_findings if f.status == "broken-cite")
    gaps = sum(1 for f in all_findings if f.status == "contract-gap")
    return {
        "checksRun": [c for c in CHECK_ORDER if c in findings_by_check],
        "findings": [f.to_dict() for fs in findings_by_check.values() for f in fs],
        "reanchor": {
            "proposals": reanchor_proposals,
            "unsupported": [f.to_dict() for f in reanchor_unsupported],
        },
        "notes": notes,
        "summary": {
            "brokenCite": broken,
            "contractGap": gaps,
            "total": len(all_findings),
            "reanchorProposals": len(reanchor_proposals),
        },
    }


# ===========================================================================
# CLI
# ===========================================================================

VALID_CHECKS = ("doc-cite", "code-cite", "contract-gap", "deps")


def build_arg_parser():
    p = argparse.ArgumentParser(
        prog="ndv_check.py",
        description="Deterministic, read-only-by-default checker for ndvkit pipeline artifacts. "
                     "Run from the host repo root.",
    )
    p.add_argument("--config", default=".claude/ndvkit/ndvkit.config.json",
                    help="path to ndvkit.config.json (default: %(default)s)")
    p.add_argument("--checks", default="doc-cite,code-cite,contract-gap",
                    help="comma-separated subset of {} (default: %(default)s)".format(
                        ",".join(VALID_CHECKS)))
    p.add_argument("--touched", nargs="+", default=None, metavar="FILE",
                    help="restrict code-cite (and --reanchor) to cites resolving to these files")
    p.add_argument("--artifact", nargs="+", default=None, metavar="FILE",
                    help="restrict scanning (and --reanchor) to these repo-relative artifact "
                         "paths; combines with --touched as an intersection")
    p.add_argument("--reanchor", action="store_true",
                    help="dry-run conversion of legacy line anchors to symbol cites")
    p.add_argument("--refresh-status", nargs="*", default=None, metavar="MODULE",
                    help="standalone mode: dry-run derive modules.json status for the given "
                         "module ids (default: all modules) from code/tasks/audit/plan/"
                         "requirement evidence; combine with --write to apply")
    p.add_argument("--render", action="store_true",
                    help="standalone mode: write <matrixRoot>/modules.md from modules.json "
                         "(deterministic)")
    p.add_argument("--inventory", action="store_true",
                    help="standalone mode: read-only artifact coverage matrix + estate counts")
    p.add_argument("--write", action="store_true",
                    help="apply --reanchor changes in place, and/or apply --refresh-status "
                         "changes to modules.json (no-op without --reanchor/--refresh-status)")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    return p


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    requested = [c.strip() for c in args.checks.split(",") if c.strip()]
    if not requested or any(c not in VALID_CHECKS for c in requested):
        sys.stderr.write("ERROR: --checks must be a comma-separated subset of {}\n".format(
            ",".join(VALID_CHECKS)))
        return 2

    cfg = load_config(args.config)
    cache = FileCache()

    new_modes = [name for name, on in (
        ("--refresh-status", args.refresh_status is not None),
        ("--render", args.render),
        ("--inventory", args.inventory),
    ) if on]
    if len(new_modes) > 1:
        sys.stderr.write("ERROR: {} are mutually exclusive\n".format(" and ".join(new_modes)))
        return 2
    if new_modes:
        if args.refresh_status is not None:
            return run_refresh_status(args, cfg, cache)
        if args.render:
            return run_render(args, cfg, cache)
        return run_inventory(args, cfg, cache)

    notes = []

    code_roots = [to_posix(r) for r in (cfg.get("codeRoots") or [])]
    missing_roots = [r for r in code_roots if not os.path.isdir(r)]
    if missing_roots:
        notes.append("codeRoots not found on disk, skipped: " + ", ".join(missing_roots))
    code_roots = [r for r in code_roots if os.path.isdir(r)]

    code_cite_artifacts, doc_cite_artifacts, matrix_path = gather_artifacts(cfg, notes)
    modules, module_ids = load_modules(matrix_path, cache)
    if matrix_path and modules is None:
        notes.append("{} present but did not parse as {{modules:[...]}} — module-dependent checks degrade".format(
            matrix_path))

    # --artifact restricts scanning (and --reanchor) to a caller-chosen subset of
    # the scanned artifact set. Validate against the full universe (doc_cite_artifacts
    # is a superset of code_cite_artifacts — see gather_artifacts) regardless of which
    # --checks were requested, since the two flags are orthogonal.
    artifact_filter = None
    if args.artifact:
        universe = set(doc_cite_artifacts)
        requested_artifacts = set(to_posix(a) for a in args.artifact)
        unknown = sorted(a for a in requested_artifacts if a not in universe)
        if unknown:
            sys.stderr.write(
                "ERROR: --artifact path(s) not in the scanned artifact set: {}\n".format(
                    ", ".join(unknown)))
            return 2
        artifact_filter = requested_artifacts
        code_cite_artifacts = [a for a in code_cite_artifacts if a in artifact_filter]
        doc_cite_artifacts = [a for a in doc_cite_artifacts if a in artifact_filter]
        if matrix_path and matrix_path not in artifact_filter:
            notes.append("deps skipped — {} not in --artifact filter".format(matrix_path))

    findings_by_check = collections.OrderedDict()
    legacy_sink = [] if args.reanchor else None
    inexact_sym_sink = [] if args.reanchor else None
    need_code_cite_data = "code-cite" in requested or args.reanchor

    if need_code_cite_data:
        code_index = CodeIndex(code_roots)
        cc_findings = check_code_cite(code_cite_artifacts, code_index, cache,
                                       touched=args.touched, legacy_sink=legacy_sink,
                                       inexact_sym_sink=inexact_sym_sink)
        if "code-cite" in requested:
            findings_by_check["code-cite"] = cc_findings

    if "doc-cite" in requested:
        doc_roots = {
            "rulesRoot": cfg.get("rulesRoot"), "kitRulesRoot": cfg.get("kitRulesRoot"),
            "tddRoot": cfg.get("tddRoot"), "specsRoot": cfg.get("specsRoot"),
            "gddRoot": cfg.get("gddRoot"),
        }
        findings_by_check["doc-cite"] = check_doc_cite(doc_cite_artifacts, doc_roots, cache)

    if "contract-gap" in requested:
        findings_by_check["contract-gap"] = check_contract_gap(
            cfg.get("specsRoot"), cache, module_ids, artifact_filter=artifact_filter)

    if "deps" in requested:
        if artifact_filter is not None and matrix_path not in artifact_filter:
            findings_by_check["deps"] = []
        else:
            findings_by_check["deps"] = check_deps(code_roots, modules, matrix_path, cache)

    reanchor_proposals, reanchor_unsupported = [], []
    if args.reanchor:
        reanchor_proposals, reanchor_unsupported = build_reanchor_proposals(legacy_sink, cache, args.touched)
        reanchor_proposals.extend(inexact_sym_sink)
        reanchor_proposals.sort(key=lambda p: (p["artifact"], p["line"]))
        if args.write:
            applied = apply_reanchor_writes(reanchor_proposals)
            applied_keys = set((p["artifact"], p["line"], p["old"]) for p in applied)
            reanchor_proposals = [p for p in reanchor_proposals
                                   if (p["artifact"], p["line"], p["old"]) in applied_keys]

    if args.json:
        report = build_json_report(findings_by_check, reanchor_proposals, reanchor_unsupported, notes)
        json.dump(report, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
    else:
        print_text_report(findings_by_check, reanchor_proposals, reanchor_unsupported, notes, sys.stdout)
        if args.reanchor and args.write and (reanchor_proposals):
            sys.stdout.write(
                '\ncite-only edit — commit riêng với trailer "ndv-cite-only: true" '
                "(xem /ndv-sync §Cite-only edit)\n")

    all_findings = [f for fs in findings_by_check.values() for f in fs]
    has_broken = any(f.status in ("broken-cite", "contract-gap") for f in all_findings)
    return 1 if has_broken else 0


if __name__ == "__main__":
    sys.exit(main())
