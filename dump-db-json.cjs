const fs = require('fs');
const { Pool } = require('pg');
require('dotenv').config({ override: true });

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: { rejectUnauthorized: false }
});

async function dumpTableToJson(tableName, outputFile) {
  try {
    const result = await pool.query(`SELECT * FROM ${tableName}`);
    fs.writeFileSync(outputFile, JSON.stringify(result.rows, null, 2), 'utf8');
    console.log(`✅ Dump JSON de la table "${tableName}" écrit dans ${outputFile}`);
  } catch (err) {
    console.error('❌ Erreur lors du dump JSON :', err);
    process.exit(1);
  } finally {
    await pool.end();
    process.exit(0);
  }
}

dumpTableToJson('transcriptions', 'dump.json');