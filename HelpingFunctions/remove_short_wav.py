import os
import argparse
from pydub import AudioSegment

def delete_short_audio_files(directory, min_duration):
    # Parcourir tous les fichiers dans le répertoire
    for filename in os.listdir(directory):
        if filename.endswith(".mp3") or filename.endswith(".wav"):
            filepath = os.path.join(directory, filename)

            try:
                # Charger le fichier audio
                if filename.endswith(".mp3"):
                    audio = AudioSegment.from_mp3(filepath)
                elif filename.endswith(".wav"):
                    audio = AudioSegment.from_wav(filepath)

                # Obtenir la durée en secondes
                duration_in_seconds = len(audio) / 1000

                # Supprimer le fichier si la durée est inférieure à la durée minimale spécifiée
                if duration_in_seconds < min_duration:
                    os.remove(filepath)
                    print(f"Supprimé : {filename} ({duration_in_seconds} secondes)")
                else:
                    print(f"Conservé : {filename} ({duration_in_seconds} secondes)")
            except Exception as e:
                print(f"Erreur lors du traitement du fichier {filename}: {e}")

def main():
    # Configurer le parser d'arguments
    parser = argparse.ArgumentParser(description='Supprimer les fichiers MP3 et WAV dont la durée est inférieure à une durée spécifiée.')
    parser.add_argument('directory', type=str, help='Le répertoire contenant les fichiers audio')
    parser.add_argument('min_duration', type=float, help='La durée minimale en secondes')

    # Parser les arguments
    args = parser.parse_args()

    # Appeler la fonction avec les arguments fournis
    delete_short_audio_files(args.directory, args.min_duration)

if __name__ == "__main__":
    main()
