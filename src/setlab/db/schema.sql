-- Esquema de Setlab. Es el contrato entre módulos: si cambia, documentarlo en PROGRESS.md.

-- Catálogo de temas (de playlists importadas o descubiertos).
CREATE TABLE IF NOT EXISTS tracks (
    id           INTEGER PRIMARY KEY,
    spotify_id   TEXT UNIQUE,
    isrc         TEXT,
    title        TEXT NOT NULL,
    artists      TEXT NOT NULL,          -- nombres separados por ", "
    duration_ms  INTEGER CHECK (duration_ms IS NULL OR duration_ms > 0),
    deezer_id    INTEGER,
    created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_tracks_isrc ON tracks (isrc);

-- Playlists de Spotify importadas.
CREATE TABLE IF NOT EXISTS playlists (
    id           INTEGER PRIMARY KEY,
    spotify_id   TEXT NOT NULL UNIQUE,
    name         TEXT NOT NULL,
    owner        TEXT,
    snapshot_id  TEXT,                   -- para saber si cambió desde la última importación
    imported_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS playlist_tracks (
    playlist_id  INTEGER NOT NULL REFERENCES playlists (id) ON DELETE CASCADE,
    position     INTEGER NOT NULL CHECK (position >= 0),
    track_id     INTEGER NOT NULL REFERENCES tracks (id) ON DELETE CASCADE,
    PRIMARY KEY (playlist_id, position)
);
CREATE INDEX IF NOT EXISTS idx_playlist_tracks_track ON playlist_tracks (track_id);

-- Características de cada tema. Cada campo puede venir de una fuente distinta.
CREATE TABLE IF NOT EXISTS features (
    track_id       INTEGER PRIMARY KEY REFERENCES tracks (id) ON DELETE CASCADE,
    bpm            REAL CHECK (bpm IS NULL OR bpm > 0),
    camelot        TEXT CHECK (camelot IS NULL OR camelot GLOB '[1-9][AB]' OR camelot GLOB '1[0-2][AB]'),
    energy         REAL CHECK (energy IS NULL OR energy BETWEEN 0 AND 1),
    danceability   REAL CHECK (danceability IS NULL OR danceability BETWEEN 0 AND 1),
    genre          TEXT,
    bounce         INTEGER CHECK (bounce IS NULL OR bounce BETWEEN 1 AND 5),  -- manual
    bpm_source     TEXT CHECK (bpm_source IS NULL OR bpm_source IN ('getsongbpm', 'essentia', 'manual')),
    key_source     TEXT CHECK (key_source IS NULL OR key_source IN ('getsongbpm', 'essentia', 'manual')),
    audio_source   TEXT CHECK (audio_source IS NULL OR audio_source IN ('essentia')),  -- energía y danceability
    genre_source   TEXT CHECK (genre_source IS NULL OR genre_source IN ('lastfm', 'manual')),
    updated_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Temas nuevos sugeridos para una playlist (modo "descubrir").
CREATE TABLE IF NOT EXISTS candidates (
    playlist_id    INTEGER NOT NULL REFERENCES playlists (id) ON DELETE CASCADE,
    track_id       INTEGER NOT NULL REFERENCES tracks (id) ON DELETE CASCADE,
    source         TEXT NOT NULL CHECK (source IN ('lastfm_similar', 'lastfm_artist', 'deezer_artist')),
    seed_track_id  INTEGER REFERENCES tracks (id) ON DELETE SET NULL,  -- tema de la playlist que lo originó
    score          REAL,                 -- parecido con la playlist (se llena en la tarea 3.2)
    created_at     TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (playlist_id, track_id, source)
);

-- Cache de respuestas de APIs externas, para no pedir dos veces lo mismo.
CREATE TABLE IF NOT EXISTS api_cache (
    source      TEXT NOT NULL,           -- 'spotify', 'lastfm', 'deezer', 'getsongbpm'
    key         TEXT NOT NULL,           -- endpoint + parámetros normalizados
    response    TEXT NOT NULL,           -- JSON
    fetched_at  TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (source, key)
);

-- Resultado crudo del análisis de audio del preview de Deezer (tarea 2.2).
-- 2.3 combina esto con GetSongBPM y Last.fm para llenar `features`.
-- Si hay fila, no se vuelve a analizar (salvo status 'error').
CREATE TABLE IF NOT EXISTS audio_analysis (
    track_id        INTEGER PRIMARY KEY REFERENCES tracks (id) ON DELETE CASCADE,
    status          TEXT NOT NULL CHECK (status IN ('ok', 'no_preview', 'not_found', 'error')),
    deezer_id       INTEGER,
    deezer_bpm      REAL,                -- el BPM que trae Deezer (suele venir en 0 = desconocido)
    bpm             REAL CHECK (bpm IS NULL OR bpm > 0),
    camelot         TEXT CHECK (camelot IS NULL OR camelot GLOB '[1-9][AB]' OR camelot GLOB '1[0-2][AB]'),
    key_confidence  REAL,
    energy          REAL CHECK (energy IS NULL OR energy BETWEEN 0 AND 1),
    danceability    REAL CHECK (danceability IS NULL OR danceability BETWEEN 0 AND 1),
    error           TEXT,
    analyzed_at     TEXT NOT NULL DEFAULT (datetime('now'))
);
