// reset-likes.cjs
// Script Node.js pour remettre à zéro les compteurs de likes et dislikes dans la table audio_files

require('dotenv').config();
const { Pool } = require('pg');

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: { rejectUnauthorized: false }
});

async function resetTable() {
  try {
    await pool.query('UPDATE transcriptions SET likes = 0, dislikes = 0');
    console.log('Likes et dislikes remis à zéro pour toutes les entrées lignes modifiées).');
  } catch (err) {
    console.error('❌ Erreur :', err.message);
  } finally {
    await pool.end();
  }
}

resetTable();