#!/usr/bin/env python3
"""ndv_blueprint.py — deterministic check / render / approve for <matrixRoot>/blueprint.json.

Run from the host repo root. Python 3.8+, stdlib only. Reuses config + cite resolvers of
ndv-sync/scripts/ndv_check.py. Rule ids (MD-xx): <kitRulesRoot>/Shared/module-design.md.

  --check            validate schema, graph, band / role rules, cites, modules.json conformance
  --render           --check, then write blueprint.html from <templates>/blueprint-template.html
  --approve DATE     --check, then set approved / approvedDate / approvedDigest
                     (refused on any blocking finding or open decision)
  --code-graph       file-level type-reference cycles (SCC) under codeRoots — brownfield input

Exit codes: 0 = no blocking finding, 1 = blocking finding, 2 = usage/config/parse error.
"""

import argparse
import collections
import glob
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "..", "ndv-sync", "scripts"))
import ndv_check as nc

SCHEMA = "ndv-blueprint/1"
ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
GDD_CITE_RE = re.compile(r"^(?P<path>.+?\.md)(?:#(?P<anchor>.+))?$")
BANDS = ("foundation", "game")
BUILD_MODES = ("new", "extend", "rebuild", "existing")
DEP_KINDS = ("call", "event", "data")
ROLES = ("composition", "presentation")
ARROW_ACTIONS = ("reversed", "dropped")
APPROVAL_KEYS = ("approved", "approvedDate", "approvedDigest", "dismissed", "generated")
ROW_WIDTH = 6
STRUCTURAL = {"schema", "bad-id", "duplicate-id", "unknown-module", "self-dep", "duplicate-dep", "cycle"}
BLOCKING = STRUCTURAL | {
    "foundation-depends-on-game", "missing-extends", "missing-source", "broken-cite", "duplicate-data",
    "shared-wraps", "forbidden-dep", "role-placement", "paths-overlap", "scc-split",
    "open-decision-approved", "approval-void", "matrix-band-violation",
}
GATE_KINDS = {"approval-void", "matrix-band-violation"}
FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})(.*)$")
NUM_RE = re.compile(r"^§?\s*([0-9]+(?:\.[0-9]+)*)\.?(?:\s|$)")


class Report(object):
    def __init__(self):
        self.findings = []

    def add(self, kind, where, detail):
        self.findings.append({"kind": kind, "where": str(where), "detail": detail, "blocking": kind in BLOCKING})

    def has(self, kinds):
        return any(f["kind"] in kinds for f in self.findings)

    def blocking(self):
        return any(f["blocking"] for f in self.findings)

    def dismiss(self, dismissed):
        keys = {(str(d.get("kind")), str(d.get("where"))) for d in dismissed or [] if isinstance(d, dict)}
        kept = [f for f in self.findings if f["blocking"] or (f["kind"], f["where"]) not in keys]
        dropped = len(self.findings) - len(kept)
        self.findings = kept
        return dropped


def text(x):
    return isinstance(x, str) and bool(x.strip())


def strs(x):
    return isinstance(x, list) and all(text(s) for s in x)


def digest(bp):
    body = {k: v for k, v in bp.items() if k not in APPROVAL_KEYS}
    return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def check_schema(bp, rep):
    if bp.get("schema") != SCHEMA:
        rep.add("schema", "schema", "must be " + SCHEMA)
    for key in ("project", "title", "gdd"):
        if not text(bp.get(key)):
            rep.add("schema", key, "required non-empty string")
    if not DATE_RE.match(str(bp.get("generated") or "")):
        rep.add("schema", "generated", "must be yyyy-mm-dd")
    if not isinstance(bp.get("approved"), bool):
        rep.add("schema", "approved", "must be true | false")
    if not strs(bp.get("gddSources")) or not bp.get("gddSources"):
        rep.add("schema", "gddSources", "non-empty list of GDD file paths")
    for key in ("loops", "modules", "deps", "decisions", "outOfScope"):
        if not isinstance(bp.get(key), list):
            rep.add("schema", key, "must be a list")
    for key in ("gddArrows", "forbiddenDeps", "dismissed"):
        if bp.get(key) is not None and not isinstance(bp.get(key), list):
            rep.add("schema", key, "must be a list when present")
    if isinstance(bp.get("modules"), list) and not bp["modules"]:
        rep.add("schema", "modules", "at least one module")


