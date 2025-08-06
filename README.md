# 🧠 Kréyol Audio Transcription Pipeline 🇬🇵

Ce dépôt contient une pipeline complète pour le traitement, la transcription et l'enrichissement de fichiers audio en créole guadeloupéen.  
Elle est optimisée pour fonctionner avec **Whisper Large V3 Turbo** qui supporte nativement le kreol haïtien (ht) tout en intégrant un ensemble d'étapes de prétraitement avancé : découpage, filtrage, diarisation, suppression, transcription, tagging ID3, et annotation manuelle via une interface Vue.js.

---

## 🔁 Pipeline complète

```mermaid
graph TD
    A[Fichier Multimedia en Kréyol de Guadeloupe] --> B[Split en segments de 15mn max]
    B --> C[Filtrage sur les Voix Humaines]
    C --> D[Diarization de l'audio]
    D --> E[Suppression des segments audio < 5s]
    E --> F[Transcription avec Whisper Turbo V3 et créole haïtien]
    F --> G[Ajout de la transcription dans le tag ID3 du MP3]
```

---

## 🚀 Fonctionnalités

- 📎 **Découpage automatique** de fichiers volumineux en segments de 15 minutes  
- 🔊 **Filtrage des voix humaines** via extraction vocale  
- 🗣️ **Diarisation** des locuteurs avec `pyannote/speaker-diarization`  
- ✂️ **Suppression des segments < 2s**  
- 📝 **Transcription haute qualité** avec `openai/whisper-large-v3-turbo`, en créole haïtien (`ht`)  
- 🏷️ **Ajout des transcriptions dans les tags ID3** des fichiers `.mp3`  
- ✍🏽 **Interface d’annotation manuelle** avec [Potomitan (Vue.js)](https://github.com/famibelle/potomitan)  
- 🗄️ **Sauvegarde JSON ou insertion en base PostgreSQL**

---

## 📂 Structure des fichiers

```bash
.
├── batch_pipeline.py          # Script principal de traitement
├── batch_vocal_extract_demucs.py
├── batch_diarization.py
├── batch_remove_short_wav.py
├── pipeline.log               # Fichier de log
├── json_logs/                 # Insertion et logs au format JSON
└── .env                       # Configuration (DATABASE_URL, etc.)
```

---

## ⚙️ Installation

### 1. Cloner le dépôt

```bash
git clone https://github.com/famibelle/potomitan.git
cd potomitan
```

### 2. Installer les dépendances

```bash
pip install -r requirements.txt
```


### 3. Configurer l’environnement

Crée un fichier `.env` :

```env
DATABASE_URL=postgresql://user:password@host:port/dbname
HUGGINFACE=YOUR_Token
```

---

## 🧪 Utilisation

### 🔹 Pour un seul fichier

```bash
python batch_pipeline.py path/to/audio.mp3 --output_dir pipeline_tmp
```

### 🔹 Pour un dossier de fichiers

```bash
python batch_pipeline.py ./dossier_audios --output_dir pipeline_tmp
```

### 🔹 Mode JSON uniquement (sans base PostgreSQL)

```bash
python batch_pipeline.py ./audio --no-db
```

---

## 🧠 Modèles utilisés

| Étape         | Modèle / Techno                       |
|---------------|---------------------------------------|
| Extraction    | Demucs (via `batch_vocal_extract`)    |
| Diarisation   | `pyannote/speaker-diarization-3.1`    |
| Transcription | `openai/whisper-large-v3-turbo`       |

---

## 🖋️ Interface d’annotation manuelle

Une interface Web construite avec **Vue.js** est disponible dans le dépôt [famibelle/potomitan](https://github.com/famibelle/potomitan) pour :

- 🎧 Écouter les segments audio
- ✍🏽 Corriger manuellement les transcriptions

### 🔧 Déploiement local rapide

```bash
git clone https://github.com/famibelle/potomitan.git
cd potomitan
npm install
npm run dev
```

> L’interface est accessible sur `http://localhost:5173/`  
> Les données à annoter doivent être placées dans `public/data/` (format `.json` ou `.wav` + `.txt`).

### 📌 Exemple d’usage combiné

1. Utilise la pipeline automatique pour transcrire tous tes fichiers :
   ```bash
   python batch_pipeline.py ./data/audio_kreyol --output_dir pipeline_tmp
   ```

2. Glisse les fichiers `.json` ou `.txt` dans `potomitan/public/data/`

3. Lance l’interface d’annotation pour validation linguistique manuelle

4. Récupère les fichiers corrigés pour :
   - un retrain modèle
   - une évaluation qualité
   - une insertion enrichie en base PostgreSQL

---

## 💾 Base de données (optionnel)

La transcription est insérée dans 3 tables PostgreSQL :
- `fichiers_audio`
- `contributeur`
- `transcription`

Les erreurs ou doublons sont journalisés dans `json_logs/`.

---

## 📈 Monitoring & Stats

Chaque exécution de pipeline produit :
- Un journal `pipeline.log`
- Des fichiers `db_insertions_YYYY-MM-DD.json`
- Un suivi des temps d'exécution par étape
- Optionnel : consommation GPU affichée (si CUDA est disponible)

---

## 📎 TODO

- [ ] Ajouter une interface web de suivi global
- [ ] Support multi-langue (créole martiniquais, guyanais...)
- [ ] Indexation plein texte dans PostgreSQL ou Elastic
- [ ] Exportation vers [Potomitan](https://github.com/famibelle/potomitan) via API ou montage automatique

---

## 📄 Licence

MIT © 2025 – Projet audio-linguistique Kréyol

---

## ✊🏽 Contribuer

Pour contribuer, ouvre une _issue_, une _pull request_ ou contacte moi.
