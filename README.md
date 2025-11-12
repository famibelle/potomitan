# [Potomitan] Audio segmenter
*L'inclusion linguistique pour la Guadeloupe*

![Logo du projet](https://i.imgur.com/ZTaBTZD.png)

> &copy; 2025 [Potomitan™](https://potomitan.io). Tous droits réservés.

## Présentation
Ce répertoire contient le code permettant de ségmenter des fichiers audio en suivant la *pipeline* développée par [Medhi Famibelle](https://github.com/famibelle), les ségments ainsi réalisés ont pour objectif d'être rendu disponible sur la [plateforme de marquage de Potomitan](https://transcrire.potomitan.io).

# Définition des scripts

## Transfert et archivage des fichiers audios

Ce script Bash automatise le transfert de fichiers audio depuis un répertoire local vers un répertoire distant sur un serveur via SSH. Il garde en mémoire la liste des fichiers déjà transférés pour éviter les doublons et archive localement tous les fichiers traités.

Pour exécuter ce script, entrez la commande :
```bash
npm run push-audio
```

## Synchronisation des fichiers audio et mise à jour de la base PostgreSQL

Ce script Bash permet de synchroniser la liste des fichiers audio présentes sur un serveur distant avec une base de données PostgreSQL distante. Il crée un tunnel SSH local sécurisé vers le serveur distant, interroge la base de données, vérifie quels fichiers sont enregistrés, et insère dans la base ceux qui manquent selon la liste des fichiers distants.

Pour exécuter ce script, entrez la commande :
```bash
npm run update-audio
```

## Synchronisation des fichiers audio et mise à jour de la base PostgreSQL

Ce script Bash permet d'extraire la liste des fichiers audio présentes sur un serveur distant avec au moins une transcription. Il crée un tunnel SSH local sécurisé vers le serveur distant, interroge la base de données, extrais les données en SQL, et génère un fichier JSON contenant les informations.

Pour exécuter ce script, entrez la commande :
```bash
npm run extract-transition
```

# Variables d’environnement
Les scripts utilisent un ensemble de variables d’environnement à configurer dans un fichier `.env` pour garantir la flexibilité et la sécurité des connexions ainsi que le comportement du serveur.

| Variable      | Description                                                                                              |
|---------------|----------------------------------------------------------------------------------------------------------|
| `REMOTE_HOST` | Adresse IP ou nom de domaine du serveur distant hébergeant les fichiers audio                            |
| `REMOTE_DIR`  | Chemin absolu du répertoire distant contenant les fichiers audio à synchroniser                          |
| `LOCAL_DIR`   | Répertoire local contenant les fichiers audio à traiter                                                 |
| `LIST_FILE`   | Fichier local listant les fichiers audio déjà transférés ou présents sur le serveur distant              |
| `ARCHIVE_DIR` | Répertoire local où les fichiers audio traités sont archivés après transfert ou vérification            |
| `DB_USER`     | Nom d'utilisateur PostgreSQL pour la connexion à la base de données                                     |
| `DB_PASSWORD` | Mot de passe de l'utilisateur PostgreSQL                                                               |
| `DB_NAME`     | Nom de la base de données PostgreSQL ciblée                                                             |
| `DB_TABLE`    | Nom de la table contenant les enregistrements audio                                                    |
| `DB_HOST`     | Adresse IP ou nom d'hôte de la base PostgreSQL (souvent `127.0.0.1` pour localhost via tunnel SSH)      |
| `DB_PORT`     | Port d'écoute de la base PostgreSQL                                                                      |

# Licences
- Le **code source** de ce dépôt est distribué sous licence [Mozilla Public License 2.0 (MPL-2.0)](LICENSE.txt).
- Le nom **"POTOMITAN"**, le logo, l’interface utilisateur et les éléments de marque sont protégés indépendamment par le droit des marques et le droit d’auteur.
- © 2025 Potomitan™. Tous droits réservés.

# Contact
Pour toute question concernant l'interface utilisateur, contactez brigitte.democrite@brdcie.com