"""Flask server that renders markdown with annotation support."""

import json
import os

import markdown
from flask import Flask, jsonify, request, send_from_directory

from nota.template import render_page

app = Flask(__name__)

# Set via configure()
_state = {
    "md_file": None,
    "annotations_file": None,
    "md_dir": None,
}


def configure(md_file: str):
    _state["md_file"] = os.path.abspath(md_file)
    _state["md_dir"] = os.path.dirname(_state["md_file"])
    _state["annotations_file"] = _state["md_file"] + ".nota.json"


def _load_annotations():
    path = _state["annotations_file"]
    if path and os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return []


def _save_annotations(annotations):
    with open(_state["annotations_file"], "w") as f:
        json.dump(annotations, f, indent=2)


@app.route("/")
def index():
    with open(_state["md_file"]) as f:
        md_content = f.read()

    html_content = markdown.markdown(
        md_content,
        extensions=["tables", "fenced_code", "codehilite", "toc"],
    )
    annotations = _load_annotations()
    filename = os.path.basename(_state["md_file"])

    return render_page(filename, html_content, annotations)


@app.route("/api/annotations", methods=["POST"])
def update_annotations():
    data = request.get_json()
    _save_annotations(data)
    return jsonify({"ok": True, "count": len(data)})


@app.route("/api/annotations", methods=["GET"])
def get_annotations():
    return jsonify(_load_annotations())


@app.route("/videos/<path:filename>")
def serve_videos(filename):
    return send_from_directory(os.path.join(_state["md_dir"], "videos"), filename)


@app.route("/<path:filename>")
def serve_files(filename):
    return send_from_directory(_state["md_dir"], filename)
