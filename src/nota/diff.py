"""Baseline snapshots and PR-style change hunks.

nota keeps a frozen copy of the markdown file (the "before" version) next to it as
``<file>.nota.base``. Everything an agent writes into the file afterwards shows up as
reviewable hunks: accepting one advances the baseline, rejecting one restores the old
lines in the real file.
"""

import difflib
import os

# How far a hunk may grow while snapping to markdown block boundaries.
EXPAND_LIMIT = 80


def baseline_path(md_file: str) -> str:
    return md_file + ".nota.base"


def ensure_baseline(md_file: str, reset: bool = False) -> str:
    """Create the baseline snapshot if missing. Returns its path."""
    path = baseline_path(md_file)
    if reset or not os.path.exists(path):
        with open(md_file, encoding="utf-8") as f:
            content = f.read()
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    return path


def read_lines(path: str) -> list:
    with open(path, encoding="utf-8") as f:
        return f.read().splitlines()


def ends_with_newline(path: str) -> bool:
    with open(path, encoding="utf-8") as f:
        content = f.read()
    return content.endswith("\n") or not content


def write_lines(path: str, lines: list, trailing_newline: bool = True) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + ("\n" if lines and trailing_newline else ""))


def _fence_mask(lines: list) -> list:
    """Mark lines that live inside a fenced code block."""
    mask = [False] * len(lines)
    fence = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if fence is None:
            if stripped.startswith("```") or stripped.startswith("~~~"):
                fence = stripped[:3]
                mask[i] = True
        else:
            mask[i] = True
            if stripped.startswith(fence):
                fence = None
    return mask


def _separators(lines: list) -> list:
    """True where a line is a blank block separator (blanks inside fences don't count)."""
    fenced = _fence_mask(lines)
    return [not line.strip() and not fenced[i] for i, line in enumerate(lines)]


def compute_hunks(base_lines: list, cur_lines: list) -> list:
    """Group the diff into block-aligned hunks.

    Each hunk is ``{base_start, base_end, cur_start, cur_end}`` with half-open line
    ranges. Boundaries are snapped outwards to blank lines so every hunk side is a
    complete set of markdown blocks and can be rendered on its own.
    """
    matcher = difflib.SequenceMatcher(None, base_lines, cur_lines, autojunk=False)

    # Merge consecutive non-equal opcodes so hunks are separated by equal blocks only.
    hunks = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        if hunks and hunks[-1]["base_end"] == i1 and hunks[-1]["cur_end"] == j1:
            hunks[-1]["base_end"] = i2
            hunks[-1]["cur_end"] = j2
        else:
            hunks.append({"base_start": i1, "base_end": i2, "cur_start": j1, "cur_end": j2})

    if not hunks:
        return []

    base_sep = _separators(base_lines)
    cur_sep = _separators(cur_lines)

    def edge_is_blank(h, at_start):
        """Is the hunk already sitting on a block boundary at this edge?

        Only sides that actually have lines get a vote, so a pure insertion is judged
        by the added lines alone and never drags the neighbouring block into the diff.
        """
        votes = []
        if h["base_end"] > h["base_start"]:
            votes.append(base_sep[h["base_start"] if at_start else h["base_end"] - 1])
        if h["cur_end"] > h["cur_start"]:
            votes.append(cur_sep[h["cur_start"] if at_start else h["cur_end"] - 1])
        return all(votes)

    # Grow each hunk to block boundaries. The lines around a hunk are identical on both
    # sides, so both ranges shift by the same amount and stay aligned.
    for k, h in enumerate(hunks):
        prev_base_end = hunks[k - 1]["base_end"] if k else 0
        prev_cur_end = hunks[k - 1]["cur_end"] if k else 0
        next_base_start = hunks[k + 1]["base_start"] if k + 1 < len(hunks) else len(base_lines)
        next_cur_start = hunks[k + 1]["cur_start"] if k + 1 < len(hunks) else len(cur_lines)

        up = 0
        while not edge_is_blank(h, True) and up < EXPAND_LIMIT:
            bi = h["base_start"] - up - 1
            cj = h["cur_start"] - up - 1
            if bi < prev_base_end or cj < prev_cur_end:
                break
            if base_sep[bi]:
                break
            up += 1
        h["base_start"] -= up
        h["cur_start"] -= up

        down = 0
        while not edge_is_blank(h, False) and down < EXPAND_LIMIT:
            bi = h["base_end"] + down
            cj = h["cur_end"] + down
            if bi >= next_base_start or cj >= next_cur_start:
                break
            if base_sep[bi]:
                break
            down += 1
        h["base_end"] += down
        h["cur_end"] += down

        # Drop leading/trailing blank lines so a hunk renders as tight blocks.
        while h["base_end"] > h["base_start"] and base_sep[h["base_end"] - 1] and \
                h["cur_end"] > h["cur_start"] and cur_sep[h["cur_end"] - 1]:
            h["base_end"] -= 1
            h["cur_end"] -= 1

    def junction_is_clean(sep, lines, idx):
        """Does a block end at this line index?"""
        if idx <= 0 or idx >= len(lines):
            return True
        return sep[idx] or sep[idx - 1]

    # Expansion can make neighbours overlap; fold those together. Hunks that only touch
    # stay separate — so an edit and an append inside the same document can be resolved
    # one at a time — unless they sit inside a single markdown block, which has to be
    # rendered as a whole to make sense.
    merged = [hunks[0]]
    for h in hunks[1:]:
        last = merged[-1]
        overlaps = h["base_start"] < last["base_end"] or h["cur_start"] < last["cur_end"]
        touches = h["base_start"] == last["base_end"] and h["cur_start"] == last["cur_end"]
        same_block = touches and not (
            junction_is_clean(base_sep, base_lines, last["base_end"])
            and junction_is_clean(cur_sep, cur_lines, last["cur_end"])
        )
        if overlaps or same_block:
            last["base_end"] = max(last["base_end"], h["base_end"])
            last["cur_end"] = max(last["cur_end"], h["cur_end"])
        else:
            merged.append(h)

    return merged