def check_approval(bp, rep):
    if not bp.get("approved"):
        return
    if not DATE_RE.match(str(bp.get("approvedDate") or "")):
        rep.add("schema", "approvedDate", "approved blueprint needs approvedDate yyyy-mm-dd")
    if bp.get("approvedDigest") != digest(bp):
        rep.add("approval-void", "approved", "content changed after approval — re-run the /ndv-blueprint gate")


def check_sources(where, sources, rep, required):
    if not isinstance(sources, list) or not sources:
        if required:
            rep.add("missing-source", where, "cite >=1 GDD source {cite, quote}")
        return
    for s in sources:
        if not isinstance(s, dict) or not text(s.get("cite")) or not text(s.get("quote")):
            rep.add("schema", where, "sources[] items need {cite, quote}")


def check_modules(bp, rep):
    seen = {}
    for i, m in enumerate(bp.get("modules") or []):
        where = "modules[{}]".format(i)
        if not isinstance(m, dict):
            rep.add("schema", where, "must be an object")
            continue
        mid = m.get("id")
        if not isinstance(mid, str) or not ID_RE.match(mid):
            rep.add("bad-id", where, "id {!r} must match {}".format(mid, ID_RE.pattern))
            continue
        if mid.lower() in seen:
            rep.add("duplicate-id", mid, "clashes with {} (case-insensitive)".format(seen[mid.lower()]))
        seen[mid.lower()] = mid
        for key in ("name", "summary", "value"):
            if not text(m.get(key)):
                rep.add("schema", mid, key + " required")
        if m.get("band") not in BANDS:
            rep.add("schema", mid, "band must be " + " | ".join(BANDS))
        if m.get("buildMode") not in BUILD_MODES:
            rep.add("schema", mid, "buildMode must be " + " | ".join(BUILD_MODES))
        if m.get("role") is not None and m.get("role") not in ROLES:
            rep.add("schema", mid, "role must be " + " | ".join(ROLES))
        if not strs(m.get("responsibilities")) or not m.get("responsibilities"):
            rep.add("schema", mid, "responsibilities: non-empty list of strings")
        for key in ("data", "extends", "wraps", "paths"):
            if m.get(key) is not None and not strs(m.get(key)):
                rep.add("schema", mid, key + ": list of strings")
        if m.get("buildMode") in ("extend", "rebuild", "existing") and not m.get("extends"):
            rep.add("missing-extends", mid, "buildMode {} needs extends code cites (MD-21)".format(m.get("buildMode")))
        check_sources(mid, m.get("sources"), rep, True)


def module_map(bp):
    return {m["id"]: m for m in bp.get("modules") or []
            if isinstance(m, dict) and isinstance(m.get("id"), str) and ID_RE.match(m["id"])}


def check_deps(bp, mods, rep):
    decision_ids = {d.get("id") for d in bp.get("decisions") or [] if isinstance(d, dict) and isinstance(d.get("id"), str)}
    pairs = set()
    for i, e in enumerate(bp.get("deps") or []):
        if not isinstance(e, dict):
            rep.add("schema", "deps[{}]".format(i), "must be an object")
            continue
        a, b = e.get("from"), e.get("to")
        where = "{} -> {}".format(a, b)
        if not isinstance(a, str) or not isinstance(b, str) or a not in mods or b not in mods:
            rep.add("unknown-module", where, "from/to must be module ids")
            continue
        if a == b:
            rep.add("self-dep", where, "module depends on itself")
            continue
        if (a, b) in pairs:
            rep.add("duplicate-dep", where, "declared twice")
        pairs.add((a, b))
        if not text(e.get("contract")):
            rep.add("schema", where, "contract label required")
        if e.get("kind") not in DEP_KINDS:
            rep.add("schema", where, "kind must be " + " | ".join(DEP_KINDS))
        if e.get("decision") is not None:
            if not isinstance(e["decision"], str) or e["decision"] not in decision_ids:
                rep.add("schema", where, "decision {!r} is not a decision id".format(e["decision"]))
        else:
            check_sources(where, [e.get("source")] if e.get("source") is not None else None, rep, True)
        if mods[a].get("band") == "foundation" and mods[b].get("band") == "game":
            rep.add("foundation-depends-on-game", where, "Foundation may depend only on Foundation (MD-13)")
    return pairs


