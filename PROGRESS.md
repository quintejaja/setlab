# PROGRESS

Registro de sesiones. Cada sesión agrega una entrada al final.

## 2026-10-23 — Tarea 0.1: Esqueleto
- Proyecto uv con layout `src/setlab/` según AGENTS.md (ingest, analysis, setgen, export, db, matching, cli).
- CLI con typer (`setlab --help`, `setlab version`) y 2 tests con pytest. `uv run pytest` pasa.
- Decisiones: Python fijado en 3.12 (`.python-version` y `requires-python >=3.12,<3.13`), porque essentia no tiene wheels para 3.14 (la única versión instalada en la máquina); uv baja la 3.12 solo. Build con hatchling. Solo typer y pytest como dependencias por ahora: el resto se agrega en la tarea que lo usa.
- Los módulos de AGENTS.md existen como stubs vacíos ("Pendiente: ver PLAN.md").
- Bloqueos: ninguno.
- Archivos: `pyproject.toml`, `.python-version`, `uv.lock`, `src/setlab/cli.py`, `src/setlab/__init__.py`, `tests/test_cli.py`.

## 2026-10-23 — Cambio de plan (sin tarea)
- Se descarta la biblioteca local de audio: el usuario no va a aportar archivos.
- Nuevo flujo: importar playlist de Spotify (propia o pública) -> features -> descubrir temas parecidos -> setlist -> playlist nueva en Spotify.
- Decisiones del usuario: usar GetSongBPM y previews de Deezer + essentia según lo que haga falta (reglas en AGENTS.md, sección "Fuentes de features"); la única salida es una playlist en Spotify (se quitan rekordbox XML, M3U y el reporte); se aceptan playlists propias y públicas de otros.
- Se quitan mutagen y pyrekordbox del stack; se agregan httpx, Last.fm, Deezer y GetSongBPM.
- Estructura: `ingest/`, `matching.py` y `export/rekordbox.py` reemplazados por `sources/`, `discover.py` y `export/spotify.py`.
- Para tener en cuenta: GetSongBPM pide un backlink a su sitio para dar API key; Last.fm también pide registrar una API key (gratis).

## 2026-10-23 — Tarea 0.2: Esquema y módulo db
- `schema.sql` con 6 tablas: tracks, playlists, playlist_tracks, features, candidates, api_cache.
- `setlab.db.connect()` abre la DB (`:memory:`, ruta, o `SETLAB_DB` / `setlab.db` por defecto), activa foreign keys y crea las tablas. 22 tests nuevos.
- Decisiones: un solo catálogo `tracks` para temas de playlists y descubiertos (identificados por spotify_id, con isrc y deezer_id para cruzar fuentes). `features` guarda la fuente de cada dato (bpm_source, key_source, audio_source, genre_source). CHECKs en la DB para Camelot (1A–12B), energía/danceability 0–1, bounce 1–5 y BPM > 0. `api_cache` cumple la regla de no repetir pedidos a APIs. Borrar una playlist borra sus tracks asociados y candidatos (cascade).
- Bloqueos: ninguno.
- Archivos: `src/setlab/db/schema.sql`, `src/setlab/db/__init__.py`, `tests/test_db.py`.

## 2026-10-24 — Tarea 1.1: OAuth PKCE + importar playlist
- `setlab playlist import <link>` acepta link (con ?si= o /intl-xx/), URI o id; se loguea con PKCE (abre el navegador la primera vez) y guarda la playlist y sus temas en la DB. 19 tests nuevos con un cliente falso.
- Probado en vivo con la playlist "Actual": 432 items, 430 temas únicos (hay 2 repetidos en la playlist), todos con ISRC.
- Decisiones: los scopes ya incluyen escritura de playlists para la 5.1, así no hay que volver a loguearse. Token cacheado en `.spotify_token` (en .gitignore). Se aceptan las claves "track" e "item" porque Spotify renombró el campo en 2026. Owner "spotify" o 403/404 dan un error claro (editorial o privada). Reimportar reemplaza el orden de la playlist sin duplicar temas. Se agregaron spotipy y python-dotenv.
- `.env` creado con SPOTIFY_CLIENT_ID y SPOTIFY_REDIRECT_URI; NO se commitea (está en .gitignore).
- Bloqueos: ninguno.
- Archivos: `src/setlab/sources/spotify.py`, `src/setlab/db/repo.py`, `src/setlab/cli.py`, `tests/test_spotify.py`, `.gitignore`, `pyproject.toml`.

