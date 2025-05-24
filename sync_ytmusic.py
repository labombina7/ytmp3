import requests
import json
from ytmusicapi import YTMusic

YT_API = YTMusic("headers_auth.json")

BACKEND_URL = "http://localhost:5558/add"
CACHE_FILE = "downloaded_cache.json"

def load_cache():
    try:
        with open(CACHE_FILE, "r") as f:
            return set(json.load(f))
    except FileNotFoundError:
        return set()

def save_cache(ids):
    with open(CACHE_FILE, "w") as f:
        json.dump(list(ids), f)

def send_to_backend(url):
    try:
        res = requests.post(BACKEND_URL, json={"url": url, "format": "mp3"})
        print(f"✓ Enviado: {url} → {res.status_code}")
    except Exception as e:
        print(f"❌ Error enviando {url}: {e}")

def get_album_urls():
    try:
        albums = YT_API.get_library_albums(limit=100)
        if not albums:
            print("📁 No se encontraron álbumes en tu biblioteca.")
            return []

        urls = []
        for album in albums:
            album_id = album.get("browseId")
            title = album.get("title", "Sin título")
            if not album_id:
                print(f"⚠️ Álbum sin browseId: {album}")
                continue

            print(f"🎧 Álbum detectado: {title} → ID {album_id}")

            # Extraer canciones individuales del álbum
            try:
                full_album = YT_API.get_album(album_id)
                tracks = full_album.get("tracks", [])
                if not tracks:
                    print(f"⚠️ El álbum '{title}' no tiene canciones accesibles.")
                    continue

                for track in tracks:
                    if track.get("videoId"):
                        url = f"https://music.youtube.com/watch?v={track['videoId']}"
                        urls.append(("track", track["videoId"], url))
                        print(f"   ↪︎ Añadiendo canción: {track.get('title')} → {url}")
                    else:
                        print(f"   ⚠️ Canción sin videoId: {track}")
            except Exception as e:
                print(f"❌ Error al procesar el álbum '{title}': {e}")
        return urls

    except Exception as e:
        print(f"❌ Error general en get_album_urls(): {e}")
        return []

def get_playlist_urls():
    try:
        playlists = YT_API.get_library_playlists(limit=100)
        urls = []
        for pl in playlists or []:
            if pl.get("playlistId"):
                urls.append(("playlist", pl["playlistId"], f"https://music.youtube.com/playlist?list={pl['playlistId']}"))
        return urls
    except Exception as e:
        print(f"⚠️ Error al obtener playlists: {e}")
        return []

def main():
    cached_ids = load_cache()
    new_ids = set()

    # Solo álbumes y playlists
    all_entries = get_album_urls() + get_playlist_urls()

    for item_type, item_id, url in all_entries:
        if item_id not in cached_ids:
            print(f"➕ Nuevo {item_type}: {url}")
            send_to_backend(url)
            new_ids.add(item_id)
        else:
            print(f"⏭️ Ya descargado ({item_type}): {url}")

    if new_ids:
        save_cache(cached_ids.union(new_ids))
        print(f"✅ Guardado: {len(new_ids)} nuevos elementos.")
    else:
        print("🟰 Nada nuevo que descargar.")

if __name__ == "__main__":
    main()