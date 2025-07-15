require('dotenv').config();
const { Pool } = require('pg');

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: { rejectUnauthorized: false }
});

async function resetTable() {
  try {
    await pool.query('TRUNCATE TABLE transcriptions RESTART IDENTITY');
    console.log('🧨 Toutes les données supprimées et ID réinitialisés.');
  } catch (err) {
    console.error('❌ Erreur :', err.message);
  } finally {
    await pool.end();
  }
}

resetTable();