def find_cycles(ids, pairs):
    graph = collections.defaultdict(list)
    for a, b in sorted(pairs):
        graph[a].append(b)
    index, low, stack, on, out = {}, {}, [], set(), []
    counter = [0]

    def visit(v):
        index[v] = low[v] = counter[0]
        counter[0] += 1
        stack.append(v)
        on.add(v)
        for w in graph[v]:
            if w not in index:
                visit(w)
                low[v] = min(low[v], low[w])
            elif w in on:
                low[v] = min(low[v], index[w])
        if low[v] == index[v]:
            comp = []
            while True:
                w = stack.pop()
                on.discard(w)
                comp.append(w)
                if w == v:
                    break
            if len(comp) > 1:
                out.append(sorted(comp))

    for v in ids:
        if v not in index:
            visit(v)
    return out


def check_loops(bp, mods, rep):
    for i, loop in enumerate(bp.get("loops") or []):
        where = "loops[{}]".format(i)
        if not isinstance(loop, dict) or not text(loop.get("name")) or not text(loop.get("cite")):
            rep.add("schema", where, "loop needs {name, cite, stages}")
            continue
        stages = loop.get("stages")
        if not isinstance(stages, list) or len(stages) < 2:
            rep.add("schema", where, "loop needs >=2 stages")
            continue
        for j, s in enumerate(stages):
            sw = "{}.stages[{}]".format(where, j)
            if not isinstance(s, dict) or not text(s.get("name")) or not isinstance(s.get("uses"), dict):
                rep.add("schema", sw, "stage needs {name, uses{moduleId: text}}")
                continue
            for mid in s["uses"]:
                if mid not in mods:
                    rep.add("unknown-module", sw, "uses unknown module " + mid)


def check_decisions(bp, rep):
    ids = set()
    for i, d in enumerate(bp.get("decisions") or []):
        if not isinstance(d, dict) or not text(d.get("id")) or not text(d.get("question")):
            rep.add("schema", "decisions[{}]".format(i), "decision needs {id, kind, question, options, chosen}")
            continue
        where = d["id"]
        if where in ids:
            rep.add("schema", where, "duplicate decision id")
        ids.add(where)
        if d.get("kind") not in ("boundary", "gdd-gap", "foundation", "project"):
            rep.add("schema", where, "kind must be boundary | gdd-gap | foundation | project")
        options = d.get("options") if isinstance(d.get("options"), list) else []
        labels = [o.get("label") for o in options if isinstance(o, dict)]
        if len(labels) < 2 or not all(text(x) for x in labels):
            rep.add("schema", where, "needs >=2 options {label, description}")
        chosen = d.get("chosen")
        if chosen is None:
            if bp.get("approved") and bp.get("approvedDigest") == digest(bp):
                rep.add("open-decision-approved", where, "approved blueprint has an open decision")
        elif not text(d.get("answer")):
            rep.add("schema", where, "chosen decision needs answer `decision: <date> — \"<answer>\"`")


def check_architecture(bp, mods, pairs, rep):
    data_owner = {}
    for mid, m in mods.items():
        for item in m.get("data") or []:
            key = item.strip().lower()
            if key in data_owner and data_owner[key] != mid:
                rep.add("duplicate-data", item, "owned by {} and {} — single writer (MD-06)".format(data_owner[key], mid))
            data_owner.setdefault(key, mid)
    wraps = collections.defaultdict(set)
    for mid, m in mods.items():
        for w in m.get("wraps") or []:
            wraps[w].add(mid)
    for w, ids in sorted(wraps.items()):
        if len(ids) > 1:
            rep.add("shared-wraps", w, "wrapped by " + ", ".join(sorted(ids)) + " — one adapter per external (MD-24)")
    for i, f in enumerate(bp.get("forbiddenDeps") or []):
        if not isinstance(f, dict) or not strs(f.get("from")) or not strs(f.get("to")):
            rep.add("schema", "forbiddenDeps[{}]".format(i), "needs {from[], to[], cite, quote}")
            continue
        for mid in sorted(set(f["from"] + f["to"]) - set(mods)):
            rep.add("unknown-module", "forbiddenDeps[{}]".format(i), "names unknown module " + mid)
        check_sources("forbiddenDeps[{}]".format(i), [{"cite": f.get("cite"), "quote": f.get("quote")}], rep, True)
        for a, b in sorted(pairs):
            if a in f["from"] and b in f["to"]:
                rep.add("forbidden-dep", "{} -> {}".format(a, b), "GDD rule: \"{}\" (MD-17)".format(f.get("quote")))
    composition = {mid for mid, m in mods.items() if m.get("role") == "composition"}
    consumers = collections.defaultdict(set)
    for a, b in pairs:
        consumers[b].add(a)
    for mid, m in sorted(mods.items()):
        if m.get("role") in ROLES and m.get("band") != "game":
            rep.add("role-placement", mid, "role {} belongs in band game (MD-16, MD-22)".format(m["role"]))
        if m.get("role") in ROLES and consumers[mid] - composition:
            rep.add("role-placement", mid, "only composition modules may depend on a {} module (MD-16, MD-22): {}".format(
                m["role"], ", ".join(sorted(consumers[mid] - composition))))
    for i, a in enumerate(bp.get("gddArrows") or []):
        if not isinstance(a, dict) or a.get("action") not in ARROW_ACTIONS or not text(a.get("reason")):
            rep.add("schema", "gddArrows[{}]".format(i), "needs {cite, quote, action: reversed | dropped, reason}")


