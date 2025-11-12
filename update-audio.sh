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
REMOTE_DIR="$REMOTE_DIR"
LIST_FILE="$LIST_FILE"


# Demander le nom d'utilisateur SSH si non défini dans .env
if [ -z "$SSH_USER" ]; then
    read -p "Entrez le nom d'utilisateur SSH : " SSH_USER
fi

# Récupérer la liste des fichiers distants
echo "Connexion au serveur distant pour récupérer la liste des fichiers audio..."
ssh "${SSH_USER}@${REMOTE_HOST}" "ls \"${REMOTE_DIR}\" > \"${REMOTE_DIR}/liste_fichiers.txt\""
scp "${SSH_USER}@${REMOTE_HOST}:${REMOTE_DIR}/liste_fichiers.txt" "$LIST_FILE"

# Créer le fichier de liste s'il n'existe pas
touch "$LIST_FILE"

# Lire les fichiers distants dans un tableau (compatible Bash 3)
echo ""
echo "Lecture de la liste des fichiers audio distants..."
FILES_REMOTE=()
while IFS= read -r line || [[ -n "$line" ]]; do
    FILES_REMOTE+=("$line")
done < "$LIST_FILE"


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
echo "Création du tunnel SSH sur le port local $LOCAL_TUNNEL_PORT..."
ssh -f -N -M -S "$CONTROL_PATH" -L ${LOCAL_TUNNEL_PORT}:localhost:5432 "${SSH_USER}@${REMOTE_HOST}"

# Exécuter la requête psql pour récupérer tous les items de la table audio
echo ""
echo "Récupération des chemins audio depuis la base de données distante..."
UPDATED_SQL_AUDIO=$(PGPASSWORD="$DB_PASSWORD" psql -h localhost -p "$LOCAL_TUNNEL_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT path FROM $DB_TABLE;" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')

# Convertir UPDATED_SQL_AUDIO en tableau Bash
IFS=$'\n' read -r -d '' -a PATHS_ARRAY <<< "$UPDATED_SQL_AUDIO"

# Lire chaque ligne de LIST_FILE
echo ""
echo "Vérification des fichiers audio à ajouter dans la base de données..."j
while IFS= read -r LINE || [[ -n "$LINE" ]]; do
    # Vérifier si la ligne est présente dans UPDATED_SQL_AUDIO
    if ! echo "$UPDATED_SQL_AUDIO" | grep -qF "$LINE"; then
        # Ajouter le fichier dans la table audio
        PGPASSWORD="$DB_PASSWORD" psql -h localhost -p "$LOCAL_TUNNEL_PORT" -U "$DB_USER" -d "$DB_NAME" -c "INSERT INTO $DB_TABLE (path) VALUES ('$LINE');"
        echo "  -> $LINE à été ajouté dans la base."
    else
        echo "  -> $LINE est présent dans la base."
    fi
done < "$LIST_FILE"


echo "Vérification terminée."
