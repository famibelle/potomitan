const { Pool } = require('pg');
const express = require('express');
const fs = require('fs');
const path = require('path');
const cors = require('cors');
const bodyParser = require('body-parser');

// Charger les variables d'environnement uniquement en local
if (process.env.NODE_ENV !== 'production') {
  require('dotenv').config();
}

const poolConfig = {
  connectionString: process.env.DATABASE_URL,
};

// Toujours activer SSL pour Render/Postgres
poolConfig.ssl = { rejectUnauthorized: false };

const pool = new Pool(poolConfig);
const app = express();
const PORT = process.env.PORT || 3001;

const AUDIO_DIR = path.join(__dirname, 'public', 'audio');
const NOTIF_STATE_PATH = path.join(__dirname, 'notifications-state.json');

app.use(cors());
app.use(bodyParser.json({ limit: '5mb' }));

// Liste les fichiers audio + transcription (avec historique complet)
app.get('/api/audio-files', async (req, res) => {
  try {
    // On récupère les fichiers audio et, pour chacun, sa dernière transcription (version max)
    const result = await pool.query(`
      SELECT
        fa.id,
        fa.chemin    AS name,
        fa.titre     AS title,
        fa.artiste   AS artist,
        fa.annee     AS year,
        fa.commentaire,
        fa.lyrics,
        fa.source,
        fa.likes,
        fa.dislikes,
        fa.created_at AS file_created_at,
        t.texte      AS transcription,
        t.langue_code,
        t.methode_code,
        t.statut_code,
        t.id_contributeur,
        t.rating     AS rating,
        t.created_at AS transcription_created_at
      FROM fichiers_audio fa
      LEFT JOIN LATERAL (
        SELECT *
        FROM transcription
        WHERE id_fichier_audio = fa.id
        ORDER BY version DESC
        LIMIT 1
      ) t ON TRUE
      ORDER BY fa.created_at DESC
    `)
    res.json(result.rows)
  } catch (err) {
    console.error('❌ Erreur /api/audio-files:', err)
    res.status(500).json({ error: 'Erreur lors de la récupération des fichiers audio' })
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
      `INSERT INTO transcriptions (filename, transcription)
       VALUES ($1, $2)
       ON CONFLICT (filename, transcription) DO NOTHING`,
      [name, transcription]
    );
    res.json({ status: 'ok' });
  } catch (err) {
    console.error(err);
    if (err.code === '23505') { // violation contrainte UNIQUE
      return res.status(409).json({ error: 'Cette transcription a déjà été proposée' });
    }
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

app.post('/api/like', async (req, res) => {
  const { fileId } = req.body;
  try {
    const result = await pool.query(
      'UPDATE transcriptions SET likes = likes + 1 WHERE id = $1 RETURNING *',
      [fileId]
    );
    res.json({ success: true, data: result.rows[0] });
  } catch (error) {
    console.error('Error:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

app.post('/api/dislike', async (req, res) => {
  const { fileId } = req.body;
  try {
    const result = await pool.query(
      'UPDATE transcriptions SET dislikes = dislikes + 1 WHERE id = $1 RETURNING *',
      [fileId]
    );
    res.json({ success: true, data: result.rows[0] });
  } catch (error) {
    console.error('Error:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

// --- Notifications state (PostgreSQL storage) ---

// Récupérer les notifications (antichronologique)
app.get('/api/notifications-state', async (req, res) => {
  try {
    const result = await pool.query(
      `SELECT id, type, file_id AS "fileId", file_name AS "fileName", content, new_rating AS "newRating", timestamp
       FROM notifications
       ORDER BY timestamp DESC
       LIMIT 100`
    );
    res.json(result.rows);
  } catch (err) {
    console.error('Erreur lecture notifications (DB):', err);
    res.status(500).json({ error: 'Erreur lecture notifications (DB)' });
  }
});

// Ajouter une notification (ou vider la table si tableau vide)
app.post('/api/notifications-state', async (req, res) => {
  try {
    const notifs = req.body;
    if (Array.isArray(notifs) && notifs.length === 0) {
      // Vider la table
      await pool.query('DELETE FROM notifications');
      return res.json({ status: 'cleared' });
    }
    // Ajout d'une ou plusieurs notifications
    if (Array.isArray(notifs)) {
      // On ne garde que la dernière notification reçue (logique front)
      const notif = notifs[notifs.length - 1];
      await pool.query(
        `INSERT INTO notifications (type, file_id, file_name, content, new_rating, timestamp)
         VALUES ($1, $2, $3, $4, $5, $6)`,
        [notif.type, notif.fileId, notif.fileName, notif.content || null, notif.newRating || null, notif.timestamp || new Date()]
      );
      return res.json({ status: 'added' });
    }
    res.status(400).json({ error: 'Format de notification invalide' });
  } catch (err) {
    console.error('Erreur écriture notifications (DB):', err);
    res.status(500).json({ error: 'Erreur écriture notifications (DB)' });
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
