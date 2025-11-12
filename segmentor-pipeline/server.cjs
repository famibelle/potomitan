const { Pool } = require('pg');
const express = require('express');
const fs = require('fs');
const path = require('path');
const cors = require('cors');
const bodyParser = require('body-parser');
// Ajouter l'import de music-metadata
const mm = require('music-metadata');

// Fonction utilitaire pour formater la durée en heures:minutes:secondes
function formatDuration(seconds) {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
  
  return `${hours}h ${minutes}m ${secs}s`;
}

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

// Liste les fichiers audio + leur dernière transcription + labels des dimensions
app.get('/api/audio-files', async (req, res) => {
  try {
    const result = await pool.query(`
      SELECT
        fa.id,
        fa.chemin       AS name,
        fa.titre        AS title,
        fa.artiste      AS artist,
        fa.annee        AS year,
        fa.commentaire,
        fa.lyrics,
        fa.source,
        fa.likes,
        fa.dislikes,
        fa.created_at   AS file_created_at,
        t.id            AS transcription_id,
        t.texte         AS transcription,
        t.rating,
        t.created_at    AS transcription_created_at,
        t.version,
        t.date_creation,
        t.id_contributeur,
        c.nom           AS contributeur_name,
        t.langue_code,
        l.libelle       AS langue,
        t.methode_code,
        m.description   AS methode,
        t.statut_code,
        s.libelle       AS statut
      FROM fichiers_audio fa
      LEFT JOIN LATERAL (
        SELECT * FROM transcription
        WHERE id_fichier_audio = fa.id
        ORDER BY created_at DESC   -- <-- on prend la dernière transcription par date
        LIMIT 1
      ) t ON TRUE
      LEFT JOIN contributeur c
        ON t.id_contributeur = c.id
      LEFT JOIN langue l
        ON t.langue_code = l.code
      LEFT JOIN methode m
        ON t.methode_code = m.code
      LEFT JOIN statut_transcription s
        ON t.statut_code = s.code
      ORDER BY fa.created_at DESC
    `);
    res.json(result.rows);
  } catch (err) {
    console.error('❌ Erreur /api/audio-files :', err);
    res.status(500).json({ error: 'Erreur lors de la récupération des fichiers audio' });
  }
});

