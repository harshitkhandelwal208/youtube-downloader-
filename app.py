from flask import Flask, request, render_template_string, send_file
import os
import zipfile
import yt_dlp

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>YouTube Downloader</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 50px; }
        input[type=text], select, input[type=submit] {
            width: 100%%; padding: 12px; margin: 8px 0;
        }
        input[type=submit] {
            background-color: #4CAF50; color: white; border: none; cursor: pointer;
        }
        input[type=submit]:hover {
            background-color: #45a049;
        }
    </style>
</head>
<body>
    <h2>YouTube Downloader</h2>
    <form method="POST" action="/download">
        <label for="url">YouTube Video or Playlist URL:</label>
        <input type="text" id="url" name="url" required>
        <label for="format">Choose format:</label>
        <select id="format" name="format">
            <option value="audio">Audio (.m4a)</option>
            <option value="video">Video (.mp4)</option>
        </select>
        <input type="submit" value="Download">
    </form>
</body>
</html>
"""

@app.route("/", methods=["GET"])
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route("/download", methods=["POST"])
def download():
    url = request.form["url"]
    format_choice = request.form["format"]
    downloads = []

    try:
        os.makedirs("downloads", exist_ok=True)

        if format_choice == "audio":
            # Direct audio-only in m4a (no ffmpeg needed)
            ydl_opts = {
                "format": "bestaudio[ext=m4a]/bestaudio",  
                "outtmpl": "downloads/%(title)s.%(ext)s"
            }
        else:
            # Best progressive MP4 (video+audio together, no merging)
            ydl_opts = {
                "format": "best[ext=mp4][vcodec!*=vp9]/best[ext=mp4]",  
                "outtmpl": "downloads/%(title)s.%(ext)s"
            }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

            if "entries" in info:  # playlist
                for entry in info["entries"]:
                    if entry:
                        downloads.append(ydl.prepare_filename(entry))
            else:  # single video
                downloads.append(ydl.prepare_filename(info))

        # Zip if multiple files
        if len(downloads) == 1:
            return send_file(downloads[0], as_attachment=True)
        else:
            zip_path = "downloads/downloads.zip"
            with zipfile.ZipFile(zip_path, "w") as zipf:
                for file in downloads:
                    if os.path.exists(file):
                        zipf.write(file, arcname=os.path.basename(file))
            return send_file(zip_path, as_attachment=True)

    except Exception as e:
        return f"<h3>Error: {str(e)}</h3><p><a href='/'>Try again</a></p>"

if __name__ == "__main__":
    app.run(debug=True)
