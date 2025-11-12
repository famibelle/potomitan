#!/bin/bash

# Charger les variables d'environnement depuis .env
if [ -f .env ]; then
    export $(cat .env | xargs)
else
    echo "Fichier .env non trouvé."
    exit 1
fi

# Variables
REMOTE_HOST="$REMOTE_HOST"
REMOTE_DIR="$REMOTE_DIR"
LOCAL_DIR="$LOCAL_DIR"
LIST_FILE="$LIST_FILE"
ARCHIVE_DIR="$ARCHIVE_DIR"

# Demander le nom d'utilisateur SSH
read -p "Entrez le nom d'utilisateur SSH : " ssh_user

# Créer le dossier d'archive s'il n'existe pas
mkdir -p "$ARCHIVE_DIR"

# Récupérer la liste des fichiers distants
ssh "${ssh_user}@${REMOTE_HOST}" "ls \"${REMOTE_DIR}\" > \"${REMOTE_DIR}/liste_fichiers.txt\""
scp "${ssh_user}@${REMOTE_HOST}:${REMOTE_DIR}/liste_fichiers.txt" "$LIST_FILE"

# Créer le fichier de liste s'il n'existe pas
touch "$LIST_FILE"

# Lire les fichiers déjà uploadés dans un tableau (compatible macOS)
UPLOADED_FILES=()
while IFS= read -r line || [[ -n "$line" ]]; do
    UPLOADED_FILES+=("$line")
done < "$LIST_FILE"

# Récupérer tous les fichiers locaux (récursif, compatible macOS)
FILES=()
while IFS= read -r -d '' file; do
    FILES+=("$file")
done < <(find "$LOCAL_DIR" -type f -print0 2>/dev/null)

# Trier les fichiers (macOS utilise BSD sort, pas GNU)
IFS=$'\n' SORTED_FILES=($(printf "%s\n" "${FILES[@]}" | sort -r))
unset IFS

TOTAL=${#SORTED_FILES[@]}
echo "Nombre total de fichiers à vérifier : $TOTAL"
echo ""
COUNT=0
UPLOADED_COUNT=0
ARCHIVED_COUNT=0

for FILE in "${SORTED_FILES[@]}"; do
    REL_PATH="${FILE#$LOCAL_DIR/}"

    # Vérifier si le fichier a déjà été uploadé (grep compatible macOS)
    if printf '%s\n' "${UPLOADED_FILES[@]}" | grep -q "^${REL_PATH}$"; then
        # Déplacer vers audio_archive (même si déjà uploadé)
        ARCHIVE_PATH="$ARCHIVE_DIR/$(dirname "$REL_PATH")"
        mkdir -p "$ARCHIVE_PATH"
        if mv "$FILE" "$ARCHIVE_DIR/$REL_PATH"; then
            ((ARCHIVED_COUNT++))
            echo -n "A"  # Archivé sans upload
        else
            echo ""
            echo "⚠️ Échec de l'archivage pour : $REL_PATH"
        fi
    else
        # Créer le répertoire distant si nécessaire
        DIR_REMOTE=$(dirname "$REMOTE_DIR/$REL_PATH")
        ssh "${ssh_user}@$REMOTE_HOST" "mkdir -p \"$DIR_REMOTE\""

        # Upload du fichier
        if scp "$FILE" "${ssh_user}@$REMOTE_HOST:$REMOTE_DIR/$REL_PATH"; then
            # Ajouter à la liste des uploadés
            echo "$REL_PATH" >> "$LIST_FILE"

            # Déplacer vers audio_archive
            ARCHIVE_PATH="$ARCHIVE_DIR/$(dirname "$REL_PATH")"
            mkdir -p "$ARCHIVE_PATH"
            if mv "$FILE" "$ARCHIVE_DIR/$REL_PATH"; then
                ((UPLOADED_COUNT++))
                echo ""
                echo "Nouveau fichier transféré et archivé : $REL_PATH ($UPLOADED_COUNT/$TOTAL)"
            else
                echo ""
                echo "⚠️ Échec de l'archivage pour : $REL_PATH (après upload)"
            fi
        else
            echo ""
            echo "⚠️ Échec du transfert pour : $REL_PATH"
        fi
    fi
    ((COUNT++))
done

echo ""
echo "Traitement terminé :"
echo "- $UPLOADED_COUNT fichiers transférés et archivés."
echo "- $ARCHIVED_COUNT fichiers déjà uploadés et archivés."
echo "- $TOTAL fichiers traités au total."
