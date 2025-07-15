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
const jsonDir = path.join(dumpDir, 'json');
const sqlDir = path.join(dumpDir, 'sql');

if (!fs.existsSync(dumpDir)) {
  fs.mkdirSync(dumpDir);
}
if (!fs.existsSync(jsonDir)) {
  fs.mkdirSync(jsonDir);
}
if (!fs.existsSync(sqlDir)) {
  fs.mkdirSync(sqlDir);
}

// Fonction pour générer les instructions SQL CREATE TABLE
function generateCreateTableSQL(tableName, structure, constraints) {
  let sql = `-- Table: public.${tableName}\n\n`;
  
  sql += `DROP TABLE IF EXISTS public.${tableName};\n\n`;
  
  sql += `CREATE TABLE public.${tableName} (\n`;
  
  // Colonnes
  const columns = structure.map(col => {
    return `    "${col.column_name}" ${col.data_type}`;
  });
  
  // Contraintes primaires
  const primaryKeys = constraints
    .filter(con => con.constraint_type === 'PRIMARY KEY')
    .map(con => con.column_name);
  
  if (primaryKeys.length > 0) {
    columns.push(`    PRIMARY KEY (${primaryKeys.map(pk => `"${pk}"`).join(', ')})`);
  }
  
  sql += columns.join(',\n');
  sql += '\n);\n\n';
  
  return sql;
}

// Fonction pour générer les instructions SQL INSERT
function generateInsertSQL(tableName, data) {
  if (data.length === 0) return '';
  
  let sql = `-- Data for table: ${tableName}\n\n`;
  
  // Obtenir les noms des colonnes du premier objet
  const columns = Object.keys(data[0]);
  
  for (const row of data) {
    const values = columns.map(col => {
      const val = row[col];
      if (val === null) return 'NULL';
      if (typeof val === 'string') return `'${val.replace(/'/g, "''")}'`;
      if (val instanceof Date) return `'${val.toISOString()}'`;
      return val;
    });
    
    sql += `INSERT INTO public.${tableName} (${columns.map(c => `"${c}"`).join(', ')}) VALUES (${values.join(', ')});\n`;
  }
  
  sql += '\n';
  return sql;
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

    // Prépare l'objet à écrire pour JSON
    const dump = {
      structure: structureResult.rows,
      constraints: constraintsResult.rows,
      data: dataResult.rows,
      rowCount: dataResult.rows.length
    };

    // Génère le fichier JSON
    const jsonOutputFile = path.join(jsonDir, `${tableName}.json`);
    fs.writeFileSync(jsonOutputFile, JSON.stringify(dump, null, 2), 'utf8');
    console.log(`✅ Dump JSON de la table "${tableName}" écrit dans ${jsonOutputFile} (${dataResult.rows.length} lignes)`);
    
    // Génère le fichier SQL
    const createTableSQL = generateCreateTableSQL(tableName, structureResult.rows, constraintsResult.rows);
    const insertSQL = generateInsertSQL(tableName, dataResult.rows);
    const sqlOutputFile = path.join(sqlDir, `${tableName}.sql`);
    fs.writeFileSync(sqlOutputFile, createTableSQL + insertSQL, 'utf8');
    console.log(`✅ Dump SQL de la table "${tableName}" écrit dans ${sqlOutputFile}`);
    
    return { 
      table: tableName, 
      success: true, 
      rowCount: dataResult.rows.length,
      structure: structureResult.rows,
      constraints: constraintsResult.rows,
      data: dataResult.rows
    };
  } catch (err) {
    console.error(`❌ Erreur lors du dump pour "${tableName}" :`, err.message);
    return { table: tableName, success: false, error: err.message };
  }
}

// Générer un fichier SQL complet avec toutes les tables
async function generateCompleteSQLDump(results) {
  try {
    let completeSql = `-- Dump complet PostgreSQL généré le ${new Date().toISOString()}\n\n`;
    
    // Ajouter toutes les instructions CREATE TABLE d'abord
    completeSql += `-- ==========================================\n`;
    completeSql += `-- STRUCTURE DES TABLES\n`;
    completeSql += `-- ==========================================\n\n`;
    
    for (const result of results.filter(r => r.success)) {
      const createTableSQL = generateCreateTableSQL(
        result.table, 
        result.structure, 
        result.constraints
      );
      completeSql += createTableSQL;
    }
    
    // Puis ajouter toutes les données
    completeSql += `-- ==========================================\n`;
    completeSql += `-- DONNÉES DES TABLES\n`;
    completeSql += `-- ==========================================\n\n`;
    
    for (const result of results.filter(r => r.success)) {
      const insertSQL = generateInsertSQL(result.table, result.data);
      completeSql += insertSQL;
    }
    
    const completeOutputFile = path.join(sqlDir, `_complete_dump.sql`);
    fs.writeFileSync(completeOutputFile, completeSql, 'utf8');
    console.log(`✅ Dump SQL complet écrit dans ${completeOutputFile}`);
  } catch (err) {
    console.error(`❌ Erreur lors de la génération du dump SQL complet:`, err.message);
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
    function deleteDir(dir) {
      if (fs.existsSync(dir)) {
        fs.readdirSync(dir).forEach((file) => {
          const curPath = path.join(dir, file);
          if (fs.lstatSync(curPath).isDirectory()) {
            deleteDir(curPath);
          } else {
            fs.unlinkSync(curPath);
          }
        });
        fs.rmdirSync(dir);
      }
    }
    
    deleteDir(dumpDir);
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
    
    // Génère le dump SQL complet
    await generateCompleteSQLDump(results);
    
    // Crée un fichier de résumé
    const summary = {
      timestamp: new Date().toISOString(),
      totalTables: tablesToDump.length,
      successCount: results.filter(r => r.success).length,
      failureCount: results.filter(r => !r.success).length,
      details: results.map(r => ({
        table: r.table,
        success: r.success,
        rowCount: r.success ? r.rowCount : 0,
        error: r.error || null
      }))
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
