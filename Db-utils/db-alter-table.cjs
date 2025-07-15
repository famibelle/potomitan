// alter-table.cjs
// Charger les variables d'environnement uniquement en local
if (process.env.NODE_ENV !== 'production') {
  require('dotenv').config({ override: true });
}
const { Pool } = require('pg');

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: { rejectUnauthorized: false }
});

async function alterTable() {
  try {
    //const sql = `ALTER TABLE transcriptions   ADD COLUMN rating SMALLINT     CHECK (rating BETWEEN 0 AND 5)    DEFAULT 0;`
    //const sql = `ALTER TABLE transcriptions ADD COLUMN author TEXT DEFAULT 'whisper-large-v3';`;
    //Ajout de colonnes pour les likes et les dislikes
    //const sql = `ALTER TABLE transcriptions ADD COLUMN likes INTEGER DEFAULT 0, ADD COLUMN dislikes INTEGER DEFAULT 0;`
    //await pool.query(sql);
    //console.log('✅ Colonnes likes et dislikes ajoutées avec succès.');

    // Ajout contrainte UNIQUE sur le champ transcription
    // const sqlUnique = `ALTER TABLE transcriptions ADD CONSTRAINT unique_transcription UNIQUE (transcription);`;
    // const sqlUnique = `ALTER TABLE transcriptions ADD CONSTRAINT unique_filename UNIQUE (filename);`;
    // const sqlUnique = `ALTER TABLE transcriptions ADD COLUMN created_at TIMESTAMP DEFAULT NOW();`;
    // const sqlUnique = `ALTER TABLE transcriptions DROP CONSTRAINT IF EXISTS unique_filename, DROP CONSTRAINT IF EXISTS unique_trancription;`;
    const sqlUnique = `ALTER TABLE contributeur
    ADD CONSTRAINT uq_contributeur_nom UNIQUE(nom);`;
    
    await pool.query(sqlUnique);
    console.log('✅ Contrainte UNIQUE ajoutée sur le champ transcription.');
  } catch (err) {
    console.error('❌ Erreur :', err.message);
  } finally {
    await pool.end();
  }
}

alterTable();
