# Setlab

Generador de sets para DJ: toma una playlist de Spotify, analiza cada tema (BPM, key en Camelot,
energía, danceability, género), descubre temas parecidos y arma una setlist ordenada que se guarda
como playlist en tu Spotify. Pensado para open format (trap, reggaetón, RKT, tech/house).

> Proyecto personal en desarrollo. Ver [PLAN.md](PLAN.md) y [PROGRESS.md](PROGRESS.md).

## Uso

```sh
uv sync
cp .env.example .env   # completar las keys
uv run setlab playlist import <link de la playlist>
uv run setlab audio --playlist <nombre o link>
```

## Seguridad

- Las credenciales van solo en `.env`, que está en `.gitignore`. Nunca se commitean.
- El hook `.githooks/pre-commit` bloquea commits con `.env`, la base local, tokens o audio.
  Activalo una vez con `git config core.hooksPath .githooks`.
- Spotify se usa solo por su API oficial con OAuth PKCE (sin client secret).
- Los previews de audio se analizan en un archivo temporal y se borran al instante.

## Créditos

- BPM data provided by [GetSongBPM](https://getsongbpm.com).
- Metadata de [Last.fm](https://www.last.fm) y [Deezer](https://www.deezer.com).
