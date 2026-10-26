# PLAN

Cada tarea tiene un criterio de "terminado". Una tarea = una sesión.

## Fase 0 — Esqueleto
- [x] 0.1 Proyecto uv, estructura de carpetas de AGENTS.md, pytest andando, CLI vacía con typer. ✔ `uv run setlab --help` funciona.
- [ ] 0.2 `schema.sql` + módulo db (tracks_spotify, tracks_local, features, matches). ✔ test que crea la DB en memoria.

## Fase 1 — Biblioteca local
- [ ] 1.1 Escanear carpeta de audio (mp3/wav/flac/aiff) y leer tags con mutagen. ✔ `setlab scan <carpeta>` llena tracks_local.
- [ ] 1.2 Importar BPM/key de un XML de rekordbox si existe. ✔ test con un XML de ejemplo.

## Fase 2 — Análisis
- [ ] 2.1 BPM y key con essentia + conversión a Camelot. ✔ tests de la conversión key->Camelot.
- [ ] 2.2 Energía y danceability. Cache por hash del archivo. ✔ re-analizar no recalcula.
- [ ] 2.3 Género: modelo de essentia o tag manual. Campo `bounce` manual (1–5). ✔ `setlab tag` para editarlo.

## Fase 3 — Spotify
- [ ] 3.1 OAuth PKCE + leer mis playlists a tracks_spotify. ✔ `setlab spotify sync`.
- [ ] 3.2 Matching fuzzy spotify<->local + reporte de los que faltan. ✔ `setlab match` lista los no encontrados.

## Fase 4 — Generador de sets
- [ ] 4.1 Función de compatibilidad entre dos tracks (score + tipo de transición). ✔ tests de casos Camelot/BPM/half-time.
- [ ] 4.2 Grafo de compatibilidad. ✔ test con 10 tracks ficticios.
- [ ] 4.3 Beam search con curva de energía objetivo y duración. ✔ `setlab build --playlist X --minutos 60`.

## Fase 5 — Export
- [ ] 5.1 Export a XML de rekordbox + M3U. ✔ el XML se importa en rekordbox.
- [ ] 5.2 Reporte del set: tabla con BPM, key y tipo de cada transición.

## Fase 6 — Opcional
- [ ] 6.1 UI (web local o Avalonia leyendo la misma SQLite).