def normalize(s):
    return re.sub(r"\s+", " ", re.sub(r"\*\*|`", "", s)).strip().lower()


def headings(lines):
    out, fence = [], None
    for i, line in enumerate(lines, 1):
        f = FENCE_RE.match(line)
        if f and fence is None:
            fence = f.group(1)
            continue
        if f and f.group(1)[0] == fence[0] and len(f.group(1)) >= len(fence) and not f.group(2).strip():
            fence = None
            continue
        m = None if fence else nc.HEADING_RE.match(line)
        if m:
            out.append((i, len(m.group(1)), m.group(2)))
    return out


def exact_heading(anchor, title):
    num = NUM_RE.match(anchor)
    if num:
        head = NUM_RE.match(title)
        return bool(head) and head.group(1) == num.group(1)
    norm = lambda x: re.sub(r"[^a-z0-9]", "", x.lower())
    return norm(anchor) == norm(title) or nc.github_slug(title) == anchor.lower().lstrip("#")


def section_text(path, anchor, cache):
    lines = cache.lines(path)
    if not anchor:
        return "\n".join(lines), None
    heads = headings(lines)
    hit = next((i for i, h in enumerate(heads) if exact_heading(anchor, h[2])), None)
    inexact = None
    if hit is None:
        loose = [i for i, h in enumerate(heads) if h[1] > 1 and nc.section_matches(anchor, [h[2]])]
        hit = max(loose, key=lambda i: (len(re.sub(r"[^a-z0-9]", "", heads[i][2].lower())), -i)) if loose else None
        inexact = heads[hit][2] if hit is not None else None
    if hit is None:
        return None, None
    lineno, level, _ = heads[hit]
    end = next((ln for ln, lv, _ in heads[hit + 1:] if lv <= level), len(lines) + 1)
    return "\n".join(lines[lineno - 1:end - 1]), inexact


def resolve_gdd(cite, cache, quote=None):
    m = GDD_CITE_RE.match(cite.strip())
    if not m:
        return "not a <path>.md#<section> cite", None
    path = m.group("path").strip()
    if not os.path.isfile(path):
        return "file not found", None
    body, inexact = section_text(path, (m.group("anchor") or "").strip(), cache)
    if body is None:
        return "section not found", None
    if isinstance(quote, str) and quote and normalize(quote) not in normalize(body):
        return "quote not verbatim under that section", inexact
    return None, inexact


def resolve_code(cite, index, cache):
    m = nc.SYM_RE.fullmatch(cite.strip())
    if not m:
        return None, "not a <path>::<Type>.<Member> cite"
    resolved, status = index.resolve(m.group("path"))
    if status in ("missing", "ambiguous"):
        return None, "path " + status
    body = cache.text(resolved)
    missing = [s for s in (m.group("type"), m.group("member")) if s and not re.search(r"\b" + re.escape(s) + r"\b", body)]
    return resolved, ("symbol missing: " + ",".join(missing) if missing else None)


def gdd_cites(bp):
    for i, loop in enumerate(bp.get("loops") or []):
        if isinstance(loop, dict):
            yield "loops[{}]".format(i), loop.get("cite"), None
            for j, s in enumerate(loop.get("stages") or []):
                if isinstance(s, dict) and s.get("cite"):
                    yield "loops[{}].stages[{}]".format(i, j), s["cite"], None
    for m in bp.get("modules") or []:
        if isinstance(m, dict):
            for s in m.get("sources") or []:
                if isinstance(s, dict):
                    yield m.get("id"), s.get("cite"), s.get("quote")
    for e in bp.get("deps") or []:
        if isinstance(e, dict) and isinstance(e.get("source"), dict):
            yield "{} -> {}".format(e.get("from"), e.get("to")), e["source"].get("cite"), e["source"].get("quote")
    for i, a in enumerate(bp.get("gddArrows") or []):
        if isinstance(a, dict):
            yield "gddArrows[{}]".format(i), a.get("cite"), a.get("quote")
    for i, f in enumerate(bp.get("forbiddenDeps") or []):
        if isinstance(f, dict):
            yield "forbiddenDeps[{}]".format(i), f.get("cite"), f.get("quote")
    for d in bp.get("decisions") or []:
        if isinstance(d, dict) and isinstance(d.get("cite"), str) and not nc.SYM_RE.fullmatch(d["cite"].strip()):
            yield d.get("id"), d["cite"], None
    for i, o in enumerate(bp.get("outOfScope") or []):
        if isinstance(o, dict):
            yield "outOfScope[{}]".format(i), o.get("cite"), None


