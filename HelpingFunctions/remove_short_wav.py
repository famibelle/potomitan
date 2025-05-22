import os
import librosa
import sys

def remove_short_wav_files(directory, min_duration=0.5):
    for filename in os.listdir(directory):
        if filename.endswith(".wav"):
            file_path = os.path.join(directory, filename)
            try:
                # Charger le fichier audio
                y, sr = librosa.load(file_path, sr=None)
                duration = librosa.get_duration(y=y, sr=sr)

                # Supprimer le fichier si la durée est inférieure à min_duration
                if duration < min_duration:
                    os.remove(file_path)
                    print(f"Supprimé: {filename} (durée: {duration:.2f} secondes)")
            except Exception as e:
                print(f"Erreur lors du traitement de {filename}: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python remove_short_wav.py <directory>")
        sys.exit(1)
    directory = sys.argv[1]
    remove_short_wav_files(directory)
