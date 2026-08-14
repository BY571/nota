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
    <span class="title">nota: {filename}</span>
    <span class="status" id="status">Select text to annotate</span>
    <div>
        <button onclick="toggleChanges()" id="changes-btn" class="btn-changes">Changes (<span id="diff-count">0</span>)</button>
        <button onclick="toggleSidebar()" id="sidebar-btn">Notes (<span id="count">0</span>)</button>
        <button onclick="clearAndReload()">Refresh</button>
    </div>
</div>

<div class="container">
    <div id="content">{html_content}</div>

    <div id="diff-view">
        <div class="diff-bar">
            <span id="diff-summary">No changes since the baseline</span>
            <div>
                <button class="btn-reject-all" onclick="resolveAll('reject')">Reject all</button>
                <button class="btn-accept-all" onclick="resolveAll('accept')">Accept all</button>
            </div>
        </div>
        <div id="diff-body"></div>
    </div>
</div>

<div id="note-popup">
    <div class="popup-header" id="popup-header">Add annotation</div>
    <div class="selected-text" id="popup-selected"></div>
    <textarea id="popup-note" placeholder="What should be changed?"></textarea>
    <div class="popup-actions">
        <button class="btn-cancel" onclick="closePopup()">Cancel</button>
        <button class="btn-save-accept" id="popup-accept" onclick="saveAnnotation(true)">Accept &amp; comment</button>
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

// --- Popup event isolation ---
document.getElementById('note-popup').addEventListener('mouseup', function(e) {{ e.stopPropagation(); }});
document.getElementById('note-popup').addEventListener('mousedown', function(e) {{ e.stopPropagation(); }});

// --- Text selection annotations ---
document.getElementById('content').addEventListener('mouseup', function(e) {{
    if (document.getElementById('note-popup').style.display === 'block') return;
    // Ignore clicks on add-note buttons and media
    if (e.target.closest('.add-note-btn') || e.target.closest('.media-annotatable')) return;

    setTimeout(function() {{
        const selection = window.getSelection();
        const text = selection.toString().trim();

        if (text.length > 2) {{
            pendingSelection = {{ text: text, type: 'text' }};
            showPopup(
                selection.getRangeAt(0).getBoundingClientRect(),
                'Annotate selected text',
                text.length > 150 ? text.substring(0, 150) + '...' : text
            );
        }}
    }}, 10);
}});

// --- Block-level "+" buttons ---
function initBlockButtons() {{
    const blocks = document.querySelectorAll('#content > p, #content > h1, #content > h2, #content > h3, #content > h4, #content > h5, #content > h6, #content > blockquote, #content > pre, #content > table, #content > ul, #content > ol');

    blocks.forEach((block, idx) => {{
        block.style.position = 'relative';
        block.dataset.blockIdx = idx;

        const btn = document.createElement('button');
        btn.className = 'add-note-btn';
        btn.textContent = '+';
        btn.title = 'Add note after this element';
        btn.addEventListener('click', function(e) {{
            e.stopPropagation();
            if (document.getElementById('note-popup').style.display === 'block') {{ closePopup(); return; }}

            const blockText = block.textContent.trim();
            const preview = blockText.length > 80 ? blockText.substring(0, 80) + '...' : blockText;
            const tag = block.tagName.toLowerCase();

            pendingSelection = {{
                text: '[after: ' + tag + '] ' + preview,
                type: 'block',
                blockTag: tag,
                blockIdx: idx,
            }};
            showPopup(
                block.getBoundingClientRect(),
                'Add note after this ' + tag,
                preview || '(empty block)'
            );
        }});

        block.appendChild(btn);
    }});
}}

