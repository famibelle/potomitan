const fs = require('fs');
const path = require('path');
const { Pool } = require('pg');
const archiver = require('archiver'); // Nécessite npm install archiver
require('dotenv').config({ override: true });

// Liste des tables à dumper
const tablesToDump = [
  'contributeur',
  'fichiers_audio',
  'langue',
  'methode',
  'notifications',
  'statut_transcription',
  'transcription',
  'transcriptions'
];

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: { rejectUnauthorized: false }
});

function getTimestamp() {
  const now = new Date();
  const pad = n => String(n).padStart(2, '0');
  return `${now.getFullYear()}${pad(now.getMonth()+1)}${pad(now.getDate())}_${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;
}

// Créer le dossier principal "Dumps" s'il n'existe pas
const mainDumpDir = 'Dumps';
if (!fs.existsSync(mainDumpDir)) {
  fs.mkdirSync(mainDumpDir);
  console.log(`📁 Dossier principal "${mainDumpDir}" créé`);
}

// Créer un sous-dossier horodaté à l'intérieur de "Dumps"
const timestamp = getTimestamp();
const dumpDir = path.join(mainDumpDir, `dump_${timestamp}`);
if (!fs.existsSync(dumpDir)) {
  fs.mkdirSync(dumpDir);
}

async function dumpTableToJson(tableName) {
  try {
    console.log(`🔄 Dumping table "${tableName}"...`);
    
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
      data: dataResult.rows,
      rowCount: dataResult.rows.length
    };

    // Génère le nom de fichier dans le dossier de dump
    const outputFile = path.join(dumpDir, `${tableName}.json`);
    fs.writeFileSync(outputFile, JSON.stringify(dump, null, 2), 'utf8');
    console.log(`✅ Dump JSON de la table "${tableName}" écrit dans ${outputFile} (${dataResult.rows.length} lignes)`);
    return { table: tableName, success: true, rowCount: dataResult.rows.length };
  } catch (err) {
    console.error(`❌ Erreur lors du dump JSON pour "${tableName}" :`, err.message);
    return { table: tableName, success: false, error: err.message };
  }
}

// Fonction pour créer un fichier ZIP avec tous les dumps
function createZipArchive() {
  return new Promise((resolve, reject) => {
    const zipFilePath = path.join(mainDumpDir, `dump_${timestamp}.zip`);
    const output = fs.createWriteStream(zipFilePath);
    const archive = archiver('zip', { zlib: { level: 9 } });  // Niveau de compression maximum

    output.on('close', () => {
      console.log(`📦 Archive ZIP créée avec succès: ${zipFilePath} (${archive.pointer()} octets)`);
      resolve(zipFilePath);
    });
    
    archive.on('error', (err) => {
      reject(err);
    });

    archive.pipe(output);
    
    // Ajouter le dossier entier au ZIP
    archive.directory(dumpDir, false);
    
    archive.finalize();
  });
}

// Fonction pour supprimer le dossier temporaire après la création du ZIP
function removeTempFolder() {
  try {
    const files = fs.readdirSync(dumpDir);
    for (const file of files) {
      fs.unlinkSync(path.join(dumpDir, file));
    }
    fs.rmdirSync(dumpDir);
    console.log(`🧹 Dossier temporaire supprimé: ${dumpDir}`);
  } catch (err) {
    console.error(`❌ Erreur lors de la suppression du dossier temporaire: ${err.message}`);
  }
}

async function dumpAllTables() {
  console.log(`🚀 Démarrage du dump de ${tablesToDump.length} tables...`);
  console.log(`📁 Les fichiers seront stockés temporairement dans: ${dumpDir}`);
  
  try {
    const results = [];
    
    // Dump chaque table spécifiée
    for (const tableName of tablesToDump) {
      const result = await dumpTableToJson(tableName);
      results.push(result);
    }
    
    // Crée un fichier de résumé
    const summary = {
      timestamp: new Date().toISOString(),
      totalTables: tablesToDump.length,
      successCount: results.filter(r => r.success).length,
      failureCount: results.filter(r => !r.success).length,
      details: results
    };
    
    fs.writeFileSync(
      path.join(dumpDir, '_summary.json'), 
      JSON.stringify(summary, null, 2), 
      'utf8'
    );
    
    console.log(`\n📊 Résumé du dump :`);
    console.log(`   - Tables traitées : ${tablesToDump.length}`);
    console.log(`   - Succès : ${results.filter(r => r.success).length}`);
    console.log(`   - Échecs : ${results.filter(r => !r.success).length}`);
    
    // Crée le fichier ZIP avec tous les dumps
    const zipPath = await createZipArchive();
    
    // Supprimer le dossier temporaire après la création du ZIP
    removeTempFolder();
    
    console.log(`\n✅ Opération terminée! Vous pouvez trouver le dump complet ici: ${zipPath}`);
    
  } catch (err) {
    console.error('❌ Erreur générale lors du dump :', err);
  } finally {
    await pool.end();
    console.log('👋 Connexion à la base fermée, fin du processus');
  }
}

// Exécute le dump de toutes les tables
dumpAllTables();