## 2026-10-25 — Decisiones del humano (sin tarea)
- Análisis de audio con librosa en vez de essentia (essentia no tiene wheels para Windows). Energía y danceability son estimaciones propias.
- UI: web local. Se hace al final, después de que todo ande por CLI.
- Se trabaja en tandas de tareas independientes (protocolo actualizado en AGENTS.md). Tanda 1: 1.2, 2.1, 2.2, 4.1.

## 2026-10-25 — Tanda 1: tareas 4.1, 2.1, 1.2 y 2.2

### 4.1 Compatibilidad entre dos temas
- `setgen/compat.py`: `transition(a, b)` devuelve score 0–1, tipo (mezcla, half_time, echo_out, corte) y relación de key.
- Decisiones: los scores por tipo no se pisan: mezcla >= 0.5 > echo_out (0.25–0.45) > corte (0.1–0.2). Penalización: key adyacente o relativa -0.1, key desconocida -0.2, BPM lineal hasta -0.2 al 6 %, -0.1 extra por half-time. BPM desconocido = corte (no se puede garantizar la mezcla). La energía no se mira acá: la maneja la curva en 4.3.

### 2.1 Camelot + GetSongBPM
- `analysis/camelot.py` convierte Am, C#m, E♭ major, A minor, etc. a Camelot (rueda completa testeada). `sources/getsongbpm.py` busca por artista+título con fuzzy y pide el detalle si la búsqueda no trae tempo.
- `sources/http.py`: cliente HTTP compartido con cache en `api_cache` (la api_key no se guarda en la clave), reintento en 429 y 404 cacheado. `sources/text.py`: normaliza títulos (saca feat., acentos y "Remastered", pero NO remix/edit).
- La API está en `api.getsong.co` (el dominio viejo está detrás de Cloudflare). Sin probar en vivo: falta `GETSONGBPM_API_KEY`.

### 1.2 Búsqueda en Spotify
- `search_track()` en `sources/spotify.py`: primero `isrc:`, después `track:"..." artist:"..."` y por último texto libre; elige con rapidfuzz (título 60 % + artista principal 40 %, -10 si la duración difiere más de 15 s). Umbral 82. Cache opcional en `api_cache`.
- Probado en vivo: Gasolina, Tití Me Preguntó, Systëm (con diéresis), Marea (con feat.), Bzrp Session 52; un tema inexistente devuelve None.

### 2.2 Deezer + librosa
- `sources/deezer.py` (ISRC y búsqueda), `analysis/audio.py` (BPM con beat_track, key con perfiles Krumhansl sobre chroma CQT, energía y danceability propias) y `analysis/runner.py` (baja el preview a un temporal, analiza y lo borra). Comando `setlab audio --playlist X`.
- Cambio de esquema: tabla nueva `audio_analysis` (resultado crudo por tema, con status ok/no_preview/not_found/error). Los que dieron error se reintentan; el resto no se recalcula ni se vuelve a consultar Deezer.
- El preview de Deezer viene firmado y vence a los ~15 min: la consulta del tema no se cachea, se guarda `deezer_id` en tracks.
- BPM: beat_track solo da valores cuantizados (error mediano 1.3 %). Se refina con una recta sobre los tiempos de los beats (hop 128): error mediano 0.14 % contra el BPM de Deezer (43 temas; 40 dentro del 2 %, 1 fuera del 6 %). Opción `--rehacer` para recalcular todo.
- Probado en vivo con "Actual": 421 analizados, 2 no están en Deezer, 7 sin preview, 0 errores. Ningún audio queda en disco. Tarda ~10 min para 430 temas.
- Pendiente para 2.3: la energía cae casi toda entre 0.45 y 0.85 (promedio 0.66). Para la curva del set conviene usarla relativa a la playlist (percentiles), no absoluta.
- Bloqueos: ninguno. Falta `LASTFM_API_KEY` y `GETSONGBPM_API_KEY` para probar en vivo 2.1, 2.3 y 3.1.
