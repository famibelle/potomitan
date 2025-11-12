import os
import psycopg2
import argparse
from dotenv import load_dotenv
from tqdm import tqdm

# Charger les variables d'environnement
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

def clean_database(base_path="public/audio", dry_run=False):
    """Supprime les entrées de la base de données pour les fichiers qui n'existent plus sur le disque."""
    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        with conn.cursor() as cur:
            # Récupérer tous les chemins de fichiers référencés dans la base
            cur.execute("SELECT id, chemin FROM fichiers_audio;")
            files_in_db = cur.fetchall()

            total_files = len(files_in_db)
            deleted_files = 0

            for file_id, file_path in tqdm(files_in_db, desc="Vérification des fichiers", unit="fichier"):
                full_path = os.path.join(base_path, file_path)
                if not os.path.exists(full_path):
                    if dry_run:
                        print(f"🟡 Fichier à supprimer (dry-run) : {full_path}")
                        deleted_files += 1  # Incrémenter même en mode dry-run
                    else:
                        # Supprimer l'entrée de la base si le fichier n'existe pas
                        cur.execute("DELETE FROM fichiers_audio WHERE id = %s;", (file_id,))
                        print(f"🗑️ Fichier supprimé de la base : {full_path}")
                        deleted_files += 1

            if not dry_run:
                conn.commit()
                print(f"✅ Nettoyage terminé. {deleted_files} fichier(s) supprimé(s) sur {total_files} vérifié(s).")
            else:
                print(f"✅ Dry-run terminé. {deleted_files} fichier(s) à supprimer sur {total_files} vérifié(s). Aucun changement effectué.")
    except Exception as e:
        print(f"❌ Erreur lors du nettoyage de la base : {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Nettoie la base de données en supprimant les fichiers audio inexistants sur le disque.")
    parser.add_argument(
        "--path",
        default="public/audio",
        help="Chemin racine où les fichiers audio sont censés être stockés. Par défaut : /public/audio."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simule le nettoyage sans effectuer de suppression dans la base de données."
    )
    args = parser.parse_args()

    clean_database(base_path=args.path, dry_run=args.dry_run)