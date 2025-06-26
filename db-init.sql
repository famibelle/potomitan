-- Initialisation de la base de données pour l'application de transcription audio

CREATE TABLE IF NOT EXISTS langue (
    code    VARCHAR(5) PRIMARY KEY,
    libelle TEXT      NOT NULL
);

CREATE TABLE IF NOT EXISTS methode (
    code        VARCHAR(20) PRIMARY KEY,
    description TEXT
);

CREATE TABLE IF NOT EXISTS statut_transcription (
    code    VARCHAR(20) PRIMARY KEY,
    libelle TEXT       NOT NULL
);

-- Table FichiersAudio
-- Cette table stocke les informations sur les fichiers audio à transcrire
CREATE TABLE IF NOT EXISTS fichiers_audio (
    id          SERIAL    PRIMARY KEY,
    chemin      TEXT      NOT NULL UNIQUE,
    titre       TEXT,
    artiste      TEXT,
    annee       SMALLINT,
    commentaire  TEXT,
    lyrics      TEXT,
    source      TEXT,
    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    likes       INTEGER   NOT NULL DEFAULT 0,
    dislikes    INTEGER   NOT NULL DEFAULT 0
);

-- Table Contributeur
-- Cette table stocke les contributeurs qui participent à la transcription
CREATE TABLE IF NOT EXISTS contributeur (
    id               SERIAL    PRIMARY KEY,
    nom              TEXT      NOT NULL,
    email            TEXT      UNIQUE,
    role             TEXT,
    date_inscription TIMESTAMP NOT NULL DEFAULT NOW(),
    actif            BOOLEAN   NOT NULL DEFAULT TRUE
);

-- Table Transcription
-- Cette table stocke les transcriptions des fichiers audio
CREATE TABLE IF NOT EXISTS transcription (
    id               SERIAL     PRIMARY KEY,
    id_fichier_audio  INTEGER    NOT NULL
        REFERENCES fichiers_audio(id)
        ON DELETE CASCADE,
    id_contributeur   INTEGER
        REFERENCES contributeur(id),
    texte            TEXT       NOT NULL,
    langue_code      VARCHAR(5) NOT NULL DEFAULT 'gp'
        REFERENCES langue(code),
    date_creation    TIMESTAMP  NOT NULL DEFAULT NOW(),
    version          INTEGER    NOT NULL DEFAULT 1,
    statut_code      VARCHAR(20)
        REFERENCES statut_transcription(code),
    methode_code     VARCHAR(20)
        REFERENCES methode(code),
    confiance        NUMERIC(3,2),
    updated_at       TIMESTAMP,
    rating           INTEGER
);

CREATE TABLE IF NOT EXISTS traduction (
    id               SERIAL     PRIMARY KEY,
    id_transcription INTEGER    NOT NULL
        REFERENCES transcription(id)
        ON DELETE CASCADE,
    langue_code      VARCHAR(5) NOT NULL
        REFERENCES langue(code),
    texte            TEXT       NOT NULL,
    date_creation    TIMESTAMP  NOT NULL DEFAULT NOW(),
    confiance        NUMERIC(3,2),
    updated_at       TIMESTAMP
);