#!/usr/bin/env python3
"""Validate cross-references inside the Episky RFC corpus.

Dev-only tool. It checks, across all RFC-*.md files in ../rfc:

  1. Inter-RFC references: every RFC-XXXX token names an RFC that exists in the
     corpus (0000-0021). A reference to a planned RFC (0005-0020) is allowed.
  2. Section references: every §N / §N.M / §N.M.K resolves to a real heading,
     an implicit subsection, a numbered-list item in the target section, or a
     table row. A bare §N.M that follows an RFC-XXXX §N.M on the same paragraph
     inherits that RFC's scope (continuation references).
   3. Invariant references: RFC-0002 invariants 1-15, RFC-0004 invariants A1-A10,
      RFC-0007 invariants T1-T12, RFC-0008 invariants P1-P14, RFC-0005
   invariants F1-F16, RFC-0006 invariants V1-V16, RFC-0010 invariants
   PR1-PR16, RFC-0011 invariants SK1-SK16, RFC-0009 invariants SC1-SC16,
   RFC-0012 invariants CM1-CM16, and RFC-0013 invariants AU1-AU16. A
   lettered reference used with the word "invariant" must be an invariant,
   not a principle. RFC-0007's sanitization principles S1-S8 are recognised
   as principles.
  4. Open questions: every RFC-0001 / RFC-0002 question must be owned in the
     RFC-0000 §8 coverage tables; every coverage entry must map to an existing
     question. Open questions in RFC-0004 / RFC-0007 / RFC-0021 must name an
     owning RFC (or a delegation marker) inline. RFC-0003's questions are
     deliberately delegated to maintainers and are exempt.
  5. Open-question references: RFC-0001 Q1-Q27, RFC-0002 Q1-Q17 must be in range.

Usage:  python3 tools/validate_rfc_refs.py
Exit:   0 on clean, 1 when issues are found (a report is printed).
"""

import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
RFC_DIR = os.path.join(ROOT, "rfc")

VALID_RFC_NUMS = set(range(22))  # 0000-0021 per RFC-0000 index

INVARIANT_REGISTRIES = {
    "RFC-0002": {str(i) for i in range(1, 16)},   # invariants 1-15
    "RFC-0004": {f"A{i}" for i in range(1, 11)},  # invariants A1-A10
    "RFC-0007": {f"T{i}" for i in range(1, 13)},  # invariants T1-T12
    "RFC-0008": {f"P{i}" for i in range(1, 15)},  # invariants P1-P14
    "RFC-0005": {f"F{i}" for i in range(1, 17)},  # invariants F1-F16
    "RFC-0006": {f"V{i}" for i in range(1, 17)},  # invariants V1-V16
    "RFC-0010": {f"PR{i}" for i in range(1, 17)}, # invariants PR1-PR16
    "RFC-0011": {f"SK{i}" for i in range(1, 17)}, # invariants SK1-SK16
    "RFC-0009": {f"SC{i}" for i in range(1, 17)}, # invariants SC1-SC16
    "RFC-0012": {f"CM{i}" for i in range(1, 17)}, # invariants CM1-CM16
    "RFC-0013": {f"AU{i}" for i in range(1, 17)}, # invariants AU1-AU16
}
PRINCIPLE_REGISTRIES = {
    "RFC-0007": {f"S{i}" for i in range(1, 9)},   # sanitization principles S1-S8
}

OQ_RANGES = {"RFC-0001": (1, 27), "RFC-0002": (1, 17)}          # §12 / §11
OQ_INLINE_RFCS = ("RFC-0004", "RFC-0007", "RFC-0021")           # name owner inline
OQ_COVERED_RFCS = ("RFC-0001", "RFC-0002")                      # RFC-0000 §8 tables

RFC_MENTION = re.compile(r"RFC-\d{4}")


class Issues:
    def __init__(self):
        self.errors = []
        self.warnings = []

    def error(self, fname, line, msg):
        self.errors.append(f"{fname}:{line}: ERROR  {msg}")

    def warn(self, fname, line, msg):
        self.warnings.append(f"{fname}:{line}: WARNING  {msg}")


def rfc_files():
    out = {}
    for name in sorted(os.listdir(RFC_DIR)):
        m = re.fullmatch(r"RFC-(\d{4})-[^/]+\.md", name)
        if m:
            out[int(m.group(1))] = os.path.join(RFC_DIR, name)
    return out


# ------------------------------------------------------------- section indexing

