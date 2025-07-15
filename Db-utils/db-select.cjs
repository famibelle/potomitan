const { Pool } = require('pg')

// Charger les variables d'environnement (toujours)
require('dotenv').config({ override: true });

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: { rejectUnauthorized: false }
})

async function printTableContents() {
  try {
    const result = await pool.query(`SELECT * FROM transcriptions;`)
    console.table(result.rows)
    console.log(`✅ ${result.rows.length} ligne(s) récupérée(s)`)
  } catch (err) {
    console.error('❌ Erreur lors de la requête :', err)
    process.exit(1)
  } finally {
    await pool.end()
    process.exit(0)
  }
}

printTableContents()
