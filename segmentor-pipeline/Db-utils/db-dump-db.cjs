// dump-db.cjs
const { spawn } = require('child_process');
require('dotenv').config({ override: true });

const dbUrl = process.env.DATABASE_URL;

if (!dbUrl) {
  console.error('❌ DATABASE_URL non défini dans .env');
  process.exit(1);
}

console.log('⏳ Dump de la base de données en cours...\n');

const dump = spawn('pg_dump', [dbUrl]);

dump.stdout.on('data', (data) => {
  process.stdout.write(data);
});

dump.stderr.on('data', (data) => {
  process.stderr.write(data);
});

dump.on('close', (code) => {
  if (code === 0) {
    console.log('\n✅ Dump terminé avec succès');
  } else {
    console.error(`\n❌ pg_dump s'est terminé avec le code ${code}`);
  }
});