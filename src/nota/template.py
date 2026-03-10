"""HTML template for the annotation UI."""

import json


def render_page(filename: str, html_content: str, annotations: list) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Annotate: {filename}</title>
{CSS}
</head>
<body>

<div class="toolbar">
    <span class="title">md-annotate: {filename}</span>
    <span class="status" id="status">Select text to annotate</span>
    <div>
        <button onclick="toggleSidebar()" id="sidebar-btn">Notes (<span id="count">0</span>)</button>
        <button onclick="location.reload()">Refresh</button>
    </div>
</div>

<div class="container">
    <div id="content">{html_content}</div>
</div>

<div id="note-popup">
    <div class="popup-header">Add annotation</div>
    <div class="selected-text" id="popup-selected"></div>
    <textarea id="popup-note" placeholder="What should be changed?"></textarea>
    <div class="popup-actions">
        <button class="btn-cancel" onclick="closePopup()">Cancel</button>
        <button class="btn-save" onclick="saveAnnotation()">Save (Ctrl+Enter)</button>
    </div>
</div>

<div id="sidebar">
    <h3>Annotations</h3>
    <div id="annotations-list"></div>
</div>

<script>
let annotations = {json.dumps(annotations)};
let pendingSelection = null;

function updateCount() {{
    document.getElementById('count').textContent = annotations.length;
    document.getElementById('status').textContent =
        annotations.length > 0
            ? annotations.length + ' annotation(s)'
            : 'Select text to annotate';
}}

document.getElementById('content').addEventListener('mouseup', function(e) {{
    setTimeout(function() {{
        const selection = window.getSelection();
        const text = selection.toString().trim();

        if (text.length > 2) {{
            pendingSelection = {{ text: text }};

            const range = selection.getRangeAt(0);
            const rect = range.getBoundingClientRect();
            const popup = document.getElementById('note-popup');

            popup.style.display = 'block';
            popup.style.top = Math.min(rect.bottom + window.scrollY + 10, document.body.scrollHeight - 250) + 'px';
            popup.style.left = Math.min(rect.left, window.innerWidth - 370) + 'px';
            popup.style.position = 'absolute';

            document.getElementById('popup-selected').textContent =
                text.length > 150 ? text.substring(0, 150) + '...' : text;
            document.getElementById('popup-note').value = '';
            document.getElementById('popup-note').focus();
        }}
    }}, 10);
}});

function closePopup() {{
    document.getElementById('note-popup').style.display = 'none';
    pendingSelection = null;
    window.getSelection().removeAllRanges();
}}

function saveAnnotation() {{
    if (!pendingSelection) return;

    const note = document.getElementById('popup-note').value.trim();
    annotations.push({{
        text: pendingSelection.text,
        note: note || '(no note)',
        timestamp: new Date().toISOString(),
    }});

    fetch('/api/annotations', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify(annotations),
    }}).then(() => {{
        updateCount();
        renderSidebar();
        highlightAnnotations();
        closePopup();
    }});
}}

function deleteAnnotation(idx) {{
    annotations.splice(idx, 1);
    fetch('/api/annotations', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify(annotations),
    }}).then(() => {{
        updateCount();
        renderSidebar();
        highlightAnnotations();
    }});
}}

function toggleSidebar() {{
    document.getElementById('sidebar').classList.toggle('open');
    document.body.classList.toggle('sidebar-open');
    renderSidebar();
}}

function renderSidebar() {{
    const list = document.getElementById('annotations-list');
    if (annotations.length === 0) {{
        list.innerHTML = '<p style="color:#8b949e;font-size:13px;">No annotations yet. Select text to add one.</p>';
        return;
    }}
    list.innerHTML = annotations.map((a, i) => `
        <div class="annotation-card" onclick="scrollToAnnotation(${{i}})">
            <span class="delete-btn" onclick="event.stopPropagation(); deleteAnnotation(${{i}})">delete</span>
            <span class="idx">#${{i + 1}}</span>
            <span class="highlighted">${{escapeHtml(truncate(a.text, 100))}}</span>
            <div class="note">${{escapeHtml(a.note)}}</div>
        </div>
    `).join('');
}}