// Initialisation de la BDD (création de la table et colonne rating)
app.get('/api/init-db', async (req, res) => {
  try {
    // Lookup tables
    await pool.query(`
      CREATE TABLE IF NOT EXISTS langue (
        code      VARCHAR(5)  PRIMARY KEY,
        libelle   TEXT        NOT NULL
      );
      CREATE TABLE IF NOT EXISTS methode (
        code        VARCHAR(20) PRIMARY KEY,
        description TEXT
      );
      CREATE TABLE IF NOT EXISTS statut_transcription (
        code      VARCHAR(20) PRIMARY KEY,
        libelle   TEXT        NOT NULL
      );
    `);

    // Table FichiersAudio
    await pool.query(`
      CREATE TABLE IF NOT EXISTS fichiers_audio (
        id           SERIAL     PRIMARY KEY,
        chemin       TEXT       NOT NULL UNIQUE,
        titre        TEXT,
        artiste      TEXT,
        annee        SMALLINT,
        commentaire  TEXT,
        lyrics       TEXT,
        source       TEXT,
        created_at   TIMESTAMP  NOT NULL DEFAULT NOW(),
        likes        INTEGER    NOT NULL DEFAULT 0,
        dislikes     INTEGER    NOT NULL DEFAULT 0
      );
    `);

    // Table Contributeur
    await pool.query(`
      CREATE TABLE IF NOT EXISTS contributeur (
        id                SERIAL    PRIMARY KEY,
        nom               TEXT      NOT NULL,
        email             TEXT      UNIQUE,
        role              TEXT,
        date_inscription  TIMESTAMP NOT NULL DEFAULT NOW(),
        actif             BOOLEAN   NOT NULL DEFAULT TRUE
      );
    `);

    // Table Transcription
    await pool.query(`
      CREATE TABLE IF NOT EXISTS transcription (
        id                  SERIAL      PRIMARY KEY,
        id_fichier_audio    INTEGER     NOT NULL
                              REFERENCES fichiers_audio(id)
                              ON DELETE CASCADE,
        id_contributeur     INTEGER
                              REFERENCES contributeur(id),
        texte               TEXT        NOT NULL,
        langue_code         VARCHAR(5)
                              REFERENCES langue(code),
        date_creation       TIMESTAMP   NOT NULL DEFAULT NOW(),
        version             INTEGER     NOT NULL DEFAULT 1,
        statut_code         VARCHAR(20)
                              REFERENCES statut_transcription(code),
        methode_code        VARCHAR(20)
                              REFERENCES methode(code),
        confiance           NUMERIC(3,2),
        created_at          TIMESTAMP   NOT NULL DEFAULT NOW(),
        updated_at          TIMESTAMP,
        rating              INTEGER
      );
      CREATE INDEX IF NOT EXISTS idx_transcription_audio
        ON transcription(id_fichier_audio);
      CREATE INDEX IF NOT EXISTS idx_transcription_langue
        ON transcription(langue_code);
      CREATE INDEX IF NOT EXISTS idx_transcription_statut
        ON transcription(statut_code);
      CREATE INDEX IF NOT EXISTS idx_transcription_methode
        ON transcription(methode_code);
      CREATE INDEX IF NOT EXISTS idx_transcription_date
        ON transcription(created_at);
    `);

    // Table Notifications
    await pool.query(`
      CREATE TABLE IF NOT EXISTS notifications (
        id          SERIAL PRIMARY KEY,
        type        VARCHAR(20),
        file_id     INTEGER,
        file_name   TEXT,
        content     TEXT,
        new_rating  INTEGER,
        timestamp   TIMESTAMP NOT NULL DEFAULT NOW()
      );
    `);

    console.log('✅ Schéma de base de données créé ou mis à jour avec succès.');
  } catch (err) {
    console.error('❌ Erreur lors de la création du schéma :', err);
    process.exit(1);
  } finally {
    res.json({ status: 'ok', message: 'Schéma de base de données créé ou mis à jour.' });
  }
});

// Enregistre une nouvelle transcription
app.post('/api/save-transcription', async (req, res) => {
  const {
    name,
    transcription,
    langue_code,
    methode_code,
    statut_code,
    id_contributeur
  } = req.body;
  if (!name || transcription == null) {
    return res.status(400).send('Champs `name` et `transcription` obligatoires.');
  }

  try {
    // 1) Récupère l'id du fichier audio
    const f = await pool.query(
      'SELECT id FROM fichiers_audio WHERE chemin = $1',
      [name]
    );
    if (f.rowCount === 0) {
      return res.status(404).send('Fichier audio introuvable');
    }
    const fileId = f.rows[0].id;

    // 2) Calcule la prochaine version
    const v = await pool.query(
      'SELECT MAX(version) AS maxv FROM transcription WHERE id_fichier_audio = $1',
      [fileId]
    );
    const nextVersion = (v.rows[0].maxv || 0) + 1;

    // 3) Insère la nouvelle transcription
    const insert = await pool.query(
      `INSERT INTO transcription
         (id_fichier_audio, id_contributeur, texte, langue_code, methode_code, statut_code, version, date_creation, created_at)
       VALUES ($1,$2,$3,$4,$5,$6,$7,NOW(),NOW())
       RETURNING id, texte AS transcription, created_at AS timestamp, version`,
      [
        fileId,
        id_contributeur,
        transcription,
        langue_code,
        methode_code,
        statut_code,
        nextVersion
      ]
    );

    // 4) Renvoie l’enregistrement créé
    res.json({ status: 'ok', entry: insert.rows[0] });

  } catch (err) {
    console.error('❌ Erreur /api/save-transcription:', err);
    res.status(500).json({ error: 'Erreur lors de la sauvegarde de la transcription' });
  }
});

