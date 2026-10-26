# PLAN

Cada tarea tiene un criterio de "terminado". Una tarea = una sesión.

## Fase 0 — Esqueleto
- [x] 0.1 Proyecto uv, estructura de carpetas de AGENTS.md, pytest andando, CLI vacía con typer. ✔ `uv run setlab --help` funciona.
- [x] 0.2 `schema.sql` + módulo db (tracks, playlists, playlist_tracks, features, candidates). ✔ test que crea la DB en memoria.

## Fase 1 — Spotify (entrada)
- [ ] 1.1 OAuth PKCE + importar una playlist (mía o pública, por link o id) a la DB. Error claro si es editorial. ✔ `setlab playlist import <link>`.
- [ ] 1.2 Buscar un tema en Spotify por ISRC o artista+título (fuzzy con rapidfuzz). ✔ tests con respuestas mockeadas.

## Fase 2 — Features
- [ ] 2.1 Conversión key->Camelot + cliente GetSongBPM (BPM, key). ✔ tests de la conversión y del cliente mockeado.
- [ ] 2.2 Deezer: encontrar el tema (ISRC), bajar el preview, analizar con essentia (BPM, key, energía, danceability) y borrarlo. Cache en DB. ✔ re-analizar no recalcula.
- [ ] 2.3 Combinar fuentes según AGENTS.md + género por tags de Last.fm + `bounce` manual. ✔ `setlab analyze --playlist X` y `setlab tag`.

## Fase 3 — Descubrir temas nuevos
- [ ] 3.1 Candidatos: temas similares de Last.fm + top tracks de artistas relacionados (Last.fm/Deezer). ✔ `setlab discover --playlist X` guarda candidatos.
- [ ] 3.2 Rankear candidatos por parecido con la playlist (BPM, energía, género). ✔ tests con tracks ficticios.

## Fase 4 — Generador de sets
- [ ] 4.1 Función de compatibilidad entre dos tracks (score + tipo de transición). ✔ tests de casos Camelot/BPM/half-time.
- [ ] 4.2 Grafo de compatibilidad. ✔ test con 10 tracks ficticios.
- [ ] 4.3 Beam search con curva de energía objetivo y duración, modos `playlist` y `descubrir`. ✔ `setlab build --playlist X --minutos 60 --modo descubrir`.

## Fase 5 — Export
- [ ] 5.1 Guardar la setlist como playlist nueva en mi Spotify. ✔ `setlab build ... ` crea la playlist y muestra el link.

## Fase 6 — Opcional
- [ ] 6.1 UI (web local o Avalonia leyendo la misma SQLite).