function scrollToAnnotation(idx) {{
    const els = document.querySelectorAll('.annotated-text');
    if (els[idx]) {{
        els[idx].scrollIntoView({{ behavior: 'smooth', block: 'center' }});
        els[idx].style.background = '#ffc107';
        setTimeout(() => els[idx].style.background = '#fff3cd', 1500);
    }}
}}

function truncate(s, n) {{ return s.length > n ? s.substring(0, n) + '...' : s; }}

function escapeHtml(text) {{
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}}

function highlightAnnotations() {{
    // Remove existing highlights
    document.querySelectorAll('.annotated-text, .annotation-indicator').forEach(el => {{
        if (el.classList.contains('annotation-indicator')) {{
            el.remove();
        }} else {{
            el.replaceWith(...el.childNodes);
        }}
    }});

    const content = document.getElementById('content');

    annotations.forEach((annotation, idx) => {{
        const searchText = annotation.text.substring(0, 200);
        const treeWalker = document.createTreeWalker(content, NodeFilter.SHOW_TEXT);

        let node;
        while (node = treeWalker.nextNode()) {{
            const pos = node.textContent.indexOf(searchText);
            if (pos !== -1) {{
                const range = document.createRange();
                range.setStart(node, pos);
                range.setEnd(node, Math.min(pos + searchText.length, node.textContent.length));

                const wrapper = document.createElement('span');
                wrapper.className = 'annotated-text';
                wrapper.title = annotation.note;
                wrapper.onclick = function() {{
                    if (!document.getElementById('sidebar').classList.contains('open')) toggleSidebar();
                }};

                try {{
                    range.surroundContents(wrapper);
                    const badge = document.createElement('span');
                    badge.className = 'annotation-indicator';
                    badge.textContent = idx + 1;
                    badge.title = annotation.note;
                    wrapper.after(badge);
                }} catch(e) {{}}

                break;
            }}
        }}
    }});
}}

document.addEventListener('keydown', function(e) {{
    if (e.key === 'Escape') closePopup();
    if (e.key === 'Enter' && e.ctrlKey && document.getElementById('note-popup').style.display !== 'none') {{
        e.preventDefault();
        saveAnnotation();
    }}
}});

updateCount();
highlightAnnotations();
</script>
</body>
</html>"""


CSS = """<style>
* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
    line-height: 1.6;
    color: #24292e;
    background: #f6f8fa;
}

.container {
    max-width: 900px;
    margin: 0 auto;
    padding: 40px 20px;
}

.toolbar {
    position: fixed;
    top: 0; left: 0; right: 0;
    background: #24292e;
    color: white;
    padding: 10px 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    z-index: 1000;
    font-size: 14px;
}