// Met à jour la note d’une transcription
app.post('/api/save-rating/:id', async (req, res) => {
  const id = parseInt(req.params.id, 10);
  const { rating } = req.body;
  if (isNaN(id) || rating == null) {
    return res.status(400).send('ID ou rating invalide.');
  }

  try {
    const result = await pool.query(
      `UPDATE transcription
         SET rating     = $1,
             updated_at = NOW()
       WHERE id = $2
       RETURNING *`,
      [rating, id]
    );
    if (result.rowCount === 0) {
      return res.status(404).json({ error: 'Transcription introuvable.' });
    }
    res.json({ status: 'ok', transcription: result.rows[0] });
  } catch (err) {
    console.error('❌ Erreur /api/save-rating:', err);
    res.status(500).json({ error: 'Erreur lors de la mise à jour de la note' });
  }
});

// Like / Dislike sur le fichier audio
app.post('/api/like', async (req, res) => {
  const { fileId } = req.body;
  try {
    const result = await pool.query(
      'UPDATE fichiers_audio SET likes = likes + 1 WHERE id = $1 RETURNING *',
      [fileId]
    );
    res.json({ success: true, file: result.rows[0] });
  } catch (err) {
    console.error('❌ Erreur /api/like:', err);
    res.status(500).json({ success: false, error: err.message });
  }
});

