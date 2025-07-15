// notifications-init-db.cjs
// Crée la table notifications dans PostgreSQL (similaire à init-db.cjs)

const { Pool } = require('pg')

// Charger les variables d'environnement uniquement en local
if (process.env.NODE_ENV !== 'production') {
  require('dotenv').config({ override: true });
}

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: { rejectUnauthorized: false }
})

async function createNotificationsTable() {
  await pool.query(`
    CREATE TABLE IF NOT EXISTS notifications (
      id SERIAL PRIMARY KEY,
      type TEXT NOT NULL,
      file_id INTEGER,
      file_name TEXT,
      content TEXT,
      new_rating SMALLINT,
      timestamp TIMESTAMPTZ DEFAULT NOW()
    );
  `)
  console.log('✅ Table notifications créée')
  process.exit(0)
}

createNotificationsTable().catch(err => {
  console.error('❌ Erreur :', err)
  process.exit(1)
})
