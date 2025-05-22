const { Pool } = require('pg')

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
