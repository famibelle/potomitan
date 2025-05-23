// print-schema.js
const { Pool } = require('pg')

// Toujours charger .env en local
require('dotenv').config({ override: true });

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: { rejectUnauthorized: false }
})

async function printTableSchema() {
  try {
    const result = await pool.query(`
      SELECT
        column_name,
        data_type,
        is_nullable,
        column_default
      FROM information_schema.columns
      WHERE table_name = 'transcriptions'
      ORDER BY ordinal_position;
    `)

    console.log('\n📋 Structure de la table "transcriptions":\n')
    console.table(result.rows)
    console.log(`\n✅ ${result.rows.length} colonne(s) trouvée(s)\n`)
  } catch (err) {
    console.error('❌ Erreur lors de la récupération du schéma :', err)
    process.exit(1)
  } finally {
    await pool.end()
    process.exit(0)
  }
}

printTableSchema()
