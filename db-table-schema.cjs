// print-schema.js
const { Pool } = require('pg')
require('dotenv').config({ override: true })

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: { rejectUnauthorized: false }
})

async function printAllSchemas() {
  try {
    // Récupérer la liste des tables dans le schéma public
    const tablesRes = await pool.query(`
      SELECT table_name
      FROM information_schema.tables
      WHERE table_schema = 'public'
        AND table_type = 'BASE TABLE'
      ORDER BY table_name;
    `)
    const tables = tablesRes.rows.map(r => r.table_name)

    for (const table of tables) {
      const schemaRes = await pool.query(`
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
        WHERE c.table_schema = 'public'
          AND c.table_name = $1
        ORDER BY c.ordinal_position;
      `, [table])

      console.log(`\n📋 Structure de la table "${table}":\n`)
      console.table(schemaRes.rows)
    }

    console.log(`\n✅ ${tables.length} table(s) analysée(s)\n`)
  } catch (err) {
    console.error('❌ Erreur lors de la récupération des schémas :', err)
    process.exit(1)
  } finally {
    await pool.end()
    process.exit(0)
  }
}

printAllSchemas()