def coverage_cites(bp):
    for loop in bp.get("loops") or []:
        if isinstance(loop, dict):
            yield loop.get("cite")
            for s in loop.get("stages") or []:
                if isinstance(s, dict):
                    yield s.get("cite")
    for m in bp.get("modules") or []:
        for s in (m.get("sources") or []) if isinstance(m, dict) else []:
            if isinstance(s, dict):
                yield s.get("cite")
    for o in bp.get("outOfScope") or []:
        if isinstance(o, dict):
            yield o.get("cite")


def gdd_files(folder):
    if not isinstance(folder, str) or not os.path.isdir(folder):
        return []
    out = []
    for f in glob.glob(os.path.join(folder, "**", "*.md"), recursive=True):
        rel = nc.to_posix(os.path.relpath(f, folder))
        if not any(part.startswith("_") for part in rel.split("/")[:-1]):
            out.append(nc.to_posix(f))
    return sorted(out)


def check_cites(bp, cfg, cache, rep):
    gdd_root = nc.to_posix(cfg.get("gddRoot") or "").rstrip("/")
    sources = [p for p in bp.get("gddSources") or [] if isinstance(p, str)]
    for path in sources:
        if not os.path.isfile(path):
            rep.add("broken-cite", "gddSources", path + ": file not found")
    for where, cite, quote in gdd_cites(bp):
        if not text(cite):
            rep.add("schema", where, "cite required")
            continue
        err, inexact = resolve_gdd(cite, cache, quote)
        if inexact:
            rep.add("inexact-anchor", where, "{} matched heading \"{}\" only loosely — cite the exact heading".format(cite, inexact))
        if err:
            rep.add("broken-cite", where, "{}: {}".format(cite, err))
        elif gdd_root and not nc.to_posix(cite).startswith(gdd_root + "/"):
            rep.add("outside-gddRoot", where, cite + " is not under gddRoot " + gdd_root)
    covered = set()
    for cite in coverage_cites(bp):
        m = GDD_CITE_RE.match(cite.strip()) if isinstance(cite, str) else None
        if m:
            covered.add(nc.to_posix(m.group("path").strip()))
    listed = {nc.to_posix(p) for p in sources}
    for path in gdd_files(bp.get("gdd")):
        if path not in listed:
            rep.add("unread-file", path, "GDD file missing from gddSources")
        if path not in covered:
            rep.add("uncovered-file", path, "no module source, loop or outOfScope cites this GDD file (MD-04)")
    roots = [nc.to_posix(r) for r in cfg.get("codeRoots") or [] if os.path.isdir(r)]
    index = nc.CodeIndex(roots)
    decided = {}
    for d in bp.get("decisions") or []:
        if isinstance(d, dict) and isinstance(d.get("cite"), str) and nc.SYM_RE.fullmatch(d["cite"].strip()):
            resolved, err = resolve_code(d["cite"], index, cache)
            if err:
                rep.add("broken-cite", d.get("id"), "{}: {}".format(d["cite"], err))
            elif d.get("kind") == "project":
                decided.setdefault(resolved, []).append(d)
    owners = collections.defaultdict(set)
    for m in bp.get("modules") or []:
        if not isinstance(m, dict):
            continue
        for cite in m.get("extends") or []:
            if not isinstance(cite, str):
                continue
            resolved, err = resolve_code(cite, index, cache)
            if err:
                rep.add("broken-cite", m.get("id"), "{}: {}".format(cite, err))
            else:
                owners[resolved].add(m.get("id"))
    for path, ids in sorted(owners.items()):
        if len(ids) > 1:
            rep.add("shared-extends-file", path, "extended by " + ", ".join(sorted(ids)) + " — name its write owner (MD-25)")
    return owners, decided


def owned_paths(mods):
    out = []
    for mid, m in sorted(mods.items()):
        for p in m.get("paths") or []:
            out.append((mid, nc.to_posix(p).rstrip("/")))
    return out


