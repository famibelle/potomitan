const { Pool } = require('pg')

// Charger les variables d'environnement uniquement en local
if (process.env.NODE_ENV !== 'production') {
  require('dotenv').config({ override: true });
}

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: { rejectUnauthorized: false }
})

async function createTable() {
  await pool.query(`
    CREATE TABLE IF NOT EXISTS transcriptions (
      id SERIAL PRIMARY KEY,
      filename TEXT NOT NULL,
      transcription TEXT NOT NULL,
      rating SMALLINT     CHECK (rating BETWEEN 0 AND 5)    DEFAULT 0,
      author TEXT DEFAULT 'whisper-large-v3',
      timestamp TIMESTAMPTZ DEFAULT NOW()
    );
  `)
  console.log('✅ Table transcriptions créée')
  process.exit(0)
}

createTable().catch(err => {
  console.error('❌ Erreur :', err)
  process.exit(1)
})