def build_section_index(lines):
    """Map 'N', 'N.M', 'N.M.K' -> True for every real/structural target.

    Handles: ## N headings, ### N.M headings, #### N.M.K headings, unnumbered
    ### subsections (assigned N.i in order), numbered-list items inside a
    section (referenced as §N.M, e.g. RFC-0001 §3, §8, §10; RFC-0000 §6;
    RFC-0007 §13; RFC-0002 §9 invariants), and markdown table rows (RFC-0021
    §8 rows are referenced as §8.1..§8.6).
    """
    index = {}
    current_top = None
    current_sub = 0
    in_table = False
    list_items = set()
    table_rows = 0

    def flush():
        if current_top is None:
            return
        index[str(current_top)] = True
        for item in list_items:
            index[f"{current_top}.{item}"] = True
        for r in range(1, table_rows + 1):
            index[f"{current_top}.{r}"] = True

    for line in lines:
        h = re.match(r"^##\s+(\d+)\.", line)
        if h:
            flush()
            current_top = int(h.group(1))
            current_sub = 0
            in_table = False
            list_items = set()
            table_rows = 0
            continue
        if current_top is None:
            continue
        h3 = re.match(r"^###\s+(\d+\.\d+)", line)
        h3u = re.match(r"^###\s+", line)
        h4 = re.match(r"^####\s+(\d+\.\d+\.\d+)", line)
        if h3:
            index[h3.group(1)] = True
            flush()
            current_sub = 0
            in_table = False
            list_items = set()
            table_rows = 0
        elif h4:
            index[h4.group(1)] = True
        elif h3u:
            current_sub += 1
            index[f"{current_top}.{current_sub}"] = True
        elif re.match(r"^\s*\|", line):
            if re.match(r"^\s*\|\s*:?-+", line):
                in_table = True
                table_rows = 0
            elif in_table:
                table_rows += 1
        else:
            m = re.match(r"^\s*(\d+)\.\s", line)
            if m and not in_table:
                list_items.add(int(m.group(1)))
    flush()
    return index


# ------------------------------------------------------------ reference scanning

# Scoped section ref (RFC-0003 Part II §5, RFC-0001 (§7-§8)) and bare § ref,
# with optional range continuation (N-M / N.M-N.K).
SECTION_REF = re.compile(
    r"RFC-(\d{4})\s*(?:Part\s+II\s*)?\(?\s*§\s*(\d+(?:\.\d+){0,2})"
    r"(?:\s*[–-]\s*§?\s*(\d+(?:\.\d+){0,2}))?"
    r"|§\s*(\d+(?:\.\d+){0,2})(?:\s*[–-]\s*§?\s*(\d+(?:\.\d+){0,2}))?"
)

# Invariant references with the word "invariant" (list capture incl. ranges).
INVARIANT_REF = re.compile(
    r"RFC-(\d{4})\s+invariant[s]?\s+([A-Z]{1,2}\d+(?:\s*(?:,|and|[–-])\s*[A-Z]{1,2}\d+)*)"
    r"|\binvariant[s]?\s+([A-Z]{1,2}\d+(?:\s*(?:,|and|[–-])\s*[A-Z]{1,2}\d+)*)"
)

# Bare lettered invariant/principle tokens: A1-A10, T1-T12, S1-S8, P1-P14,
# F1-F16, V1-V16, PR1-PR16, SK1-SK16, SC1-SC16, CM1-CM16, AU1-AU16.
LETTERED = re.compile(r"(?<![\w.])((?:PR|SK|SC|CM|AU|[AFPSTV])\d{1,2})(?!\w)")

# Open-question references.
OQ_REF = re.compile(
    r"RFC-0001\s+Q(\d+)"
    r"|RFC-0002\s+(?:Open Question|Q)\s*(\d+)"
    r"|\bOpen Question\s+(\d+)"
)


def expand_ids(ids):
    """Expand '1-2', '4 and 5', '11', 'A1-A10', 'PR1-PR16' style strings into a list."""
    out = []
    for part in re.split(r"\s*(?:,|and)\s*", ids.strip()):
        m = re.fullmatch(r"([A-Z]{1,2}\d+)\s*[–-]\s*([A-Z]{1,2}\d+)", part)
        if m:
            a, b = m.group(1), m.group(2)
            pa, pb = re.match(r"[A-Z]*", a).group(0), re.match(r"[A-Z]*", b).group(0)
            na, nb = int(a[len(pa):]), int(b[len(pb):])
            if pa != pb:
                out.append(part)
            else:
                out.extend(f"{pa}{n}" for n in range(na, nb + 1))
        else:
            out.append(part)
    return [x for x in out if x]


