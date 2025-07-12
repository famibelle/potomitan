const { Pool } = require('pg');
require('dotenv').config({ override: true });

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: { rejectUnauthorized: false }
});

async function createSchema() {
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

    console.log('✅ Schéma de base de données créé ou mis à jour avec succès.');
  } catch (err) {
    console.error('❌ Erreur lors de la création du schéma :', err);
    process.exit(1);
  } finally {
    await pool.end();
  }
}

createSchema();