app.post('/api/dislike', async (req, res) => {
  const { fileId } = req.body;
  try {
    const result = await pool.query(
      'UPDATE fichiers_audio SET dislikes = dislikes + 1 WHERE id = $1 RETURNING *',
      [fileId]
    );
    res.json({ success: true, file: result.rows[0] });
  } catch (err) {
    console.error('❌ Erreur /api/dislike:', err);
    res.status(500).json({ success: false, error: err.message });
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

// Liste des langues, méthodes, statuts et contributeurs (dimensions)
app.get('/api/dim-languages', async (_, res) => {
  const { rows } = await pool.query('SELECT code, libelle FROM langue');
  res.json(rows);
});
app.get('/api/dim-methods', async (_, res) => {
  const { rows } = await pool.query('SELECT code, description FROM methode');
  res.json(rows);
});
app.get('/api/dim-statuses', async (_, res) => {
  const { rows } = await pool.query('SELECT code, libelle FROM statut_transcription');
  res.json(rows);
});
app.get('/api/contributors', async (_, res) => {
  const { rows } = await pool.query('SELECT id, nom FROM contributeur');
  res.json(rows);
});

// Sert d’abord les fichiers statiques audio
app.use('/audio', express.static(AUDIO_DIR));

// Sert ensuite le build Vue
app.use(express.static(path.join(__dirname, 'dist')));
app.get(/.*/, (req, res) => {
  res.sendFile(path.join(__dirname, 'dist', 'index.html'));
});

/**
 * Synchronise la table `fichiers_audio` avec le contenu du dossier public/audio :
 * 1) Insert tous les fichiers présents sur le disque et non en base.
 * 2) Supprime les enregistrements en base dont le fichier n’existe plus.
 */
app.post('/api/sync-audio-files', async (req, res) => {
  try {
    const log = (...args) => {
      console.log(...args);
      if (res && !res.headersSent) {
        res.write(typeof args[0] === 'string' ? args.join(' ') + '\n' : JSON.stringify(args) + '\n');
      }
    };

    log('🔄 Démarrage de la synchronisation des fichiers audio...');
    // Lecture du dossier
    const diskFiles = fs.readdirSync(AUDIO_DIR)
      .filter(f => /\.(mp3|wav)$/i.test(f));
    
    // Calculer la durée totale
    let totalDuration = 0;
    for (const file of diskFiles) {
      try {
        const filePath = path.join(AUDIO_DIR, file);
        const metadata = await mm.parseFile(filePath);
        totalDuration += metadata.format.duration || 0;
      } catch (err) {
        log(`⚠️ Erreur lors de l'extraction de la durée pour ${file}: ${err.message}`);
      }
    }
    
    // Formater la durée pour l'affichage
    const formattedDuration = formatDuration(totalDuration);
    log(`📂 Fichiers trouvés sur le disque : ${diskFiles.length} (durée totale: ${formattedDuration})`);

    // 1) Upsert des fichiers existants sur le disque
    let upserted = 0;
    for (const name of diskFiles) {
      const result = await pool.query(
        `INSERT INTO fichiers_audio (chemin)
           VALUES ($1)
           ON CONFLICT (chemin) DO NOTHING
           RETURNING id`,
        [name]
      );
      if (result.rowCount > 0) {
        upserted++;
        log(`➕ Ajouté en base : ${name}`);
      }
    }
    log(`✅ Fichiers ajoutés (nouveaux) : ${upserted}`);

    // 2) Suppression des enregistrements obsolètes
    const dbFilesRes = await pool.query(`SELECT chemin FROM fichiers_audio`);
    const dbFiles = dbFilesRes.rows.map(r => r.chemin);
    const toDelete = dbFiles.filter(chemin => !diskFiles.includes(chemin));
    if (toDelete.length) {
      await pool.query(
        `DELETE FROM fichiers_audio WHERE chemin = ANY($1::text[])`,
        [toDelete]
      );
      log(`🗑️ Fichiers supprimés de la base (absents du disque) : ${toDelete.length}`);
      toDelete.forEach(f => log(`   - ${f}`));
    } else {
      log('🗑️ Aucun fichier à supprimer de la base.');
    }

    // 3) S’assurer qu’il y ait au moins une ligne dans transcription par fichier
    const missingRes = await pool.query(`
      SELECT id FROM fichiers_audio fa
      WHERE NOT EXISTS (
        SELECT 1 FROM transcription t
        WHERE t.id_fichier_audio = fa.id
      )
    `);
    let addedTrans = 0;
    for (const { id } of missingRes.rows) {
      await pool.query(
        `INSERT INTO transcription (id_fichier_audio, texte, date_creation)
         VALUES ($1, '', NOW())`,
        [id]
      );
      addedTrans++;
      log(`📝 Transcription vide ajoutée pour fichier id=${id}`);
    }
    if (addedTrans === 0) {
      log('📝 Toutes les transcriptions sont déjà présentes.');
    }

    log('✅ Synchronisation terminée.');
    if (!res.headersSent) {
      res.end(JSON.stringify({
        status: 'ok',
        synced: diskFiles.length,
        totalDuration: totalDuration,
        formattedDuration: formattedDuration,
        removed: toDelete.length,
        addedEmptyTranscriptions: missingRes.rows.length
      }));
    }
  } catch (err) {
    console.error('❌ Erreur /api/sync-audio-files :', err);
    if (!res.headersSent) {
      res.status(500).json({ error: err.message });
    }
  }
});

// Retourne l'historique des transcriptions pour un fichier audio donné
app.get('/api/transcription-history/:fileId', async (req, res) => {
  const fileId = parseInt(req.params.fileId, 10);
  if (isNaN(fileId)) {
    return res.status(400).json({ error: 'ID de fichier invalide' });
  }
  try {
    const result = await pool.query(
      `SELECT
         texte            AS transcription,
         created_at       AS timestamp,
         version
       FROM transcription
       WHERE id_fichier_audio = $1
       ORDER BY created_at ASC`,
      [fileId]
    );
    res.json(result.rows);
  } catch (err) {
    console.error('❌ Erreur /api/transcription-history:', err);
    res.status(500).json({ error: 'Erreur lors de la lecture de l’historique' });
  }
});

app.listen(PORT, () => console.log(`✅ Serveur Express lancé sur http://localhost:${PORT}`));
