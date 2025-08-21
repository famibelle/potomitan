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
    G --> H[Annotation par un linguiste via potomitan.io/contribuer]
    H --> I[Validation finale + Export Hugging Face Dataset]
```

---

## 🚀 Fonctionnalités

- 📎 **Découpage automatique** de fichiers volumineux en segments de 15 minutes  
- 🔊 **Filtrage des voix humaines** via extraction vocale  
- 🗣️ **Diarisation** des locuteurs avec `pyannote/speaker-diarization`  
- ✂️ **Suppression des segments < 2s**  
- 📝 **Transcription haute qualité** avec `openai/whisper-large-v3-turbo`, en créole haïtien (`ht`)  
- 🏷️ **Ajout des transcriptions dans les tags ID3** des fichiers `.mp3`  
- ✍🏽 **Interface d’annotation linguistique** [potomitan.io/contribuer](https://potomitan.io/contribuer)  
- ☁️ **Publication des données validées** sur Hugging Face :  
  👉🏽 [POTOMITAN/potomitan-gcf-transcription](https://huggingface.co/datasets/POTOMITAN/potomitan-gcf-transcription)

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


## 💾 Base de données (optionnel)

La transcription est insérée dans 3 tables PostgreSQL :
- `fichiers_audio`
- `contributeur`
- `transcription`

Les erreurs ou doublons sont journalisés dans `json_logs/`.

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

## 📈 Monitoring & Stats

Chaque exécution de pipeline produit :
- Un journal `pipeline.log`
- Des fichiers `db_insertions_YYYY-MM-DD.json`
- Un suivi des temps d'exécution par étape

---
## ☁️ Diffusion sur Hugging Face

Les segments validés sont publiés dans le dataset :

🔗 **[POTOMITAN/potomitan-gcf-transcription](https://huggingface.co/datasets/POTOMITAN/potomitan-gcf-transcription)**

Ce corpus contribue à la documentation et au développement d’outils pour les langues créoles, notamment en NLP, TTS, ASR, et lexicographie.

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


## 🌐 Liens utiles

- 🔗 Interface d'annotation : https://potomitan.io/contribuer  
- 📦 Dataset final : https://huggingface.co/datasets/POTOMITAN/potomitan-gcf-transcription  
- 💻 Code de l'interface locale : [github.com/famibelle/potomitan](https://github.com/famibelle/potomitan)