// --- Media annotations (images, gifs, videos) ---
function initMediaAnnotations() {{
    const mediaEls = document.querySelectorAll('#content img, #content video');

    mediaEls.forEach((el) => {{
        const wrapper = document.createElement('div');
        wrapper.className = 'media-annotatable';
        el.parentNode.insertBefore(wrapper, el);
        wrapper.appendChild(el);

        const overlay = document.createElement('div');
        overlay.className = 'media-overlay';
        overlay.innerHTML = '<span class="media-note-btn">+ Add note</span>';
        wrapper.appendChild(overlay);

        overlay.addEventListener('click', function(e) {{
            e.stopPropagation();
            if (document.getElementById('note-popup').style.display === 'block') {{ closePopup(); return; }}

            const src = el.getAttribute('src') || '';
            const alt = el.getAttribute('alt') || '';
            const label = alt || src.split('/').pop();

            pendingSelection = {{
                text: '[media] ' + label,
                type: 'media',
                src: src,
                alt: alt,
            }};
            showPopup(
                wrapper.getBoundingClientRect(),
                'Annotate image/media',
                label
            );
        }});
    }});
}}

// --- Shared popup logic ---
function showPopup(rect, header, previewText) {{
    const popup = document.getElementById('note-popup');
    document.getElementById('popup-accept').style.display = 'none';
    popup.style.display = 'block';
    popup.style.position = 'absolute';
    popup.style.top = Math.min(rect.bottom + window.scrollY + 10, document.body.scrollHeight - 250) + 'px';
    popup.style.left = Math.min(rect.left, window.innerWidth - 370) + 'px';

    document.getElementById('popup-header').textContent = header;
    document.getElementById('popup-selected').textContent = previewText;
    document.getElementById('popup-note').value = '';
    document.getElementById('popup-note').focus();
}}

function closePopup() {{
    document.getElementById('note-popup').style.display = 'none';
    pendingSelection = null;
    window.getSelection().removeAllRanges();
}}

function saveAnnotation(alsoAccept) {{
    if (!pendingSelection) return;

    const note = document.getElementById('popup-note').value.trim();
    const entry = {{
        text: pendingSelection.text,
        type: pendingSelection.type || 'text',
        note: note || '(no note)',
        timestamp: new Date().toISOString(),
    }};
    if (entry.type === 'change') {{
        entry.chunkKey = pendingSelection.chunkKey;
        entry.before = pendingSelection.before;
        entry.after = pendingSelection.after;
        entry.resolution = alsoAccept ? 'accepted' : 'pending';
    }}
    annotations.push(entry);

    const wasChange = entry.type === 'change';
    const chunkIdx = pendingSelection.chunkIdx;

    fetch('/api/annotations', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify(annotations),
    }}).then(() => {{
        updateCount();
        renderSidebar();
        highlightAnnotations();
        closePopup();
        if (wasChange) {{
            if (alsoAccept) resolveHunk(chunkIdx, 'accept');
            else loadDiff();
        }}
    }});
}}

