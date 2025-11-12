require('dotenv').config();
const { Pool } = require('pg');

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: { rejectUnauthorized: false }
});

async function cleanNullTimestamps() {
  try {
    const res = await pool.query('DELETE FROM transcriptions WHERE timestamp IS NULL');
    console.log(`🧹 ${res.rowCount} entrées supprimées avec timestamp NULL.`);
  } catch (err) {
    console.error('❌ Erreur :', err.message);
  } finally {
    await pool.end();
  }
}

cleanNullTimestamps();
