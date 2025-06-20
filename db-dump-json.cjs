const fs = require('fs');
const { Pool } = require('pg');
require('dotenv').config({ override: true });

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: { rejectUnauthorized: false }
});

function getTimestamp() {
  const now = new Date();
  const pad = n => String(n).padStart(2, '0');
  return `${now.getFullYear()}${pad(now.getMonth()+1)}${pad(now.getDate())}_${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;
}

async function dumpTableToJson(tableName) {
  try {
    // Récupère la structure de la table (colonnes + types)
    const structureResult = await pool.query(
      `SELECT column_name, data_type 
       FROM information_schema.columns 
       WHERE table_name = $1
       ORDER BY ordinal_position`,
      [tableName]
    );
    // Récupère les données de la table
    const dataResult = await pool.query(`SELECT * FROM ${tableName}`);
    // Prépare l'objet à écrire
    const dump = {
      structure: structureResult.rows,
      data: dataResult.rows
    };
    // Génère le nom de fichier avec timestamp
    const outputFile = `dump_${tableName}_${getTimestamp()}.json`;
    fs.writeFileSync(outputFile, JSON.stringify(dump, null, 2), 'utf8');
    console.log(`✅ Dump JSON de la table "${tableName}" écrit dans ${outputFile}`);
  } catch (err) {
    console.error('❌ Erreur lors du dump JSON :', err);
    process.exit(1);
  } finally {
    await pool.end();
    process.exit(0);
  }
}

dumpTableToJson('transcriptions');