function deleteComment(idx) {{
    annotations.splice(idx, 1);
    fetch('/api/annotations', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify(annotations),
    }}).then(() => {{
        updateCount();
        renderSidebar();
        loadDiff();
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
    list.innerHTML = annotations.map((a, i) => {{
        const typeIcon = a.type === 'media' ? '🖼' : a.type === 'block' ? '¶'
            : a.type === 'change' ? '±' : '✎';
        const open = a.type === 'change'
            ? `goToChunk('${{a.chunkKey}}')`
            : `scrollToAnnotation(${{i}})`;
        return `
        <div class="annotation-card" onclick="${{open}}">
            <span class="delete-btn" onclick="event.stopPropagation(); deleteAnnotation(${{i}})">delete</span>
            <span class="idx">${{typeIcon}} #${{i + 1}}</span>
            <span class="highlighted">${{escapeHtml(truncate(a.text, 100))}}</span>
            <div class="note">${{escapeHtml(a.note)}}</div>
        </div>`;
    }}).join('');
}}

function goToChunk(key) {{
    if (!diffMode) toggleChanges();
    setTimeout(function() {{
        const seg = diffSegments.find(s => s.type === 'hunk' && s.key === key);
        const el = seg && document.getElementById('hunk-' + seg.idx);
        if (el) el.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
    }}, 300);
}}

function scrollToAnnotation(idx) {{
    const els = document.querySelectorAll('.annotated-text, .annotated-block, .annotated-media');
    if (els[idx]) {{
        els[idx].scrollIntoView({{ behavior: 'smooth', block: 'center' }});
        els[idx].classList.add('flash');
        setTimeout(() => els[idx].classList.remove('flash'), 1500);
    }}
}}

function truncate(s, n) {{ return s.length > n ? s.substring(0, n) + '...' : s; }}

function escapeHtml(text) {{
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}}

function highlightAnnotations() {{
    // Remove old text highlights
    document.querySelectorAll('.annotated-text, .annotation-indicator').forEach(el => {{
        if (el.classList.contains('annotation-indicator')) el.remove();
        else el.replaceWith(...el.childNodes);
    }});
    // Remove old block/media highlights
    document.querySelectorAll('.annotated-block, .annotated-media').forEach(el => {{
        el.classList.remove('annotated-block', 'annotated-media');
    }});

    const content = document.getElementById('content');

    annotations.forEach((annotation, idx) => {{
        if (annotation.type === 'change') {{
            // Lives in the Changes view, not in the rendered document.
            return;
        }} else if (annotation.type === 'media') {{
            // Find media by src
            const src = annotation.src || '';
            const el = content.querySelector(`img[src="${{src}}"], video[src="${{src}}"]`);
            if (el) {{
                const wrapper = el.closest('.media-annotatable') || el;
                wrapper.classList.add('annotated-media');
            }}
        }} else if (annotation.type === 'block') {{
            // Find block by index
            const blocks = content.querySelectorAll(':scope > p, :scope > h1, :scope > h2, :scope > h3, :scope > h4, :scope > h5, :scope > h6, :scope > blockquote, :scope > pre, :scope > table, :scope > ul, :scope > ol');
            const blockIdx = annotation.blockIdx;
            if (blockIdx !== undefined && blocks[blockIdx]) {{
                blocks[blockIdx].classList.add('annotated-block');
            }}
        }} else {{
            // Text highlight
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
        }}
    }});
}}

// --- Change review (PR-style diff against the baseline snapshot) ---
let diffMode = false;
let lastMtime = null;
let diffSegments = [];

function toggleChanges() {{
    diffMode = !diffMode;
    history.replaceState(null, '', diffMode ? '#changes' : location.pathname);
    document.getElementById('diff-view').classList.toggle('open', diffMode);
    document.getElementById('content').style.display = diffMode ? 'none' : 'block';
    document.getElementById('changes-btn').classList.toggle('active', diffMode);
    if (diffMode) loadDiff();
}}

function loadDiff() {{
    // Comments live in the annotations file, so pull both together.
    Promise.all([
        fetch('/api/diff').then(r => r.json()),
        fetch('/api/annotations').then(r => r.json()),
    ]).then(([data, notes]) => {{
        annotations = notes;
        lastMtime = data.mtime;
        diffSegments = data.segments;
        updateCount();
        updateDiffCount(data.count);
        renderDiff(data);
    }});
}}

function commentOnChunk(idx) {{
    const seg = diffSegments.find(s => s.type === 'hunk' && s.idx === idx);
    if (!seg) return;
    const body = seg.new_text || seg.old_text || '';

    pendingSelection = {{
        text: '[change] ' + (body.length > 120 ? body.substring(0, 120) + '...' : body),
        type: 'change',
        chunkKey: seg.key,
        chunkIdx: idx,
        before: seg.old_text,
        after: seg.new_text,
    }};

    const el = document.getElementById('hunk-' + idx);
    showPopup(
        el.getBoundingClientRect(),
        'What should be different about this change?',
        body.length > 150 ? body.substring(0, 150) + '...' : body
    );
    document.getElementById('popup-accept').style.display = 'inline-block';
}}

function chunkComments(key) {{
    return annotations
        .map((a, i) => ({{ a: a, i: i }}))
        .filter(x => x.a.type === 'change' && x.a.chunkKey === key);
}}

function updateDiffCount(count) {{
    document.getElementById('diff-count').textContent = count;
    document.getElementById('changes-btn').classList.toggle('has-changes', count > 0);
    document.getElementById('diff-summary').textContent =
        count > 0
            ? count + ' change' + (count === 1 ? '' : 's') + ' since the baseline'
            : 'No changes since the baseline';
}}

function renderDiff(data) {{
    const body = document.getElementById('diff-body');

    if (data.count === 0) {{
        body.innerHTML = '<div class="diff-empty">Nothing changed yet.<br>' +
            'Edits made to the file after nota started show up here as reviewable chunks.</div>';
        return;
    }}

    body.innerHTML = data.segments.map(seg => {{
        if (seg.type === 'equal') {{
            return '<div class="seg-equal">' + seg.html + '</div>';
        }}
        const n = seg.idx + 1;
        const label = !seg.old_html ? 'Added' : !seg.new_html ? 'Removed' : 'Changed';
        let sides = '';
        if (seg.old_html) {{
            sides += '<div class="side side-old"><span class="side-tag">− before</span>' + seg.old_html + '</div>';
        }}
        if (seg.new_html) {{
            sides += '<div class="side side-new"><span class="side-tag">+ after</span>' + seg.new_html + '</div>';
        }}

        const comments = chunkComments(seg.key);
        const thread = comments.length === 0 ? '' : `
            <div class="hunk-comments">
                ${{comments.map(c => `
                <div class="hunk-comment">
                    <span class="comment-del" onclick="deleteComment(${{c.i}})">delete</span>
                    ${{escapeHtml(c.a.note)}}
                </div>`).join('')}}
            </div>`;

        return `
        <div class="hunk${{comments.length ? ' has-comments' : ''}}" id="hunk-${{seg.idx}}">
            <div class="hunk-bar">
                <span class="hunk-label">${{label}} · chunk ${{n}}${{comments.length ? ' · ' + comments.length + ' comment' + (comments.length === 1 ? '' : 's') : ''}}</span>
                <span>
                    <button class="btn-comment" onclick="commentOnChunk(${{seg.idx}})">Comment</button>
                    <button class="btn-reject" onclick="resolveHunk(${{seg.idx}}, 'reject')">Reject</button>
                    <button class="btn-accept" onclick="resolveHunk(${{seg.idx}}, 'accept')">Accept</button>
                </span>
            </div>
            ${{sides}}
            ${{thread}}
        </div>`;
    }}).join('');
}}

function resolveHunk(idx, action) {{
    const el = document.getElementById('hunk-' + idx);
    if (el) el.classList.add('resolving');
    fetch('/api/diff/' + idx + '/' + action, {{ method: 'POST' }})
        .then(r => r.json())
        .then(() => loadDiff());
}}

function resolveAll(action) {{
    const count = parseInt(document.getElementById('diff-count').textContent, 10);
    if (count === 0) return;
    const verb = action === 'accept' ? 'Accept' : 'Reject';
    if (!confirm(verb + ' all ' + count + ' change(s)?')) return;
    fetch('/api/diff/' + action + '_all', {{ method: 'POST' }})
        .then(r => r.json())
        .then(() => loadDiff());
}}

// Pick up edits made by an agent while the page is open.
setInterval(function() {{
    fetch('/api/diff/status').then(r => r.json()).then(data => {{
        updateDiffCount(data.count);
        if (diffMode && data.mtime !== lastMtime) loadDiff();
    }}).catch(() => {{}});
}}, 3000);

function clearAndReload() {{
    fetch('/api/annotations', {{ method: 'DELETE' }}).then(() => location.reload());
}}

document.addEventListener('keydown', function(e) {{
    if (e.key === 'Escape') closePopup();
    if (e.key === 'Enter' && e.ctrlKey && document.getElementById('note-popup').style.display !== 'none') {{
        e.preventDefault();
        saveAnnotation();
    }}
}});

updateCount();
initBlockButtons();
initMediaAnnotations();
highlightAnnotations();
fetch('/api/diff/status').then(r => r.json()).then(d => updateDiffCount(d.count));
if (location.hash === '#changes') toggleChanges();
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

#content h1, #diff-body h1 { font-size: 2em; margin: 0.67em 0; border-bottom: 1px solid #d0d7de; padding-bottom: 0.3em; }
#content h2, #diff-body h2 { font-size: 1.5em; margin: 1em 0 0.5em; border-bottom: 1px solid #d0d7de; padding-bottom: 0.3em; }
#content h3, #diff-body h3 { font-size: 1.25em; margin: 1em 0 0.5em; }
#content p, #diff-body p { margin: 0 0 16px; }
#content img, #diff-body img { max-width: 100%; }
#content table, #diff-body table { border-collapse: collapse; width: 100%; margin: 16px 0; }
#content th, #content td, #diff-body th, #diff-body td { border: 1px solid #d0d7de; padding: 8px 13px; text-align: left; }
#content th, #diff-body th { background: #f6f8fa; font-weight: 600; }
#content pre, #diff-body pre { background: #f6f8fa; padding: 16px; border-radius: 6px; overflow-x: auto; margin: 16px 0; }
#content code, #diff-body code { font-family: 'SFMono-Regular', Consolas, monospace; font-size: 85%; }
#content blockquote, #diff-body blockquote { padding: 0 16px; color: #57606a; border-left: 4px solid #d0d7de; margin: 16px 0; }
#content ul, #content ol, #diff-body ul, #diff-body ol { padding-left: 2em; margin: 16px 0; }

/* Text selection highlights */
.annotated-text {
    background: #fff3cd;
    border-bottom: 2px solid #f0ad4e;
    cursor: pointer;
    padding: 1px 2px;
    border-radius: 2px;
    transition: background 0.3s;
}
.annotated-text:hover { background: #ffe69c; }
.annotated-text.flash { background: #ffc107; }

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

/* Block-level "+" button */
.add-note-btn {
    position: absolute;
    right: -32px;
    top: 50%;
    transform: translateY(-50%);
    width: 24px; height: 24px;
    border-radius: 50%;
    border: 1px solid #d0d7de;
    background: white;
    color: #57606a;
    font-size: 16px;
    line-height: 22px;
    text-align: center;
    cursor: pointer;
    opacity: 0;
    transition: opacity 0.15s, background 0.15s;
    padding: 0;
}

*:hover > .add-note-btn { opacity: 1; }
.add-note-btn:hover { background: #0969da; color: white; border-color: #0969da; }

/* Block annotation highlight */
.annotated-block {
    border-left: 3px solid #f0ad4e !important;
    background: #fffdf5 !important;
    padding-left: 12px !important;
}
.annotated-block.flash { background: #fff3cd !important; }

/* Media annotation support */
.media-annotatable {
    position: relative;
    display: inline-block;
}

.media-overlay {
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    display: flex;
    align-items: flex-start;
    justify-content: flex-end;
    padding: 8px;
    opacity: 0;
    transition: opacity 0.15s;
}

.media-annotatable:hover .media-overlay { opacity: 1; }

.media-note-btn {
    background: rgba(9, 105, 218, 0.9);
    color: white;
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 500;
    cursor: pointer;
}
.media-note-btn:hover { background: rgba(9, 105, 218, 1); }

.annotated-media {
    outline: 3px solid #f0ad4e;
    outline-offset: 2px;
    border-radius: 4px;
}
.annotated-media.flash { outline-color: #ffc107; }

/* --- Change review view --- */
.toolbar .btn-changes { background: #30363d; }
.toolbar .btn-changes:hover { background: #444c56; }
.toolbar .btn-changes.has-changes { background: #9a6700; }
.toolbar .btn-changes.has-changes:hover { background: #bb8009; }
.toolbar .btn-changes.active { background: #0969da; }

#diff-view { display: none; margin-top: 50px; }
#diff-view.open { display: block; }

.diff-bar {
    position: sticky;
    top: 44px;
    z-index: 500;
    background: white;
    border: 1px solid #d0d7de;
    border-radius: 6px;
    padding: 10px 16px;
    margin-bottom: 16px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 13px;
    font-weight: 600;
    color: #57606a;
}

.diff-bar button {
    border: 1px solid #d0d7de;
    border-radius: 6px;
    padding: 5px 14px;
    font-size: 12px;
    font-weight: 500;
    cursor: pointer;
    margin-left: 6px;
    background: white;
}

.diff-bar .btn-accept-all { background: #1a7f37; border-color: #1a7f37; color: white; }
.diff-bar .btn-accept-all:hover { background: #1c8139; }
.diff-bar .btn-reject-all { color: #cf222e; }
.diff-bar .btn-reject-all:hover { background: #ffebe9; border-color: #cf222e; }

#diff-body {
    background: white;
    border: 1px solid #d0d7de;
    border-radius: 6px;
    padding: 45px;
}

.diff-empty { color: #8b949e; font-size: 14px; text-align: center; padding: 40px 0; line-height: 1.8; }

.seg-equal { color: #57606a; }
.seg-equal > *:first-child { margin-top: 0; }

.hunk {
    border: 1px solid #d0d7de;
    border-radius: 6px;
    margin: 20px 0;
    overflow: hidden;
    transition: opacity 0.2s;
}

.hunk.resolving { opacity: 0.4; }

.hunk-bar {
    background: #f6f8fa;
    border-bottom: 1px solid #d0d7de;
    padding: 6px 12px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.hunk-label { font-size: 11px; font-weight: 700; color: #57606a; text-transform: uppercase; letter-spacing: 0.04em; }

.hunk-bar button {
    border-radius: 6px;
    padding: 4px 12px;
    font-size: 12px;
    font-weight: 500;
    cursor: pointer;
    margin-left: 6px;
    border: 1px solid #d0d7de;
    background: white;
}

.hunk-bar .btn-accept { background: #1a7f37; border-color: #1a7f37; color: white; }
.hunk-bar .btn-accept:hover { background: #1c8139; }
.hunk-bar .btn-reject { color: #cf222e; }
.hunk-bar .btn-reject:hover { background: #ffebe9; border-color: #cf222e; }
.hunk-bar .btn-comment { color: #0969da; }
.hunk-bar .btn-comment:hover { background: #ddf4ff; border-color: #0969da; }

.hunk.has-comments { border-color: #0969da; }
.hunk.has-comments .hunk-bar { background: #ddf4ff; border-bottom-color: #0969da; }
.hunk.has-comments .hunk-label { color: #0969da; }

.hunk-comments { border-top: 1px solid #d0d7de; background: #f6f8fa; padding: 4px 12px 10px; }

.hunk-comment {
    background: white;
    border: 1px solid #d0d7de;
    border-left: 3px solid #0969da;
    border-radius: 6px;
    padding: 8px 12px;
    margin-top: 8px;
    font-size: 13px;
    color: #24292e;
}

.hunk-comment .comment-del { float: right; color: #cf222e; cursor: pointer; font-size: 11px; opacity: 0.6; }
.hunk-comment .comment-del:hover { opacity: 1; }

#note-popup .btn-save-accept { display: none; background: #1a7f37; color: white; border: none; }
#note-popup .btn-save-accept:hover { background: #1c8139; }

.side { position: relative; padding: 14px 18px 14px 20px; }
.side > *:first-child { margin-top: 0; }
.side > *:last-child { margin-bottom: 0; }

.side-old { background: #fff5f5; border-left: 4px solid #cf222e; }
.side-new { background: #f2fbf4; border-left: 4px solid #1a7f37; }
.side-old + .side-new { border-top: 1px solid #d0d7de; }

.side-old h1, .side-old h2 { border-bottom-color: #ffcecb; }
.side-new h1, .side-new h2 { border-bottom-color: #b7e2c1; }
.side-old pre { background: #ffebe9; }
.side-new pre { background: #e4f7e9; }

.side-tag {
    display: block;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    margin-bottom: 8px;
}

.side-old .side-tag { color: #cf222e; }
.side-new .side-tag { color: #1a7f37; }

/* Popup */
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

/* Sidebar */
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
