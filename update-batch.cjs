const fs = require('fs');
const path = require('path');
const { Pool } = require('pg');

// Charger les variables d'environnement uniquement en local
if (process.env.NODE_ENV !== 'production') {
  require('dotenv').config({ override: true });
}

// Utilisation d'un argument pour le nom du fichier JSON
const args = process.argv.slice(2);
const inputFile = args[0] || 'transcription_batch.json';
const dataFilePath = path.resolve(__dirname, inputFile);

const poolConfig = {
  connectionString: process.env.DATABASE_URL,
};

// Activer SSL si l'URL Render le nécessite (par exemple, contient ".render.com")
if (process.env.DATABASE_URL?.includes('render.com')) {
  poolConfig.ssl = { rejectUnauthorized: false };
}

console.log('📡 Connexion à la base de données :', poolConfig.connectionString);
console.log('🔐 SSL activé ?', !!poolConfig.ssl);

const pool = new Pool(poolConfig);

async function updateBatch() {
  let data;

  try {
    const fileContent = fs.readFileSync(dataFilePath, 'utf-8');
    data = JSON.parse(fileContent);
  } catch (err) {
    console.error('❌ Erreur lors de la lecture ou du parsing du fichier JSON :', err.message);
    return;
  }

  for (const item of data) {
    const { name, transcription, timestamp, author } = item;

    try {
      await pool.query(
        `INSERT INTO transcriptions (filename, transcription, timestamp, author)
        VALUES ($1, $2, $3, $4);`,
        [name, transcription, timestamp, author]
      );

      console.log(`✅ Donnée insérée ou ignorée (doublon) : ${name}`);
    } catch (err) {
      console.error(`❌ Erreur d'insertion pour ${name} :`, err.message);
    }
  }

  await pool.end();
  console.log('📦 Traitement terminé');
}

updateBatch();