def covers(owner, path):
    return path == owner or path.startswith(owner + "/")


def check_paths(cfg, cache, mods, extends_owners, decided, rep):
    owned = owned_paths(mods)
    for i, (a, pa) in enumerate(owned):
        for b, pb in owned[i + 1:]:
            if a != b and (covers(pa, pb) or covers(pb, pa)):
                rep.add("paths-overlap", "{} / {}".format(a, b), "{} overlaps {} (MD-25)".format(pa, pb))
    if not owned and not extends_owners:
        return
    for comp in code_graph(cfg, cache)["sccs"]:
        writers = sorted({mid for f in comp for mid, p in owned if covers(p, f)})
        touching = sorted(set(writers) | {mid for f in comp for mid in extends_owners.get(f, ())})
        shell = [mid for mid in writers if all(any(covers(p, f) for m2, p in owned if m2 == mid) for f in comp)]
        decisions = [d for f in comp for d in decided.get(f, ())]
        size = "{} files".format(len(comp))
        if len(writers) > 1:
            rep.add("scc-split", ", ".join(writers), "one type-reference cycle of {} has several write owners (MD-25)".format(size))
        elif len(touching) > 1 and not shell:
            chosen = [d for d in decisions if d.get("chosen") is not None]
            if chosen:
                rep.add("scc-decided", ", ".join(touching), "no shell `paths` over a cycle of {}; decision {} chose \"{}\" — check it matches paths / extends (MD-25)".format(
                    size, chosen[0].get("id"), chosen[0].get("chosen")))
            elif not decisions:
                rep.add("scc-split", ", ".join(touching), "modules touch one type-reference cycle of {} with no shell `paths` and no `project` decision citing it (MD-25)".format(size))


def check_usage(bp, mods, pairs, rep):
    linked = {a for a, _ in pairs} | {b for _, b in pairs}
    used = set()
    for loop in bp.get("loops") or []:
        for s in (loop.get("stages") or []) if isinstance(loop, dict) else []:
            if isinstance(s, dict) and isinstance(s.get("uses"), dict):
                used.update(s["uses"])
    for mid in mods:
        if mid not in linked and mid not in used:
            rep.add("isolated", mid, "no dependency, no consumer, no loop stage — cut it or wire it")


def check_matrix(cfg, cache, mods, pairs, rep):
    path = nc.matrix_json_path(cfg)
    if not path or not os.path.isfile(path):
        return
    modules, _ = nc.load_modules(path, cache)
    for m in modules or []:
        mid = m.get("id") if isinstance(m, dict) else None
        if not isinstance(mid, str):
            continue
        if mid not in mods:
            rep.add("unlisted-in-blueprint", mid, "in modules.json, not in blueprint")
            continue
        edges = [d for key in ("deps", "plannedDeps") if isinstance(m.get(key), list) for d in m[key] if isinstance(d, str)]
        for dep in sorted(set(edges)):
            if dep not in mods:
                continue
            if mods[mid].get("band") == "foundation" and mods[dep].get("band") == "game":
                rep.add("matrix-band-violation", "{} -> {}".format(mid, dep), "modules.json edge breaks the Foundation band (MD-13)")
            elif (mid, dep) not in pairs:
                rep.add("edge-undeclared", "{} -> {}".format(mid, dep), "modules.json edge not declared in blueprint")


def run_checks(bp, cfg, cache):
    rep = Report()
    check_schema(bp, rep)
    check_modules(bp, rep)
    mods = module_map(bp)
    pairs = check_deps(bp, mods, rep)
    for comp in find_cycles(sorted(mods), pairs):
        rep.add("cycle", ", ".join(comp), "these modules form a dependency cycle (MD-11)")
    check_loops(bp, mods, rep)
    check_decisions(bp, rep)
    extends_owners, decided = check_cites(bp, cfg, cache, rep)
    check_approval(bp, rep)
    if not rep.has(STRUCTURAL):
        check_architecture(bp, mods, pairs, rep)
        check_paths(cfg, cache, mods, extends_owners, decided, rep)
        check_usage(bp, mods, pairs, rep)
        check_matrix(cfg, cache, mods, pairs, rep)
    dropped = rep.dismiss(bp.get("dismissed"))
    return rep, mods, pairs, dropped


