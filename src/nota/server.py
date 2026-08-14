"""Flask server that renders markdown with annotation support."""

import hashlib
import json
import os

import markdown
from flask import Flask, jsonify, request, send_from_directory

from nota import diff
from nota.template import render_page

app = Flask(__name__)

# Set via configure()
_state = {
    "md_file": None,
    "annotations_file": None,
    "md_dir": None,
    "base_file": None,
}


def configure(md_file: str, reset_base: bool = False):
    _state["md_file"] = os.path.abspath(md_file)
    _state["md_dir"] = os.path.dirname(_state["md_file"])
    _state["annotations_file"] = _state["md_file"] + ".nota.json"
    _state["base_file"] = diff.ensure_baseline(_state["md_file"], reset=reset_base)


def _load_annotations():
    path = _state["annotations_file"]
    if path and os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return []


def _save_annotations(annotations):
    with open(_state["annotations_file"], "w") as f:
        json.dump(annotations, f, indent=2)


def _render_md(md_content: str) -> str:
    return markdown.markdown(
        md_content,
        extensions=["tables", "fenced_code", "codehilite", "toc"],
    )


@app.route("/")
def index():
    with open(_state["md_file"]) as f:
        md_content = f.read()

    html_content = _render_md(md_content)
    annotations = _load_annotations()
    filename = os.path.basename(_state["md_file"])

    return render_page(filename, html_content, annotations)


@app.route("/api/annotations", methods=["DELETE"])
def clear_annotations():
    _save_annotations([])
    return jsonify({"ok": True, "count": 0})


@app.route("/api/annotations", methods=["POST"])
def update_annotations():
    data = request.get_json()
    _save_annotations(data)
    return jsonify({"ok": True, "count": len(data)})


@app.route("/api/annotations", methods=["GET"])
def get_annotations():
    return jsonify(_load_annotations())


def _hunk_key(old_text: str, new_text: str) -> str:
    digest = hashlib.sha1((old_text + "\x00" + new_text).encode("utf-8"))
    return digest.hexdigest()[:12]


def _diff_state():
    base_lines = diff.read_lines(_state["base_file"])
    cur_lines = diff.read_lines(_state["md_file"])
    return base_lines, cur_lines, diff.compute_hunks(base_lines, cur_lines)


@app.route("/api/diff", methods=["GET"])
def get_diff():
    """The full document with changed blocks rendered as before/after pairs."""
    base_lines, cur_lines, hunks = _diff_state()
    segments = diff.build_segments(base_lines, cur_lines, hunks)

    out = []
    for seg in segments:
        if seg["type"] == "equal":
            out.append({"type": "equal", "html": _render_md("\n".join(seg["lines"]))})
        else:
            old_text = "\n".join(seg["old"]).strip()
            new_text = "\n".join(seg["new"]).strip()
            out.append({
                "type": "hunk",
                "idx": seg["idx"],
                # Chunks get renumbered as others are resolved, so comments anchor to
                # the content itself rather than to a position.
                "key": _hunk_key(old_text, new_text),
                "old_html": _render_md("\n".join(seg["old"])) if seg["old"] else "",
                "new_html": _render_md("\n".join(seg["new"])) if seg["new"] else "",
                "old_text": old_text[:600],
                "new_text": new_text[:600],
            })

    return jsonify({
        "count": len(hunks),
        "mtime": os.path.getmtime(_state["md_file"]),
        "segments": out,
    })


@app.route("/api/diff/status", methods=["GET"])
def diff_status():
    _, _, hunks = _diff_state()
    return jsonify({"count": len(hunks), "mtime": os.path.getmtime(_state["md_file"])})


@app.route("/api/diff/<int:idx>/<action>", methods=["POST"])
def resolve_hunk(idx, action):
    if action == "accept":
        ok = diff.accept_hunk(_state["md_file"], idx)
    elif action == "reject":
        ok = diff.reject_hunk(_state["md_file"], idx)
    else:
        return jsonify({"ok": False, "error": "unknown action"}), 400

    _, _, hunks = _diff_state()
    return jsonify({"ok": ok, "count": len(hunks)})


@app.route("/api/diff/<action>_all", methods=["POST"])
def resolve_all(action):
    if action == "accept":
        diff.accept_all(_state["md_file"])
    elif action == "reject":
        diff.reject_all(_state["md_file"])
    else:
        return jsonify({"ok": False, "error": "unknown action"}), 400
    return jsonify({"ok": True, "count": 0})


@app.route("/videos/<path:filename>")
def serve_videos(filename):
    return send_from_directory(os.path.join(_state["md_dir"], "videos"), filename)


@app.route("/<path:filename>")
def serve_files(filename):
    return send_from_directory(_state["md_dir"], filename)
