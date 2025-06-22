const fs           = require('fs')
const { Pool }     = require('pg')
const cliProgress  = require('cli-progress')
require('dotenv').config({ override: true })

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: { rejectUnauthorized: false }
})

async function getOrCreateFile(chemin, createdAt) {
  // insère le fichier audio s’il n’existe pas
  await pool.query(
    `INSERT INTO fichiers_audio (chemin, created_at)
     VALUES ($1, $2)
     ON CONFLICT (chemin) DO NOTHING`,
    [chemin, createdAt]
  )
  // récupère son id
  const res = await pool.query(
    `SELECT id FROM fichiers_audio WHERE chemin = $1`,
    [chemin]
  )
  return res.rows[0].id
}

async function getOrCreateContributor(nom) {
  if (!nom) return null
  await pool.query(
    `INSERT INTO contributeur (nom)
     VALUES ($1)
     ON CONFLICT (nom) DO NOTHING`,
    [nom]
  )
  const res = await pool.query(
    `SELECT id FROM contributeur WHERE nom = $1`,
    [nom]
  )
  return res.rows[0].id
}

async function restoreFromSegments(jsonFile) {
  const dump     = JSON.parse(fs.readFileSync(jsonFile, 'utf8'))
  const segments = Array.isArray(dump.data) ? dump.data : dump

  // Initialise la barre de progression
  const bar = new cliProgress.SingleBar({
    format: 'Restoration |{bar}| {value}/{total} segments',
    hideCursor: true
  }, cliProgress.Presets.shades_classic)
  bar.start(segments.length, 0)

  try {
    await pool.query('BEGIN')

    // 1) Pré-remplir les lookup tables pour éviter les FK errors
    await pool.query(`
      INSERT INTO statut_transcription(code, libelle)
        VALUES ('brouillon','Brouillon'),
               ('validé'   ,'Validé'),
               ('rejeté'   ,'Rejeté')
      ON CONFLICT(code) DO NOTHING;

      INSERT INTO methode(code, description)
        VALUES ('manuel'     ,'Manuelle'),
               ('automatique','Automatique')
      ON CONFLICT(code) DO NOTHING;
    `)

    // 2) Vider la table des transcriptions
    await pool.query('TRUNCATE TABLE transcription RESTART IDENTITY CASCADE')

    for (const seg of segments) {
      const fileId    = await getOrCreateFile(seg.filename, seg.created_at)
      const contribId = await getOrCreateContributor(seg.author)

      await pool.query(
        `INSERT INTO transcription
           (id_fichier_audio, id_contributeur, texte, created_at,
            rating, date_creation, version, statut_code,
            methode_code, confiance)
         VALUES
           ($1,$2,$3,$4,$5,$4,1,$6,$7,NULL)`,
        [
          fileId,
          contribId,
          seg.transcription,
          seg.created_at,
          seg.rating  ?? 0,
          seg.status  || 'validé',
          seg.method  || 'manuel'
        ]
      )
      bar.increment()
    }

    await pool.query('COMMIT')
    bar.stop()
    console.log(`\n✅ Restauré ${segments.length} segments depuis "${jsonFile}"`)
  } catch (err) {
    await pool.query('ROLLBACK')
    bar.stop()
    console.error('❌ Erreur lors de la restauration :', err)
    process.exit(1)
  } finally {
    await pool.end()
  }
}

const [,, jsonFile] = process.argv
if (!jsonFile) {
  console.error('❌ Utilisation : node db-restore-json.cjs dump.json')
  process.exit(1)
}
restoreFromSegments(jsonFile)