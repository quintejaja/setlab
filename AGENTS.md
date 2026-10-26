# Setlab — generador de sets para DJ

## Qué es
Herramienta local que toma una playlist de Spotify (mía o pública de otro usuario), consigue las
características de cada tema (BPM, key, energía, danceability, género), descubre temas nuevos parecidos
y arma una setlist ordenada que se guarda como playlist en mi Spotify.
Dos modos: **playlist** (ordena solo los temas de la playlist) y **descubrir** (mezcla la playlist con temas nuevos parecidos).
Estilo open format: trap, reggaetón, RKT, tech/house. Controladora: Pioneer DDJ-FLX4.

## Stack
- Python 3.12 + uv · SQLite (archivo local) · pytest
- spotipy (Spotify Web API, OAuth PKCE) · httpx (Last.fm, Deezer, GetSongBPM) · rapidfuzz (matching por nombre)
- librosa (BPM, key, energía, danceability sobre previews de 30 s). essentia no tiene wheels para Windows: no usarlo.
- UI: web local (servidor en 127.0.0.1) leyendo la misma SQLite
- Todo gratis y local. Prohibido agregar servicios pagos o nube.

## Arquitectura
```
src/setlab/
  db/                   # schema.sql + acceso a SQLite
  sources/spotify.py    # leer playlists, buscar tracks, crear la playlist final
  sources/lastfm.py     # temas y artistas similares, tags de género
  sources/deezer.py     # buscar track (ISRC) + preview de 30 s, artistas relacionados
  sources/getsongbpm.py # BPM y key por metadata
  analysis/             # key->Camelot, análisis de previews con librosa, combinación de fuentes
  discover.py           # candidatos parecidos a una playlist + ranking por features
  setgen/graph.py       # grafo de compatibilidad
  setgen/search.py      # búsqueda del set (beam search + curva de energía)
  export/spotify.py     # guarda la setlist como playlist en Spotify
  cli.py                # punto de entrada (typer)
```
El esquema de la DB (`src/setlab/db/schema.sql`) es el contrato entre módulos.
Si una tarea necesita cambiarlo, documentar el cambio en PROGRESS.md.

## Fuentes de features (cuál usar para qué)
- **BPM y key:** primero GetSongBPM (rápido, sin descargar nada). Si no tiene el tema, librosa sobre el preview de Deezer.
- **Energía y danceability:** librosa sobre el preview de Deezer (GetSongBPM no las tiene). Son estimaciones propias (ver `analysis/audio.py`), no las de Spotify.
- **Género:** tags de Last.fm. El campo `bounce` (1–5) es manual.
- Si GetSongBPM y librosa discrepan en BPM por half/double time, se guarda el valor más cercano a 100–150 y se registra la fuente.
- Los previews se bajan a una carpeta temporal y se borran apenas se analizan. Nunca se guarda audio.
- Todo resultado de una API se cachea en la DB: no volver a pedir lo que ya está.

## Reglas de dominio
- Key en notación Camelot (1A–12B). Compatibles: misma key, ±1 número con la misma letra, y cambio A<->B con el mismo número.
- BPM: compatible si |Δ| <= 6 %, considerando half/double time (70 <-> 140).
- Las transiciones incompatibles se permiten como tipo "corte" o "echo out", con penalización en el score.
- Energía de 0 a 1. Un set sigue una curva objetivo (warmup -> pico -> cierre).

## Restricciones de Spotify (IMPORTANTE)
- Solo se usa la API oficial. Prohibido scrapear la web de Spotify o descargar audio de Spotify.
- NO usar /audio-features, /audio-analysis, /recommendations ni /related-artists: devuelven 403 para apps nuevas.
- Sí se puede: leer playlists propias y públicas de usuarios, buscar tracks, crear y llenar playlists en mi cuenta.
- Las playlists editoriales de Spotify (creadas por Spotify) no se pueden leer: mostrar un error claro.

## Comandos
- `uv sync` · `uv run pytest` · `uv run setlab --help`

## Convenciones
- Type hints en todo. Funciones puras en analysis/, discover.py y setgen/, fáciles de testear.
- Los tests nunca llaman a APIs reales: usar respuestas mockeadas y tracks ficticios.
- Credenciales solo en `.env` (está en .gitignore): `SPOTIFY_CLIENT_ID`, `LASTFM_API_KEY`, `GETSONGBPM_API_KEY`. Nunca commitear audio ni `.env`.

## Protocolo de sesión
1. Leer `PLAN.md` y `PROGRESS.md`.
2. Tomar la PRIMERA tarea sin marcar `[ ]`. Una sola tarea por sesión, salvo que el humano pida
   una tanda de varias: en ese caso, solo tareas cuyas dependencias ya estén hechas, y un commit por tarea.
3. Implementarla con tests. No avanzar a otras tareas aunque "quede tiempo".
4. Correr `uv run pytest`. Si falla y no se puede arreglar, documentarlo como bloqueo.
5. Marcar `[x]` en PLAN.md, actualizar PROGRESS.md y hacer commit.
6. Terminar usando la skill `handoff`.
