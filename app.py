#!/usr/bin/env python3
# app.py
"""
YouTube Downloader Webapp with progress bar (Flask + yt-dlp)
- Modes: video+audio, audio only, video only
- Progress tracked via polling
"""

import os
import re
import uuid
import shutil
import tempfile
import threading
from flask import Flask, request, render_template_string, jsonify, send_file, after_this_request
from yt_dlp import YoutubeDL
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Global dict for tracking tasks
tasks = {}
lock = threading.Lock()

INDEX_HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>YouTube Downloader</title>
  <style>
    body { font-family: sans-serif; margin: 2rem; }
    .progress { width:100%; background:#eee; border-radius:8px; overflow:hidden; margin:1rem 0; }
    .bar { width:0%; height:20px; background:#2f6fef; text-align:center; color:white; font-size:0.8rem; }
  </style>
</head>
<body>
  <h1>YouTube Downloader</h1>
  <form id="dlform">
    <label>URL: <input type="text" name="url" required style="width:60%"></label><br><br>
    <label>Mode:
      <select name="mode">
        <option value="video">Video+Audio</option>
        <option value="audio">Audio Only</option>
        <option value="video_only">Video Only</option>
      </select>
    </label>
    <button type="submit">Download</button>
  </form>
  <div id="progress" style="display:none;">
    <div class="progress"><div class="bar" id="bar">0%</div></div>
    <div id="status"></div>
  </div>
  <script>
    const form = document.getElementById('dlform');
    form.onsubmit = async (e)=>{
      e.preventDefault();
      document.getElementById('progress').style.display='block';
      let fd = new FormData(form);
      let res = await fetch('/start', {method:'POST', body:fd});
      let data = await res.json();
      let id = data.id;
      let interval = setInterval(async ()=>{
        let pr = await fetch('/progress/'+id);
        let pd = await pr.json();
        let bar = document.getElementById('bar');
        bar.style.width = pd.percent + '%';
        bar.textContent = pd.percent + '%';
        document.getElementById('status').textContent = pd.status;
        if(pd.status==='done'){
          clearInterval(interval);
          window.location = '/fetch/'+id;
        } else if(pd.status==='error'){
          clearInterval(interval);
          alert('Error: '+pd.error);
        }
      },1000);
    }
  </script>
</body>
</html>
"""

def sanitize_filename(s: str) -> str:
    return secure_filename(re.sub(r'[\\/:"*?<>|]+', "", s).strip()) or "yt_file"

def run_download(task_id, url, mode):
    tmpdir = tempfile.mkdtemp(prefix="yt_")
    outtmpl = os.path.join(tmpdir, "%(title)s.%(ext)s")

    def progress_hook(d):
        with lock:
            if d['status'] == 'downloading':
                percent = d.get('_percent_str', '0.0%').strip().replace('%','')
                try:
                    percent = int(float(percent))
                except:
                    percent = 0
                tasks[task_id]['percent'] = percent
                tasks[task_id]['status'] = 'downloading'
            elif d['status'] == 'finished':
                tasks[task_id]['percent'] = 100
                tasks[task_id]['status'] = 'processing'

    ydl_opts = {
        'outtmpl': outtmpl,
        'progress_hooks': [progress_hook],
        'quiet': True,
    }

    if mode=='video':
        ydl_opts['format'] = 'bestvideo+bestaudio/best'
        ydl_opts['merge_output_format'] = 'mp4'
    elif mode=='audio':
        ydl_opts['format'] = 'bestaudio/best'
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    elif mode=='video_only':
        ydl_opts['format'] = 'bestvideo[ext=mp4]/bestvideo'
    else:
        tasks[task_id]['status'] = 'error'
        tasks[task_id]['error'] = 'Invalid mode'
        return

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
        files = [os.path.join(tmpdir,f) for f in os.listdir(tmpdir)]
        filepath = max(files, key=os.path.getsize)
        tasks[task_id]['status']='done'
        tasks[task_id]['file']=filepath
        tasks[task_id]['title']=sanitize_filename(info.get('title','yt'))
    except Exception as e:
        tasks[task_id]['status']='error'
        tasks[task_id]['error']=str(e)

@app.route("/")
def index():
    return render_template_string(INDEX_HTML)

@app.route("/start", methods=["POST"])
def start():
    url = request.form.get("url","").strip()
    mode = request.form.get("mode","video")
    task_id = str(uuid.uuid4())
    with lock:
        tasks[task_id]={'status':'starting','percent':0}
    threading.Thread(target=run_download,args=(task_id,url,mode),daemon=True).start()
    return jsonify({'id':task_id})

@app.route("/progress/<task_id>")
def progress(task_id):
    with lock:
        task = tasks.get(task_id)
        if not task: return jsonify({'status':'error','error':'no such task'})
        return jsonify({'status':task['status'], 'percent':task.get('percent',0), 'error':task.get('error')})

@app.route("/fetch/<task_id>")
def fetch(task_id):
    with lock:
        task = tasks.get(task_id)
    if not task or task['status']!='done':
        return "Not ready", 404
    filepath = task['file']
    filename = task['title']+os.path.splitext(filepath)[1]
    @after_this_request
    def cleanup(resp):
        try: os.remove(filepath)
        except: pass
        try: shutil.rmtree(os.path.dirname(filepath))
        except: pass
        with lock: tasks.pop(task_id,None)
        return resp
    return send_file(filepath, as_attachment=True, download_name=filename)

if __name__=="__main__":
    port=int(os.environ.get("PORT",5000))
    app.run(host="0.0.0.0", port=port)
