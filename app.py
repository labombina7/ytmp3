import os
import subprocess
import unicodedata
import threading
import queue
import json
from flask import Flask, request, jsonify, send_from_directory, Response, stream_with_context

app = Flask(__name__)
download_queue = queue.Queue()
DOWNLOAD_PATH = "/app/downloads"

download_status = {}
clients = []

def clean_filename(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    return "".join(c if c.isalnum() or c in " .-_()" else "_" for c in s).strip()

def get_output_dir(url):
    try:
        result = subprocess.run(
            ["yt-dlp", "--skip-download", "--print", "%(artist)s|%(album)s", url],
            capture_output=True, text=True, timeout=10
        )
        raw = result.stdout.strip()

        # Protección contra salida inesperada
        parts = raw.split("|")
        artist = parts[0] if len(parts) > 0 else ""
        album = parts[1] if len(parts) > 1 else ""

        if artist.upper() == "NA":
            artist = ""
        if album.upper() == "NA":
            album = ""

        # Limpieza de colaboraciones
        if "feat." in artist.lower():
            artist = artist.split("feat.")[0].strip()
        elif "," in artist:
            artist = artist.split(",")[0].strip()

        base = f"{artist.strip()} - {album.strip()}".strip(" -") or "general"

    except Exception as e:
        print("⚠️ Error generando nombre de carpeta:", e)
        base = "general"

    safe_name = clean_filename(base)
    return os.path.join(DOWNLOAD_PATH, safe_name or "general")

def broadcast_event(event_json_str):
    for q in clients:
        q.put(event_json_str)

def download_worker():
    while True:
        job = download_queue.get()
        if job is None:
            break

        url = job["url"]
        format = job["format"]
        title = job["title"]

        vid_id = job["id"]
        download_status[vid_id]["status"] = "descargando"
        broadcast_event(json.dumps({"id": vid_id, "url": url, "title": title, "status": "descargando"}))

        output_dir = get_output_dir(url)
        os.makedirs(output_dir, exist_ok=True)

        if format == "mp3":
            title_raw = job.get("title", "")
            artist_clean = "Desconocido"
            album_clean = "Sin álbum"

            try:
                meta = subprocess.run(
                    ["yt-dlp", "--skip-download", "--print", "%(artist)s|%(album)s", url],
                    capture_output=True, text=True, timeout=10
                ).stdout.strip()

                raw_artist, raw_album = meta.split("|")

                if "feat." in raw_artist.lower():
                    artist_clean = raw_artist.split("feat.")[0].strip()
                elif "," in raw_artist:
                    artist_clean = raw_artist.split(",")[0].strip()
                else:
                    artist_clean = raw_artist.strip()

                album_clean = raw_album.split("(")[0].split("[")[0].strip()
                if not album_clean:
                    album_clean = "Sin álbum"
            except Exception as e:
                print(f"⚠️ No se pudieron obtener o limpiar metadatos: {e}")

            # Limpieza final de strings para evitar errores de ffmpeg
            artist_clean = clean_filename(artist_clean)
            album_clean = clean_filename(album_clean)

            try:
                track_number_int = int(job.get("track_number"))
            except (TypeError, ValueError):
                track_number_int = None

            if track_number_int:
                filename = f"{track_number_int:02d} - %(title)s.%(ext)s"
            else:
                filename = "%(title)s.%(ext)s"
            
            output_path = os.path.join(output_dir, filename)
            track_number = job.get("track_number")
            track_tag = f"-metadata track={track_number}" if track_number else ""

            command = [
                "yt-dlp",
                "-x", "--audio-format", "mp3",
                "--audio-quality", "0", "--prefer-ffmpeg",
                "--no-keep-video",
                "--embed-thumbnail", "--add-metadata", "--embed-metadata",
                "--convert-thumbnails", "jpg",
                "--postprocessor-args",
                f"ffmpeg:-metadata artist='{artist_clean}' -metadata album='{album_clean}' {track_tag}",
                "-o", output_path,
                url
            ]
        else:
            output_path = os.path.join(output_dir, clean_filename("%(title)s.%(ext)s"))
            command = [
                "yt-dlp", "--format", "bestvideo+bestaudio",
                "--merge-output-format", "mp4",
                "-o", output_path,
                url
            ]

        print(f"[cola] Descargando {format.upper()}: {url}")
        try:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in process.stdout:
                print(f"[yt-dlp] {line.strip()}")
            process.wait()
        except Exception as e:
            print(f"❌ Error ejecutando yt-dlp: {e}")
        finally:
            download_status[vid_id]["status"] = "completado"
            broadcast_event(json.dumps({"id": vid_id, "url": url, "title": title, "status": "completado"}))
            download_queue.task_done()

threading.Thread(target=download_worker, daemon=True).start()

@app.route("/add", methods=["POST"])
def add_url():
    data = request.get_json()
    url = data.get("url")
    format = data.get("format", "mp3")
    if not url:
        return jsonify({"error": "URL missing"}), 400

    list_command = ["yt-dlp", "--flat-playlist", "--print", "%(title)s|%(id)s", url]
    result = subprocess.run(list_command, capture_output=True, text=True)
    lines = result.stdout.strip().splitlines()

    videos = []
    for i, line in enumerate(lines, 1):
        try:
            title, vid_id = line.strip().split("|", 1)
            if not vid_id or vid_id == "NA":
                continue

            full_url = f"https://www.youtube.com/watch?v={vid_id}"
            videos.append({"title": title, "url": full_url, "id": vid_id})
            download_status[vid_id] = {"title": title, "format": format, "status": "pendiente"}

            download_queue.put({
                "url": full_url,
                "id": vid_id,
                "format": format,
                "title": title,
                "track_number": i
            })
        except ValueError:
            print(f"❌ Línea malformada (omitida): {line}")
            continue

    print(f"📥 Añadidos {len(videos)} elementos desde {url}")
    return jsonify({"status": "added", "videos": videos})

@app.route("/status")
def status():
    return jsonify({"queued": download_queue.qsize()})

@app.route("/stream")
def stream():
    def event_stream(client_queue):
        try:
            while True:
                event = client_queue.get()
                yield f"data: {event}\n\n"
        except GeneratorExit:
            print("Cliente SSE desconectado")
            clients.remove(client_queue)

    q = queue.Queue()
    clients.append(q)
    return Response(stream_with_context(event_stream(q)), mimetype='text/event-stream')

@app.route("/")
def home():
    return send_from_directory("public", "index.html")

@app.route("/<path:path>")
def static_files(path):
    return send_from_directory("public", path)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5558)