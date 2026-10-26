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