def layers(mods, pairs):
    deps = collections.defaultdict(list)
    for a, b in sorted(pairs):
        deps[a].append(b)
    memo = {}

    def depth(mid):
        if mid not in memo:
            ds = [d for d in deps[mid] if mods[d]["band"] == mods[mid]["band"]]
            memo[mid] = max([depth(d) + 1 for d in ds], default=0 if mods[mid]["band"] == "foundation" else 1)
        return memo[mid]

    return {mid: depth(mid) for mid in mods}


def layer_labels(mods, pairs):
    band_layer = layers(mods, pairs)
    found_rows = sorted({band_layer[m] for m in mods if mods[m]["band"] == "foundation"})
    out = {}
    for mid, m in mods.items():
        if m["band"] == "foundation":
            out[mid] = "Foundation" if len(found_rows) < 2 else "Foundation · row {}".format(found_rows.index(band_layer[mid]) + 1)
        else:
            out[mid] = "Layer {}".format(band_layer[mid])
    return band_layer, out


def layout(bp, mods, pairs):
    band_layer, labels = layer_labels(mods, pairs)
    order = {m["id"]: i for i, m in enumerate(bp["modules"])}
    groups = collections.OrderedDict()
    for band in BANDS:
        for lv in sorted({band_layer[m] for m in mods if mods[m]["band"] == band}):
            groups[(band, lv)] = [m for m in mods if mods[m]["band"] == band and band_layer[m] == lv]
    deps = collections.defaultdict(list)
    for a, b in sorted(pairs):
        deps[a].append(b)
    xpos, out = {}, []
    for (band, lv), ids in groups.items():
        def key(mid):
            xs = [xpos[d] for d in deps[mid] if d in xpos]
            return (sum(xs) / len(xs) if xs else order[mid] / max(len(order), 1), order[mid])
        ids = sorted(ids, key=key)
        for i, mid in enumerate(ids):
            xpos[mid] = (i + 0.5) / len(ids)
        rows = [ids[i:i + ROW_WIDTH] for i in range(0, len(ids), ROW_WIDTH)]
        if band == "foundation" and out and out[-1]["band"] == "foundation":
            out[-1]["rows"].extend(rows)
        elif band == "foundation":
            out.append({"band": band, "label": "Foundation", "note": "reusable across projects", "rows": rows})
        else:
            out.append({"band": band, "label": "Layer {}".format(lv), "note": "", "rows": rows})
    for mid, m in mods.items():
        m["layerLabel"] = labels[mid]
    return out


def render(bp, cfg, pairs, rep, out_path):
    tpl_path = os.path.join(cfg.get("templates") or ".claude/ndvkit/templates", "blueprint-template.html")
    if not os.path.isfile(tpl_path):
        sys.stderr.write("ERROR: template not found: {}\n".format(tpl_path))
        return None
    data = json.loads(json.dumps(bp))
    data["layout"] = layout(data, {m["id"]: m for m in data["modules"]}, pairs)
    data["findings"] = rep.findings
    data["approvalVoid"] = rep.has({"approval-void"})
    payload = json.dumps(data, ensure_ascii=False, sort_keys=True).replace("<", "\\u003c")
    with open(tpl_path, "r", encoding="utf-8") as f:
        html = f.read().replace("/*__BLUEPRINT_DATA__*/", payload)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    return nc.to_posix(out_path)


def code_graph(cfg, cache):
    files = []
    for root in cfg.get("codeRoots") or []:
        for dirpath, _dirs, names in os.walk(root):
            for fn in sorted(names):
                ext = fn.rsplit(".", 1)[-1].lower() if "." in fn else ""
                if ext in nc.TYPE_DECL_PATTERNS:
                    files.append((nc.to_posix(os.path.join(dirpath, fn)), ext))
    src = {f: nc.strip_comments_and_strings(cache.text(f)) for f, _ in files}
    declared = collections.defaultdict(set)
    for f, ext in files:
        for t in nc.TYPE_DECL_PATTERNS[ext].findall(src[f]):
            declared[t].add(f)
    pairs = set()
    for f, _ in files:
        for ident in set(nc.IDENT_TOKEN_RE.findall(src[f])) & set(declared):
            pairs.update((f, g) for g in declared[ident] if g != f)
    sccs = sorted(find_cycles(sorted(src), pairs), key=lambda c: (-len(c), c))
    all_files = sum(1 for root in cfg.get("codeRoots") or [] for _d, _s, names in os.walk(root)
                    for fn in names if not fn.startswith("."))
    return {"files": len(files), "allFiles": all_files, "edges": len(pairs), "sccs": sccs}


