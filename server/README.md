# bunnyland-bardsim (server plugin)

The out-of-tree Bunnyland plugin package `bunnyland_bardsim`.

## Development

Tests run against a sibling `bunnyland-server` checkout without installing anything —
`tests/conftest.py` puts both this package's `src/` and `../bunnyland-server/src` on
`sys.path`. From this `server/` directory:

```bash
# uses the sibling bunnyland-server's virtualenv/deps
uv run --project ../../bunnyland-server -m pytest
# or, if bunnyland + relics are already importable:
python -m pytest
```

Lint:

```bash
uv run ruff check src tests
```

## Loading into the server

```bash
bunnyland serve --module bunnyland_bardsim
```

`default_enabled=True`, so no `--plugin` flag is required once the module is imported.

## What it contributes

- **Components** — `InstrumentComponent` (portable instruments), `RepertoireComponent`
  (songs a character knows), `TipJarComponent` (a coin counter), and
  `PerformanceNoiseComponent` (marks the noise entity a performance spawns).
- **A performance consequence** that, once per performance, shifts the mood of every
  listener in the room through `AffectComponent` and pays the performer tips scaled by
  audience size and each listener's `SocialBond`.
- **Prompt fragments** rendering what is currently playing in the room, nearby
  instruments, and (first person) your own repertoire.
- **A worldgen hook** tagging generated musicians with a repertoire and generated
  instruments with `InstrumentComponent`.
- **Two verbs** — `perform` (play a known song on a held instrument) and `learn-song`
  (add a song to your repertoire).
- **Spawn factories** — `spawn_lute`, `spawn_fiddle`, `spawn_drum`, `spawn_musician`.
