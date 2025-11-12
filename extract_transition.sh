#!/bin/bash

# Charger les variables d'environnement depuis .env
if [ -f .env ]; then
    export $(cat .env | xargs)
else
    echo "Fichier .env non trouvé."
    exit 1
fi

# Fonction pour obtenir un port libre (compatible macOS/Linux)
get_free_port() {
    comm -23 <(seq 49152 65535 | sort) <(netstat -an | awk '/LISTEN/ && /127.0.0.1/ {split($4, a, ":"); print a[2]}' | sort -u) | sort -R | head -n 1
}

# Variables
REMOTE_HOST="$REMOTE_HOST"
REMOTE_DB_USER="$DB_USER"
REMOTE_DB_NAME="$DB_NAME"
REMOTE_DB_TABLE="$DB_TABLE"
REMOTE_DIR="/var/www/html/potomitan-transcription/webapp/audio"
LIST_FILE="./_ASSETS/liste_audio.txt"

# Demander le nom d'utilisateur SSH si non défini dans .env
if [ -z "$SSH_USER" ]; then
    read -p "Entrez le nom d'utilisateur SSH : " SSH_USER
fi

# Forcer la locale pour éviter l'erreur Perl
export LC_ALL=C.UTF-8
# Exporter le mot de passe pour psql
export PGPASSWORD="$DB_PASSWORD"
# Générer un port local libre
LOCAL_TUNNEL_PORT=$(get_free_port)

# Vérifier que le port est bien généré
if [ -z "$LOCAL_TUNNEL_PORT" ]; then
    echo "Erreur : Impossible de trouver un port libre."
    exit 1
fi

# Créer un ControlPath pour le tunnel SSH
CONTROL_PATH="/tmp/ssh-tunnel-$$-${LOCAL_TUNNEL_PORT}"

# Créer un tunnel SSH avec ControlPath
echo ""
echo "Connexion au tunnel SSH sur le port local $LOCAL_TUNNEL_PORT..."
ssh -f -N -M -S "$CONTROL_PATH" -L ${LOCAL_TUNNEL_PORT}:localhost:5432 "${SSH_USER}@${REMOTE_HOST}"

# Attendre que le tunnel soit prêt
sleep 2

# Requête SQL pour générer un tableau d'objets JSON sans doublons, avec la transcription la plus récente
SQL_QUERY="SELECT json_agg(json_build_object('audio', a.path, 'gcf', t.text, 'fr', tr.text)) AS json_result FROM audio a INNER JOIN (SELECT t.audio, t.text, t.uuid_transcription, ROW_NUMBER() OVER (PARTITION BY t.audio ORDER BY t.date_created DESC) AS rn FROM transcription t WHERE t.contributor != 'cd25e08c-5c5c-4827-87dd-a6f6432e55f3') t ON a.uuid_audio = t.audio AND t.rn = 1 LEFT JOIN translation tr ON t.uuid_transcription = tr.transcription;"

# Exécuter la requête et extraire le résultat JSON
echo ""
echo "Extraction des information et création du fichier JSON..."
psql -h localhost -p $LOCAL_TUNNEL_PORT -U $REMOTE_DB_USER -d $REMOTE_DB_NAME -t -c "$SQL_QUERY" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | python3 -c 'import sys, json; print(json.dumps(json.load(sys.stdin), indent=4, ensure_ascii=False))' > ./_ASSETS/audio.transcriptions.json

# Afficher les informations sur le fichier JSON
python3 -c '
import json
with open("./_ASSETS/audio.transcriptions.json", "r", encoding="utf-8") as f:
    data = json.load(f)
    if isinstance(data, list):
        count_audio = len(data)
        count_transcription = len([item for item in data if item.get("gcf")])
        count_translation = len([item for item in data if item.get("fr")])
        print("- Nombre de audio :", count_audio)
        print("- Nombre de transcription :", count_transcription)
        print("- Nombre de traduction :", count_translation)
    else:
        print("- Format JSON invalide")
'


# Fermer le tunnel SSH
echo ""
echo "Fermeture du tunnel SSH..."
ssh -S "$CONTROL_PATH" -O exit "${SSH_USER}@${REMOTE_HOST}"

echo "Extraction terminée."
