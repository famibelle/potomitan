// clean-table.cjs
// Script pour supprimer les doublons de texte dans la table transcriptions (PostgreSQL)
// Ne garde qu'un seul exemplaire de chaque transcription (le plus ancien)

if (process.env.NODE_ENV !== 'production') {
  require('dotenv').config({ override: true });
}
const { Pool } = require('pg');

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: { rejectUnauthorized: false }
});

async function cleanTable() {
  try {
    // Supprimer les doublons de texte (garder le plus ancien id pour chaque transcription)
    const deleteSQL = `
      DELETE FROM transcriptions t1
      USING transcriptions t2
      WHERE t1.transcription = t2.transcription
        AND t1.id > t2.id;
    `;
    await pool.query(deleteSQL);
    console.log('✅ Doublons supprimés, chaque texte de transcription est maintenant unique.');
  } catch (err) {
    console.error('❌ Erreur lors du nettoyage :', err.message);
  } finally {
    await pool.end();
  }
}

cleanTable();
