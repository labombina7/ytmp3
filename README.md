# 🎵 YT-MP3 Downloader

Este proyecto permite descargar canciones, álbumes o listas de reproducción desde YouTube o YouTube Music y convertirlas automáticamente a MP3, con metadatos embebidos (artista, álbum, carátula, número de pista, etc.).

✅ Funciona con playlists, vídeos sueltos y álbumes completos  
🧠 Detecta colaboraciones y evita duplicados de álbum  
📂 Organiza las descargas por carpeta `Artista - Álbum`  
🎶 Compatible con Apple Music, iPod y cualquier reproductor  

---

## 🚀 Cómo funciona

- Interfaz web minimalista en Flask
- Backend en Python con cola de descargas por `yt-dlp`
- SSE (Server-Sent Events) para mostrar estado en tiempo real
- Soporte para orden de pistas en álbumes

---

## 🧰 Requisitos

- Docker
- ffmpeg (instalado dentro del contenedor)
- Python 3.11 (usado en la imagen)

---

## 🔧 Uso local

```bash
git clone https://github.com/tu-usuario/ytmp3-downloader.git
cd ytmp3-downloader
docker-compose build
docker-compose up -d