.toolbar .title { font-weight: 600; }
.toolbar .status { color: #8b949e; }

.toolbar button {
    background: #238636;
    color: white;
    border: none;
    padding: 6px 16px;
    border-radius: 6px;
    cursor: pointer;
    font-size: 13px;
    font-weight: 500;
    margin-left: 6px;
}

.toolbar button:hover { background: #2ea043; }

#content {
    background: white;
    padding: 45px;
    border-radius: 6px;
    border: 1px solid #d0d7de;
    margin-top: 50px;
}

#content h1 { font-size: 2em; margin: 0.67em 0; border-bottom: 1px solid #d0d7de; padding-bottom: 0.3em; }
#content h2 { font-size: 1.5em; margin: 1em 0 0.5em; border-bottom: 1px solid #d0d7de; padding-bottom: 0.3em; }
#content h3 { font-size: 1.25em; margin: 1em 0 0.5em; }
#content p { margin: 0 0 16px; }
#content img { max-width: 100%; }
#content table { border-collapse: collapse; width: 100%; margin: 16px 0; }
#content th, #content td { border: 1px solid #d0d7de; padding: 8px 13px; text-align: left; }
#content th { background: #f6f8fa; font-weight: 600; }
#content pre { background: #f6f8fa; padding: 16px; border-radius: 6px; overflow-x: auto; margin: 16px 0; }
#content code { font-family: 'SFMono-Regular', Consolas, monospace; font-size: 85%; }
#content blockquote { padding: 0 16px; color: #57606a; border-left: 4px solid #d0d7de; margin: 16px 0; }
#content ul, #content ol { padding-left: 2em; margin: 16px 0; }

.annotated-text {
    background: #fff3cd;
    border-bottom: 2px solid #f0ad4e;
    cursor: pointer;
    padding: 1px 2px;
    border-radius: 2px;
    transition: background 0.3s;
}

.annotated-text:hover { background: #ffe69c; }

.annotation-indicator {
    display: inline-block;
    background: #f0ad4e;
    color: white;
    font-size: 10px;
    font-weight: bold;
    width: 16px; height: 16px;
    line-height: 16px;
    text-align: center;
    border-radius: 50%;
    margin-left: 2px;
    vertical-align: super;
    cursor: pointer;
}

#note-popup {
    display: none;
    position: absolute;
    background: white;
    border: 2px solid #0969da;
    border-radius: 8px;
    padding: 16px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.2);
    z-index: 2000;
    width: 350px;
}

#note-popup .popup-header { font-size: 12px; color: #57606a; margin-bottom: 8px; font-weight: 600; }

#note-popup .selected-text {
    background: #fff3cd;
    padding: 8px;
    border-radius: 4px;
    font-size: 13px;
    margin-bottom: 8px;
    max-height: 80px;
    overflow-y: auto;
    border: 1px solid #f0ad4e;
}

#note-popup textarea {
    width: 100%;
    height: 80px;
    border: 1px solid #d0d7de;
    border-radius: 6px;
    padding: 8px;
    font-family: inherit;
    font-size: 13px;
    resize: vertical;
    margin-bottom: 8px;
}

#note-popup textarea:focus { outline: none; border-color: #0969da; box-shadow: 0 0 0 3px rgba(9,105,218,0.15); }

#note-popup .popup-actions { display: flex; gap: 8px; justify-content: flex-end; }

#note-popup .popup-actions button {
    padding: 5px 14px;
    border-radius: 6px;
    font-size: 12px;
    cursor: pointer;
    font-weight: 500;
}

#note-popup .btn-save { background: #0969da; color: white; border: none; }
#note-popup .btn-save:hover { background: #0860ca; }
#note-popup .btn-cancel { background: white; color: #24292e; border: 1px solid #d0d7de; }

#sidebar {
    position: fixed;
    top: 44px; right: 0;
    width: 320px; bottom: 0;
    background: white;
    border-left: 1px solid #d0d7de;
    overflow-y: auto;
    padding: 16px;
    display: none;
    z-index: 999;
}

#sidebar.open { display: block; }
#sidebar h3 { font-size: 14px; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid #d0d7de; }

.annotation-card {
    background: #f6f8fa;
    border: 1px solid #d0d7de;
    border-radius: 6px;
    padding: 12px;
    margin-bottom: 10px;
    font-size: 13px;
    cursor: pointer;
    transition: border-color 0.2s;
}

.annotation-card:hover { border-color: #0969da; }

.annotation-card .idx { font-weight: 700; color: #f0ad4e; font-size: 11px; }

.annotation-card .highlighted {
    background: #fff3cd;
    padding: 4px 6px;
    border-radius: 3px;
    font-size: 12px;
    margin: 4px 0;
    display: block;
    border-left: 3px solid #f0ad4e;
}

.annotation-card .note { color: #24292e; margin-top: 6px; }

.annotation-card .delete-btn {
    float: right;
    color: #cf222e;
    cursor: pointer;
    font-size: 11px;
    opacity: 0.6;
}

.annotation-card .delete-btn:hover { opacity: 1; }

body.sidebar-open .container { margin-right: 340px; }
</style>"""
