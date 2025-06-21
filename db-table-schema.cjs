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
        c.column_name,
        c.data_type,
        c.is_nullable,
        c.column_default,
        tc.constraint_type
      FROM information_schema.columns c
      LEFT JOIN information_schema.key_column_usage kcu
        ON c.table_name = kcu.table_name
        AND c.column_name = kcu.column_name
        AND c.table_schema = kcu.table_schema
      LEFT JOIN information_schema.table_constraints tc
        ON kcu.constraint_name = tc.constraint_name
        AND kcu.table_schema = tc.table_schema
      WHERE c.table_name = 'transcriptions'
      ORDER BY c.ordinal_position;
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
