//Ytmp3 Downloader App

// index.js - Backend en Node.js para descarga de MP3 o video con yt-dlp, con logs y sanitización de nombres

const express = require('express');
const bodyParser = require('body-parser');
const { exec } = require('child_process');
const path = require('path');
const fs = require('fs');

const app = express();
const PORT = 5558;

const DOWNLOAD_PATH = '/volume1/Music/downloads';

app.use(bodyParser.json());
app.use(express.static('public'));

const isPlaylist = url => url.includes('list=');

function sanitizeFolderName(name) {
  return name
    .normalize("NFD").replace(/[̀-ͯ]/g, '') // eliminar tildes
    .replace(/[^\w\s.-]/g, '')                         // quitar símbolos raros
    .replace(/\s+/g, '_')                              // espacios → guiones bajos
    .slice(0, 60) || 'playlist';                        // fallback si queda vacío
}

function getPlaylistTitle(url, callback) {
  exec(`yt-dlp --flat-playlist --print "playlist_title" ${url}`, (err, stdout, stderr) => {
    if (err) {
      console.error('Error obteniendo título de la playlist:', stderr);
      return callback('unknown_playlist');
    }
    return callback(stdout.trim());
  });
}

app.post('/download', (req, res) => {
  const { url, format } = req.body;
  if (!url || !url.startsWith('http')) {
    return res.status(400).send('❌ URL no válida');
  }

  const isAudio = format === 'mp3';
  const ytFlags = isAudio
    ? "-x --audio-format mp3 --audio-quality 0 --prefer-ffmpeg"
    : "--format bestvideo+bestaudio --merge-output-format mp4";

  const outputExt = isAudio ? 'mp3' : 'mp4';

  const runDownload = (targetDir) => {
    const command = `yt-dlp ${ytFlags} -o '${targetDir}/%(title)s.${outputExt}' '${url}'`;
    console.log('Ejecutando:', command);
    exec(command, { maxBuffer: 1024 * 1024 * 10 }, (err, stdout, stderr) => {
      if (err) {
        console.error('Error en la descarga:', stderr);
        return res.status(500).send('❌ Error descargando el contenido.');
      }
      console.log('Descarga completada.');
      return res.send('✅ Descarga completada.');
    });
  };

  if (isPlaylist(url)) {
    getPlaylistTitle(url, rawTitle => {
      const folder = sanitizeFolderName(rawTitle);
      const targetDir = path.join(DOWNLOAD_PATH, folder);
      try {
        fs.mkdirSync(targetDir, { recursive: true });
      } catch (mkdirErr) {
        console.error('Error creando la carpeta de descarga:', mkdirErr);
        return res.status(500).send('❌ Error creando la carpeta destino.');
      }
      runDownload(targetDir);
    });
  } else {
    runDownload(DOWNLOAD_PATH);
  }
});

app.listen(PORT, () => {
  console.log(`yt-dlp downloader running on port ${PORT}`);
});