def print_report(rep, dropped, out):
    for f in sorted(rep.findings, key=lambda x: (not x["blocking"], x["kind"], x["where"])):
        out.write("{:<8} {:<28} {:<36} {}\n".format("BLOCK" if f["blocking"] else "warn", f["kind"], f["where"], f["detail"]))
    blocking = sum(1 for f in rep.findings if f["blocking"])
    out.write("\nSUMMARY: {} blocking, {} warning, {} dismissed\n".format(blocking, len(rep.findings) - blocking, dropped))


def load_blueprint(path):
    if not os.path.isfile(path):
        sys.stderr.write("ERROR: blueprint not found: {}\n".format(path))
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            bp = json.load(f)
    except ValueError as e:
        sys.stderr.write("ERROR: invalid JSON in {}: {}\n".format(path, e))
        return None
    if not isinstance(bp, dict):
        sys.stderr.write("ERROR: {} must be a JSON object\n".format(path))
        return None
    return bp


def main(argv=None):
    try:
        return run(argv)
    except Exception as e:
        sys.stderr.write("ERROR: {}: {}\n".format(type(e).__name__, e))
        return 2


def run(argv):
    p = argparse.ArgumentParser(prog="ndv_blueprint.py", description="Check / render / approve <matrixRoot>/blueprint.json. Run from the host repo root.")
    p.add_argument("--config", default=".claude/ndvkit/ndvkit.config.json")
    p.add_argument("--blueprint", default=None, help="default: <matrixRoot>/blueprint.json")
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--render", action="store_true")
    mode.add_argument("--approve", metavar="YYYY-MM-DD")
    mode.add_argument("--code-graph", action="store_true")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    cfg = nc.load_config(args.config)
    sys.setrecursionlimit(max(10000, sys.getrecursionlimit()))
    if args.code_graph:
        graph = code_graph(cfg, nc.FileCache())
        if args.json:
            json.dump(graph, sys.stdout, indent=2, ensure_ascii=False)
            sys.stdout.write("\n")
        else:
            sys.stdout.write("graphed files {} · all files under codeRoots {} · type-reference edges {} · cycles {}\n".format(
                graph["files"], graph["allFiles"], graph["edges"], len(graph["sccs"])))
            for i, comp in enumerate(graph["sccs"], 1):
                sys.stdout.write("SCC {} ({} files): {}\n".format(i, len(comp), ", ".join(comp)))
        return 0
    if args.approve and not DATE_RE.match(args.approve):
        sys.stderr.write("ERROR: --approve needs yyyy-mm-dd\n")
        return 2
    path = args.blueprint or os.path.join(cfg.get("matrixRoot") or "", "blueprint.json")
    bp = load_blueprint(path)
    if bp is None:
        return 2

    cache = nc.FileCache()
    rep, mods, pairs, dropped = run_checks(bp, cfg, cache)
    written = None
    if args.render and not rep.has(STRUCTURAL):
        written = render(bp, cfg, pairs, rep, os.path.join(os.path.dirname(path), "blueprint.html"))
        if written is None:
            return 2
    if args.approve:
        open_ids = [d.get("id") for d in bp.get("decisions") or [] if isinstance(d, dict) and d.get("chosen") is None]
        stale = [f for f in rep.findings if f["blocking"] and f["kind"] != "approval-void"]
        if stale or open_ids:
            rep.add("open-decision-approved", "approve", "refused: {} blocking finding(s), open decision(s): {}".format(len(stale), ", ".join(open_ids) or "none"))
        else:
            rep.findings = [f for f in rep.findings if f["kind"] != "approval-void"]
            bp["approved"], bp["approvedDate"], bp["approvedDigest"] = True, args.approve, digest(bp)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(bp, f, indent=2, ensure_ascii=False)
                f.write("\n")
            written = nc.to_posix(path)

    if args.json:
        labels = {} if rep.has(STRUCTURAL) else layer_labels(mods, pairs)[1]
        modules = {mid: {"band": m.get("band"), "layer": labels.get(mid)} for mid, m in sorted(mods.items())}
        json.dump({"blueprint": nc.to_posix(path), "written": written, "modules": modules, "findings": rep.findings,
                   "dismissed": dropped, "blocking": rep.blocking(),
                   "gateOnly": not any(f["blocking"] and f["kind"] not in GATE_KINDS for f in rep.findings)},
                  sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
    else:
        print_report(rep, dropped, sys.stdout)
        if written:
            sys.stdout.write("wrote {}\n".format(written))
        elif args.render:
            sys.stdout.write("not rendered: structural finding\n")
    return 1 if rep.blocking() else 0


if __name__ == "__main__":
    sys.exit(main())
