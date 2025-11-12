import os
import sys
import glob
import statistics
from mutagen import File

def format_duration(seconds: float) -> str:
    """Convertit un nombre de secondes en H:MM:SS."""
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h:d}:{m:02d}:{s:02d}"

def gather_audio_stats(directory: str):
    # Extensions audio prises en charge
    exts = ('*.mp3', '*.wav', '*.flac', '*.ogg', '*.m4a')
    paths = []
    for ext in exts:
        paths.extend(glob.glob(os.path.join(directory, ext)))
    if not paths:
        print(f"Aucun fichier audio trouvé dans {directory}")
        return

    durations = []
    for path in paths:
        audio = File(path)
        if not audio or not hasattr(audio.info, 'length'):
            continue
        durations.append((path, audio.info.length))

    if not durations:
        print("Aucun fichier audio lisible trouvé.")
        return

    # Extraction des durées
    times = [d for _, d in durations]
    total = sum(times)
    mean = statistics.mean(times)
    stdev = statistics.stdev(times) if len(times) > 1 else 0.0
    shortest = min(durations, key=lambda x: x[1])
    longest  = max(durations, key=lambda x: x[1])

    # Affichage
    print("Statistiques des durées audio")
    print("------------------------------")
    print(f"Nombre de fichiers : {len(times)}")
    print(f"Durée cumulée      : {format_duration(total)}")
    print(f"Durée moyenne      : {format_duration(mean)}")
    print(f"Écart-type         : {stdev:.2f} secondes")
    print(f"Fichier le plus court : {os.path.basename(shortest[0])} ({format_duration(shortest[1])})")
    print(f"Fichier le plus long   : {os.path.basename(longest[0])} ({format_duration(longest[1])})")

if __name__ == "__main__":
    # Usage : python audio_stats.py [répertoire]
    audio_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join("public", "audio")
    if not os.path.isdir(audio_dir):
        print(f"Erreur : le répertoire « {audio_dir} » n'existe pas.")
        sys.exit(1)
    gather_audio_stats(audio_dir)