def main():
    files = rfc_files()
    issues = Issues()
    lines = {}
    indexes = {}

    for num, path in files.items():
        with open(path, encoding="utf-8") as f:
            ln = f.read().splitlines()
        lines[num] = ln
        indexes[num] = build_section_index(strip_fenced(ln))

    # ---- 1. Inter-RFC references --------------------------------------------
    for num, ln in lines.items():
        fname = os.path.basename(files[num])
        in_fence = False
        for i, line in enumerate(ln, start=1):
            if line.lstrip().startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            for m in re.finditer(r"RFC-(\d{4})", line):
                target = int(m.group(1))
                if target not in VALID_RFC_NUMS:
                    issues.error(fname, i, f"reference to nonexistent RFC-{target:04d}")

    # ---- 2. Section references (block-scoped, handles wrapped refs) ---------
    # Refs like "RFC-0003 <newline> §2.4" and "(logs §4.12, packages §4.9)"
    # following an RFC-0021 mention in the same paragraph need scope tracking
    # across lines. We group non-fence, non-blank, non-heading lines into
    # blocks and resolve within each block.
    for num, ln in lines.items():
        fname = os.path.basename(files[num])
        blocks = []
        cur = []
        cur_start = 0
        in_fence = False
        for i, line in enumerate(ln, start=1):
            if line.lstrip().startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            if not line.strip() or line.startswith("#"):
                if cur:
                    blocks.append(("\n".join(cur), cur_start))
                    cur = []
                continue
            if not cur:
                cur_start = i
            cur.append(line)
        if cur:
            blocks.append(("\n".join(cur), cur_start))

        for block, start_line in blocks:
            scope = None
            for m in SECTION_REF.finditer(block):
                line = start_line + block[: m.start()].count("\n")
                if m.group(1):  # RFC-scoped
                    target = int(m.group(1))
                    scope = target
                    keys = [m.group(2)] + ([m.group(3)] if m.group(3) else [])
                    for key in keys:
                        if target not in indexes:
                            issues.error(fname, line, f"§{key} scopes to RFC-{target:04d}, not in corpus")
                        elif key not in indexes[target]:
                            issues.error(fname, line, f"§{key} does not exist in RFC-{target:04d}")
                else:           # bare: current doc first, block scope as fallback
                    keys = [m.group(4)] + ([m.group(5)] if m.group(5) else [])
                    for key in keys:
                        ok_here = key in indexes.get(num, {})
                        ok_scope = scope is not None and scope in indexes and key in indexes[scope]
                        if ok_here or ok_scope:
                            continue
                        issues.error(fname, line, f"§{key} does not exist in RFC-{num:04d}")

    # ---- 3. Invariant and principle references ------------------------------
    for num, ln in lines.items():
        fname = os.path.basename(files[num])
        in_fence = False
        for i, line in enumerate(ln, start=1):
            if line.lstrip().startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            consumed = []
            for m in INVARIANT_REF.finditer(line):
                consumed.append(m.span())
                if m.group(1):
                    owner = f"RFC-{m.group(1)}"
                    ids = expand_ids(m.group(2))
                else:
                    owner = None
                    ids = expand_ids(m.group(3))
                for ident in ids:
                    if ident[0].isdigit():
                        regs = {owner: INVARIANT_REGISTRIES.get(owner, set())} if owner else {"RFC-0002": INVARIANT_REGISTRIES["RFC-0002"]}
                        found = any(ident in r for r in regs.values())
                    else:
                        # Used with the word "invariant", so only invariant
                        # registries count; a principle (e.g. RFC-0007's S1-S8)
                        # is not an invariant and is a dangling reference here.
                        found = any(ident in r for r in INVARIANT_REGISTRIES.values())
                    if not found:
                        issues.error(fname, i, f"unknown invariant identifier '{ident}'")

            # Bare lettered tokens, skipping spans covered by INVARIANT_REF.
            for m in LETTERED.finditer(line):
                if any(a <= m.start() < b for a, b in consumed):
                    continue
                ident = m.group(1)
                known = any(ident in r for r in INVARIANT_REGISTRIES.values())
                known = known or any(ident in r for r in PRINCIPLE_REGISTRIES.values())
                if not known:
                    issues.error(fname, i, f"unknown invariant/principle identifier '{ident}'")

    # ---- 4. Open questions: coverage vs. inline owners ----------------------
    zero_lines = strip_fenced(lines[0])
    coverage = {rfc: set() for rfc in OQ_COVERED_RFCS}
    current = None
    for line in zero_lines:
        h = re.match(r"^###\s+(RFC-0001|RFC-0002)\s+open questions", line)
        if h:
            current = h.group(1)
            continue
        if re.match(r"^##\s+\d+\.", line):
            current = None
            continue
        if current and re.match(r"^\|\s*\d", line):
            cells = [c.strip() for c in line.split("|")]
            coverage[current].update(expand_numbers(cells[1]) if len(cells) > 1 else set())

    for rfc, (lo, hi) in OQ_RANGES.items():
        num = int(rfc.split("-")[1])
        fname = os.path.basename(files[num])
        actual = set()
        in_section = False
        for i, line in enumerate(strip_fenced(lines[num]), start=1):
            if re.match(r"^##\s+\d+\.", line):
                in_section = "Open Questions" in line
                continue
            if in_section:
                m = re.match(r"^\s*(\d+)\.\s", line)
                if m:
                    actual.add(int(m.group(1)))
        for n in range(lo, hi + 1):
            if n not in coverage[rfc]:
                issues.error(fname, 0, f"{rfc} open question {n} has no owner in RFC-0000 §8")
            if n not in actual:
                issues.error(fname, 0, f"{rfc} open question {n} claimed by RFC-0000 §8 but never asked")
        for n in sorted(actual):
            if n < lo or n > hi:
                issues.error(fname, 0, f"{rfc} open question {n} out of expected range {lo}-{hi}")

    for rfc in OQ_INLINE_RFCS:
        num = int(rfc.split("-")[1])
        fname = os.path.basename(files[num])
        in_section = False
        item = []
        item_start = 0
        for i, line in enumerate(strip_fenced(lines[num]), start=1):
            if re.match(r"^##\s+\d+\.", line):
                in_section = "Open Questions" in line
                continue
            m = re.match(r"^\s*(\d+)\.\s", line)
            if in_section and m:
                if item and not (RFC_MENTION.search(" ".join(item))
                                 or any(k in " ".join(item) for k in ("Delegated", "Future work", "future amendment"))):
                    issues.error(fname, item_start,
                                 f"{rfc} open question without an owning RFC: {' '.join(item)[:80]}")
                item = [line.strip()]
                item_start = i
            elif in_section and item:
                item.append(line.strip())
        if item and not (RFC_MENTION.search(" ".join(item))
                         or any(k in " ".join(item) for k in ("Delegated", "Future work", "future amendment"))):
            issues.error(fname, item_start,
                         f"{rfc} open question without an owning RFC: {' '.join(item)[:80]}")

    # ---- 5. Open-question references -----------------------------------------
    for num, ln in lines.items():
        fname = os.path.basename(files[num])
        in_fence = False
        for i, line in enumerate(ln, start=1):
            if line.lstrip().startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            for m in OQ_REF.finditer(line):
                if m.group(1):
                    n, rfc = int(m.group(1)), "RFC-0001"
                elif m.group(2):
                    n, rfc = int(m.group(2)), "RFC-0002"
                else:
                    n, rfc = int(m.group(3)), "RFC-0002"
                lo, hi = OQ_RANGES[rfc]
                if not (lo <= n <= hi):
                    issues.error(fname, i, f"{rfc} Q{n} out of range ({lo}-{hi})")

    # ---- Report --------------------------------------------------------------
    if issues.warnings:
        print("\n".join(issues.warnings))
    if issues.errors:
        print("\n".join(issues.errors))
        print(f"\n{len(issues.errors)} error(s), {len(issues.warnings)} warning(s)")
        return 1
    print(f"OK: {len(files)} RFC files, {len(issues.errors)} errors, {len(issues.warnings)} warnings")
    return 0


def strip_fenced(lines):
    out = []
    in_fence = False
    for line in lines:
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence:
            out.append(line)
    return out


def expand_numbers(s):
    out = set()
    for part in re.split(r"[,\s]+", s.strip()):
        if not part:
            continue
        m = re.fullmatch(r"(\d+)[–-](\d+)", part)
        if m:
            out.update(range(int(m.group(1)), int(m.group(2)) + 1))
        else:
            out.add(int(part))
    return out


if __name__ == "__main__":
    sys.exit(main())
