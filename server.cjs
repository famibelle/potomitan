const { Pool } = require('pg');

// Charger les variables d'environnement uniquement en local
if (process.env.NODE_ENV !== 'production') {
  require('dotenv').config();
}

const poolConfig = {
  connectionString: process.env.DATABASE_URL,
};

// Ajoutez la configuration SSL uniquement pour l'environnement distant
if (process.env.NODE_ENV === 'production') {
  poolConfig.ssl = { rejectUnauthorized: false };
}

const pool = new Pool(poolConfig);

const express = require('express');
const fs = require('fs');
const path = require('path');
const cors = require('cors');
const bodyParser = require('body-parser');

const app = express();
const PORT = process.env.PORT || 3001;

//const AUDIO_DIR = path.join(__dirname, 'public', 'audio');
const AUDIO_DIR = path.join(__dirname, 'dist', 'audio')

app.use(cors());
app.use(bodyParser.json());

// Liste les fichiers audio + transcription (avec historique complet)
app.get('/api/audio-files', async (req, res) => {
  try {
    // 1) Lire TOUS les fichiers .wav/.mp3 du dossier
    const diskFiles = fs
      .readdirSync(AUDIO_DIR)
      .filter((f) => f.endsWith('.wav') || f.endsWith('.mp3'));

    // 2) Récupérer TOUT l’historique depuis la BDD
    const result = await pool.query(
      `SELECT id, filename, transcription, timestamp, rating
       FROM transcriptions
       ORDER BY timestamp ASC`
    );

    // 3) Regrouper ces entrées par fichier
    const historyMap = {};
    result.rows.forEach(({ id, filename, transcription, timestamp, rating }) => {
      if (!historyMap[filename]) historyMap[filename] = [];
      historyMap[filename].push({ id, transcription, timestamp, rating });
    });

    // 4) Construire le JSON final : un objet par fichier, même sans historique
    const files = diskFiles.map((filename, idx) => {
      const history = historyMap[filename] || [];
      const latest = history[history.length - 1] || {};
      return {
        id: latest.id || idx + 1,
        name: filename,
        //url: `/audio/${filename}`,
        src: `/audio/${filename}`,
        transcription: latest.transcription || '',
        rating: latest.rating || 0,
        history,
      };
    });

    res.json(files);
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Erreur de récupération des fichiers' });
  }
});

// Initialisation de la BDD (création de la table et colonne rating)
app.get('/api/init-db', async (req, res) => {
  try {
    await pool.query(`
      CREATE TABLE IF NOT EXISTS transcriptions (
        id SERIAL PRIMARY KEY,
        filename TEXT NOT NULL,
        transcription TEXT NOT NULL,
        rating SMALLINT DEFAULT 0 CHECK (rating BETWEEN 0 AND 5),
        timestamp TIMESTAMPTZ DEFAULT NOW()
      )
    `);
    res.send('✅ Table transcriptions initialisée avec succès.');
  } catch (err) {
    console.error(err);
    res.status(500).send("❌ Erreur lors de l'initialisation de la table.");
  }
});

// Enregistre une nouvelle transcription (historique)
app.post('/api/save-transcription', async (req, res) => {
  const { name, transcription } = req.body;
  if (!name || transcription == null) return res.status(400).send('Champs requis.');

  try {
    await pool.query(
      `INSERT INTO transcriptions (filename, transcription) VALUES ($1, $2)`,
      [name, transcription]
    );
    res.json({ status: 'ok' });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Erreur lors de l\'enregistrement' });
  }
});

// Enregistre uniquement la note liée à une transcription existante
app.post('/api/save-rating/:id', async (req, res) => {
  const id = parseInt(req.params.id, 10);
  const { rating } = req.body;
  if (isNaN(id) || rating == null) {
    return res.status(400).send('ID ou rating invalide.');
  }

  try {
    await pool.query(
      `UPDATE transcriptions
         SET rating = $1,
             timestamp = NOW()
       WHERE id = $2`,
      [rating, id]
    );
    res.json({ status: 'ok' });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Erreur lors de l\'enregistrement de la note' });
  }
});

// Sert d’abord les fichiers statiques audio
app.use('/audio', express.static(AUDIO_DIR));

// Sert ensuite le build Vue
app.use(express.static(path.join(__dirname, 'dist')));
app.get(/.*/, (req, res) => {
  res.sendFile(path.join(__dirname, 'dist', 'index.html'));
});

app.listen(PORT, () => console.log(`✅ Serveur Express lancé sur http://localhost:${PORT}`));
