const fs = require('fs');
const path = require('path');
const { Pool } = require('pg');

// Charger les variables d'environnement uniquement en local
if (process.env.NODE_ENV !== 'production') {
  require('dotenv').config({ override: true });
}

// Utilisation d'un argument pour le nom du fichier JSON
const args = process.argv.slice(2);

// Affichage de l'aide si -h ou --help est présent
if (args.includes('-h') || args.includes('--help')) {
  console.log(`
Usage: node update-batch.cjs [fichier_json]

Options :
  -h, --help      Affiche cette aide

Description :
  Ce script lit un fichier JSON (par défaut transcription_batch.json) contenant des transcriptions
  et les insère dans la base de données PostgreSQL configurée via la variable d'environnement DATABASE_URL.

Exemple :
  node update-batch.cjs mon_fichier.json
  `);
  process.exit(0);
}

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
      console.error(`❌ Erreur d'insertion pour ${name} :`, err.message, '\nDétail SQL :', err);
    }
  }

  await pool.end();
  console.log('📦 Traitement terminé');
}

updateBatch();
