# Setlab — generador de sets para DJ

## Qué es
Herramienta local que toma mis playlists de Spotify, las cruza con mi biblioteca de archivos de audio,
analiza cada tema (BPM, key, energía, danceability, género) y genera sets ordenados para pinchar
en rekordbox con una Pioneer DDJ-FLX4. Estilo open format: trap, reggaetón, RKT, tech/house.

## Stack
- Python 3.12 + uv · SQLite (archivo local) · pytest
- spotipy (Spotify Web API, OAuth PKCE) · mutagen (tags) · rapidfuzz (matching)
- essentia (BPM, key, energía, modelos de género) · librosa como fallback
- pyrekordbox (leer/escribir XML de rekordbox)
- Todo gratis y local. Prohibido agregar servicios pagos o nube.

## Arquitectura
```
src/setlab/
  ingest/spotify.py     # lee playlists -> tracks_spotify
  ingest/library.py     # escanea carpeta de audio + XML de rekordbox -> tracks_local
  matching.py           # une spotify <-> local (artista+título, fuzzy)
  analysis/             # features por archivo, cacheadas por hash del archivo
  setgen/graph.py       # grafo de compatibilidad
  setgen/search.py      # búsqueda del set (beam search + curva de energía)
  export/rekordbox.py   # playlist XML para rekordbox + M3U
  cli.py                # punto de entrada (typer)
```
El esquema de la DB (`src/setlab/db/schema.sql`) es el contrato entre módulos.
Si una tarea necesita cambiarlo, documentar el cambio en PROGRESS.md.

## Reglas de dominio
- Key en notación Camelot (1A–12B). Compatibles: misma key, ±1 número con la misma letra, y cambio A<->B con el mismo número.
- BPM: compatible si |Δ| <= 6 %, considerando half/double time (70 <-> 140).
- Las transiciones incompatibles se permiten como tipo "corte" o "echo out", con penalización en el score.
- Energía de 0 a 1. Un set sigue una curva objetivo (warmup -> pico -> cierre).

## Restricciones de Spotify (IMPORTANTE)
- NO usar /audio-features, /audio-analysis, /recommendations ni /related-artists: devuelven 403 para apps nuevas.
- Las preview_url vienen en null. Nunca descargar audio de Spotify ni scrapear su web.
- Spotify solo aporta metadata de playlists. Todo el análisis de audio se hace sobre archivos locales.

## Comandos
- `uv sync` · `uv run pytest` · `uv run setlab --help`

## Convenciones
- Type hints en todo. Funciones puras en analysis/ y setgen/, fáciles de testear.
- Los tests de setgen usan tracks ficticios. No hace falta audio real.
- Credenciales solo en `.env` (está en .gitignore). Nunca commitear audio ni `.env`.

## Protocolo de sesión
1. Leer `PLAN.md` y `PROGRESS.md`.
2. Tomar la PRIMERA tarea sin marcar `[ ]`. Una sola tarea por sesión.
3. Implementarla con tests. No avanzar a otras tareas aunque "quede tiempo".
4. Correr `uv run pytest`. Si falla y no se puede arreglar, documentarlo como bloqueo.
5. Marcar `[x]` en PLAN.md, actualizar PROGRESS.md y hacer commit.
6. Terminar usando la skill `handoff`.
