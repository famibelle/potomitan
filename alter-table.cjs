// alter-table.cjs
require('dotenv').config();
const { Pool } = require('pg');

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: { rejectUnauthorized: false }
});

async function alterTable() {
  try {
    const sql = `ALTER TABLE transcriptions   ADD COLUMN rating SMALLINT     CHECK (rating BETWEEN 0 AND 5)    DEFAULT 0;`
    //const sql = `ALTER TABLE transcriptions ADD COLUMN author TEXT DEFAULT 'whisper-large-v3';`;
    await pool.query(sql);
    console.log('✅ Colonne ajoutée avec succès.');
  } catch (err) {
    console.error('❌ Erreur :', err.message);
  } finally {
    await pool.end();
  }
}

alterTable();
