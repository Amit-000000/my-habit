from flask import Flask, request, render_template_string, send_from_directory, jsonify, Response
import os

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
TEMP_FOLDER = 'temp_chunks'

for folder in [UPLOAD_FOLDER, TEMP_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)

# --- Online Fast-Mode Streaming (Video/Audio) ---
def stream_media(path, mime):
    size = os.path.getsize(path)
    range_header = request.headers.get('Range', None)
    
    # Online fast loading ke liye optimized chunk size
    chunk_size = 1024 * 1024 # 1MB

    if not range_header:
        return send_from_directory(UPLOAD_FOLDER, os.path.basename(path))

    byte1, byte2 = 0, None
    m = range_header.replace('bytes=', '').split('-')
    if m[0]: byte1 = int(m[0])
    if m[1]: byte2 = int(m[1])

    length = size - byte1
    if byte2 is not None:
        length = byte2 - byte1 + 1
    else:
        length = min(chunk_size, size - byte1)

    with open(path, 'rb') as f:
        f.seek(byte1)
        data = f.read(length)

    rv = Response(data, 206, mimetype=mime, content_type=mime, direct_passthrough=True)
    rv.headers.add('Content-Range', 'bytes {0}-{1}/{2}'.format(byte1, byte1 + length - 1, size))
    rv.headers.add('Accept-Ranges', 'bytes')
    rv.headers.add('Cache-Control', 'public, max-age=31536000') # Speed boost
    return rv

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="hi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Amit Multi-Cloud</title>
    <style>
        body { font-family: sans-serif; background: #000; color: #fff; margin: 0; padding: 10px; }
        .card { background: #111; border-radius: 12px; padding: 15px; margin-bottom: 15px; border: 1px solid #222; }
        h2 { color: #f00; text-align: center; margin-bottom: 15px; }
        
        .preview-box { width: 100%; max-width: 800px; margin: auto; text-align: center; overflow: hidden; border-radius: 10px; background: #000; }
        video, img { width: 100%; display: block; border-radius: 8px; }
        audio { width: 100%; margin: 15px 0; }

        .q-menu { display: flex; flex-wrap: wrap; justify-content: center; gap: 5px; margin: 10px 0; }
        .q-btn { padding: 6px 10px; font-size: 10px; background: #222; border: 1px solid #444; color: #fff; border-radius: 4px; cursor: pointer; }
        .q-btn.active { background: #f00; border-color: #f00; }

        .file-item { display: flex; justify-content: space-between; align-items: center; padding: 10px; border-bottom: 1px solid #222; }
        .file-name { font-size: 13px; color: #ddd; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 150px; }
        
        .btn { padding: 6px 10px; border-radius: 5px; text-decoration: none; font-size: 11px; font-weight: bold; color: white; }
        .p-btn { background: #f00; }
        .v-btn { background: #007bff; }
        .g-btn { background: #333; }

        .progress-bar { height: 4px; background: #f00; width: 0%; transition: 0.2s; border-radius: 10px; }
    </style>
</head>
<body>

    <div class="card">
        <h2>🔴 AMIT CLOUD</h2>
        <input type="file" id="fileInput" style="font-size: 11px; margin-bottom:10px;"><br>
        <button onclick="startUpload()" style="width:100%; padding:10px; background:#f00; color:#fff; border:none; border-radius:6px; font-weight:bold;">UPLOAD</button>
        <div id="pContainer" style="display:none; background:#222; height:4px; margin-top:10px;"><div id="pBar" class="progress-bar"></div></div>
    </div>

    {% if preview %}
    <div class="card preview-box" id="player">
        {% set ext = preview.lower() %}
        {% if ext.endswith(('.mp4', '.webm', '.mkv')) %}
            <video controls autoplay preload="metadata"><source src="/media/{{ preview }}" type="video/mp4"></video>
            <div class="q-menu">
                <button class="q-btn">144p</button><button class="q-btn">360p</button><button class="q-btn">720p</button><button class="q-btn active">AUTO</button>
            </div>
        {% elif ext.endswith(('.mp3', '.wav', '.ogg')) %}
            <div style="padding: 20px;">🎵 <p style="font-size:12px;">{{ preview }}</p><audio controls autoplay><source src="/media/{{ preview }}" type="audio/mpeg"></audio></div>
        {% elif ext.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')) %}
            <img src="/media/{{ preview }}">
        {% else %}
            <div style="padding: 20px;"><a href="/media/{{ preview }}" style="color:#007bff;">📄 Open File</a></div>
        {% endif %}
        <a href="/" style="display:block; padding:10px; color:#555; text-decoration:none; font-size:11px;">✖ CLOSE</a>
    </div>
    <script>document.getElementById('player').scrollIntoView();</script>
    {% endif %}

    <div class="card">
        <h3 style="font-size: 14px; margin-top:0;">My Library</h3>
        {% for f in files %}
        <div class="file-item">
            <span class="file-name">{{ f }}</span>
            <div style="display:flex; gap:4px;">
                {% set ext = f.lower() %}
                {% if ext.endswith(('.mp4', '.webm', '.mkv', '.mp3', '.wav')) %}
                    <a href="/?view={{ f }}" class="btn p-btn">PLAY</a>
                {% elif ext.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')) %}
                    <a href="/?view={{ f }}" class="btn v-btn">VIEW</a>
                {% else %}
                    <a href="/?view={{ f }}" class="btn v-btn">OPEN</a>
                {% endif %}
                <a href="/download/{{ f }}" class="btn g-btn">GET</a>
            </div>
        </div>
        {% endfor %}
    </div>

<script>
async function startUpload() {
    const file = document.getElementById('fileInput').files[0];
    if(!file) return alert("Select File!");
    document.getElementById('pContainer').style.display = 'block';
    const chunkSize = 1 * 1024 * 1024; // 1MB for stable online upload
    const total = Math.ceil(file.size / chunkSize);
    for (let i = 0; i < total; i++) {
        const fd = new FormData();
        fd.append('file_chunk', file.slice(i*chunkSize, (i+1)*chunkSize));
        fd.append('filename', file.name);
        fd.append('chunk_index', i);
        fd.append('total_chunks', total);
        await fetch('/upload_chunk', {method: 'POST', body: fd});
        document.getElementById('pBar').style.width = Math.round(((i+1)/total)*100) + '%';
    }
    location.href = "/";
}
</script>
</body>
</html>
'''

@app.route('/')
def index():
    files = sorted(os.listdir(UPLOAD_FOLDER), reverse=True)
    preview = request.args.get('view')
    return render_template_string(HTML_TEMPLATE, files=files, preview=preview)

@app.route('/media/<path:filename>')
def serve_media(filename):
    path = os.path.join(UPLOAD_FOLDER, filename)
    ext = filename.lower()
    if ext.endswith(('.mp4', '.webm', '.mkv')):
        return stream_media(path, 'video/mp4')
    elif ext.endswith(('.mp3', '.wav', '.ogg')):
        return stream_media(path, 'audio/mpeg')
    else:
        return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/upload_chunk', methods=['POST'])
def upload_chunk():
    chunk, name, idx, total = request.files['file_chunk'], request.form['filename'], int(request.form['chunk_index']), int(request.form['total_chunks'])
    temp_path = os.path.join(TEMP_FOLDER, name)
    with open(temp_path, "ab") as f: f.write(chunk.read())
    if idx + 1 == total: os.rename(temp_path, os.path.join(UPLOAD_FOLDER, name))
    return jsonify({"ok": True})

@app.route('/download/<path:filename>')
def download_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)