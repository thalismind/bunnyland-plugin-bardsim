# Bunnyland Bardsim

Out-of-tree [Bunnyland](https://github.com/thalismind/bunnyland-server) plugin: a
Sims-4-expansion-sized **music & performance** pack. Characters pick up instruments, play
songs they know, fill the room with an audible tune, lift (or sink) the mood of everyone
listening, and — when there is an audience — earn tips.

Everything reuses the stock server's own subsystems: performances become **noise** the core
hearing pipeline delivers, mood changes flow through **`AffectComponent`**, tips scale with
each listener's **`SocialBond`**, and worldgen tagging happens through the standard
generation-event hooks.

This repo intentionally keeps all bard work outside the main `bunnyland-server` repo.

## Layout

- `server/` - Python Bunnyland plugin package with the instrument/repertoire/tip
  components, the `perform` and `learn-song` verbs, the performance consequence (mood +
  busking), prompt fragments, a worldgen enrichment hook, spawn factories, and tests.

## Server Plugin

The plugin exposes `bunnyland_bardsim.bunnyland_plugins()` and contributes:

- `InstrumentComponent` - portable, holdable instruments (lute, fiddle, drum…).
- `RepertoireComponent` - the songs a character knows and can perform.
- `TipJarComponent` - a simple coin counter buskers accrue tips into.
- `PerformanceNoiseComponent` - marks the short-lived noise entity a performance spawns.
- `PerformanceConsequence` - once per performance, shifts the mood of everyone listening in
  the room and pays the performer tips scaled by audience size and social bond.
- `bardsim_fragments` - renders what is currently playing in the room, nearby instruments,
  and (first person) your own repertoire.
- `BardWorldgenHook` - tags generated musicians with a repertoire and generated instruments
  with `InstrumentComponent`.
- `perform` and `learn-song` - verbs for the holder (human or AI).
- `spawn_lute`, `spawn_fiddle`, `spawn_drum`, `spawn_musician` - spawn factories.

## Running

This package builds no containers. It is loaded into the stock server via `--module`:

```bash
bunnyland serve --module bunnyland_bardsim
```

`default_enabled=True`, so no `--plugin` flag is required once the module is imported. The
`bunnyland_bardsim` package must be importable by the server (installed into the server's
environment, or on `PYTHONPATH`).

## Development

Run server tests against a sibling `bunnyland-server` checkout (no install required —
`server/tests/conftest.py` puts both packages on `sys.path`). From `server/`:

```bash
uv run --project ../../bunnyland-server -m pytest
uv run --project ../../bunnyland-server ruff check src tests
```

See [`server/README.md`](server/README.md) for more detail.

## Contributing & Conduct

This plugin follows the Bunnyland project's
[contribution guidelines](CONTRIBUTING.md) and [code of conduct](CODE_OF_CONDUCT.md),
which point back to the `bunnyland-server` repository.

## License

Licensed under the GNU Affero General Public License v3.0. See [LICENSE](LICENSE).
