const fs = require('fs');
const path = require('path');
const { Pool } = require('pg');
const AdmZip = require('adm-zip');
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

// Tableau des tables à dumper
const tables = [
  'contributeur',
  'fichiers_audio',
  'langue',
  'methode',
  'notifications',
  'statut_transcription',
  'transcription',
  'transcriptions'
];

async function dumpTableToJson(tableName, tempDir) {
  try {
    console.log(`📋 Traitement de la table "${tableName}"...`);
    
    // Récupère la structure de la table (colonnes + types)
    const structureResult = await pool.query(
      `SELECT column_name, data_type 
       FROM information_schema.columns 
       WHERE table_name = $1
       ORDER BY ordinal_position`,
      [tableName]
    );

    // Récupère les contraintes et les colonnes associées
    const constraintsResult = await pool.query(
      `SELECT
         tc.constraint_name,
         tc.constraint_type,
         kcu.column_name
       FROM information_schema.table_constraints tc
       JOIN information_schema.key_column_usage kcu
         ON tc.constraint_name = kcu.constraint_name
         AND tc.table_name = kcu.table_name
       WHERE tc.table_name = $1
       ORDER BY tc.constraint_name, kcu.ordinal_position`,
      [tableName]
    );

    // Récupère les données de la table
    const dataResult = await pool.query(`SELECT * FROM ${tableName}`);

    // Prépare l'objet à écrire
    const dump = {
      structure: structureResult.rows,
      constraints: constraintsResult.rows,
      data: dataResult.rows
    };

    // Chemin du fichier de sortie
    const outputFile = path.join(tempDir, `${tableName}.json`);
    fs.writeFileSync(outputFile, JSON.stringify(dump, null, 2), 'utf8');
    console.log(`✅ Dump JSON de la table "${tableName}" créé`);
    
    return outputFile;
  } catch (err) {
    console.error(`❌ Erreur lors du dump de la table "${tableName}" :`, err);
    return null;
  }
}

async function dumpAllTablesToZip() {
  const timestamp = getTimestamp();
  
  // Créer le répertoire Dumps s'il n'existe pas
  const dumpsDir = path.join(__dirname, 'Dumps');
  if (!fs.existsSync(dumpsDir)) {
    fs.mkdirSync(dumpsDir, { recursive: true });
    console.log(`📁 Répertoire Dumps créé : ${dumpsDir}`);
  }
  
  // Chemin complet pour le fichier ZIP dans le répertoire Dumps
  const zipFileName = path.join(dumpsDir, `database_dump_${timestamp}.zip`);
  const tempDir = path.join(__dirname, `temp_dump_${timestamp}`);
  
  try {
    // Créer un répertoire temporaire
    if (!fs.existsSync(tempDir)) {
      fs.mkdirSync(tempDir, { recursive: true });
    }
    
    console.log(`🔄 Début du dump de la base de données...`);
    console.log(`📂 Le fichier de dump sera enregistré dans : ${zipFileName}`);
    
    // Créer un objet ZIP
    const zip = new AdmZip();
    
    // Dumper chaque table dans un fichier JSON
    for (const table of tables) {
      const jsonFile = await dumpTableToJson(table, tempDir);
      if (jsonFile) {
        // Ajouter le fichier JSON au ZIP
        zip.addLocalFile(jsonFile);
      }
    }
    
    // Ajouter un fichier README avec les informations sur le dump
    const readmeContent = `Database Dump - ${new Date().toISOString()}\n\nContient ${tables.length} tables:\n${tables.join('\n')}`;
    zip.addFile('README.txt', Buffer.from(readmeContent));
    
    // Enregistrer le fichier ZIP
    zip.writeZip(zipFileName);
    
    console.log(`✅ Dump ZIP créé avec succès dans ${zipFileName}`);
    console.log(`📊 ${tables.length} tables dumpées`);
    
    // Nettoyer le répertoire temporaire
    for (const file of fs.readdirSync(tempDir)) {
      fs.unlinkSync(path.join(tempDir, file));
    }
    fs.rmdirSync(tempDir);
    
    console.log(`🧹 Fichiers temporaires nettoyés`);
  } catch (err) {
    console.error('❌ Erreur lors de la création du fichier ZIP :', err);
  } finally {
    await pool.end();
    console.log(`🏁 Opération terminée`);
  }
}

// Exécuter le dump
dumpAllTablesToZip();