def build_segments(base_lines: list, cur_lines: list, hunks: list) -> list:
    """Interleave unchanged regions and hunks into a single reviewable document."""
    segments = []
    pos_base, pos_cur = 0, 0

    for idx, h in enumerate(hunks):
        if h["base_start"] > pos_base:
            segments.append({
                "type": "equal",
                "lines": base_lines[pos_base:h["base_start"]],
            })
        segments.append({
            "type": "hunk",
            "idx": idx,
            "old": base_lines[h["base_start"]:h["base_end"]],
            "new": cur_lines[h["cur_start"]:h["cur_end"]],
        })
        pos_base, pos_cur = h["base_end"], h["cur_end"]

    if pos_base < len(base_lines):
        segments.append({"type": "equal", "lines": base_lines[pos_base:]})

    return segments


def accept_hunk(md_file: str, idx: int) -> bool:
    """Keep the new lines: move the baseline forward for this hunk only."""
    base_file = baseline_path(md_file)
    base_lines = read_lines(base_file)
    cur_lines = read_lines(md_file)
    hunks = compute_hunks(base_lines, cur_lines)
    if idx < 0 or idx >= len(hunks):
        return False
    h = hunks[idx]
    base_lines[h["base_start"]:h["base_end"]] = cur_lines[h["cur_start"]:h["cur_end"]]
    write_lines(base_file, base_lines, ends_with_newline(base_file))
    return True


def reject_hunk(md_file: str, idx: int) -> bool:
    """Discard the new lines: restore the baseline version into the real file."""
    base_file = baseline_path(md_file)
    base_lines = read_lines(base_file)
    cur_lines = read_lines(md_file)
    hunks = compute_hunks(base_lines, cur_lines)
    if idx < 0 or idx >= len(hunks):
        return False
    h = hunks[idx]
    cur_lines[h["cur_start"]:h["cur_end"]] = base_lines[h["base_start"]:h["base_end"]]
    write_lines(md_file, cur_lines, ends_with_newline(md_file))
    return True


def accept_all(md_file: str) -> None:
    with open(md_file, encoding="utf-8") as f:
        content = f.read()
    with open(baseline_path(md_file), "w", encoding="utf-8") as f:
        f.write(content)


def reject_all(md_file: str) -> None:
    with open(baseline_path(md_file), encoding="utf-8") as f:
        content = f.read()
    with open(md_file, "w", encoding="utf-8") as f:
        f.write(content)
