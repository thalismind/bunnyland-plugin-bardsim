# Bunnyland Bardsim

Out-of-tree [Bunnyland](https://github.com/thalismind/bunnyland-server) plugin: an expansion-pack-sized **music & performance** pack. Characters pick up instruments, play
songs they know, fill the room with an audible tune, lift (or sink) the mood of everyone
listening, and — when there is an audience — earn tips.

**v2** adds the *venues, gigs & reputation* headline: open a room as a named venue, play a
**gig** there to build a shared **reputation** (renown), form **ensembles** (a typed
`BandmateOf` edge so a band draws more renown than a lone busker), and **compose** original
songs you own (a typed `Composed` edge) and can perform at once.

Everything reuses the stock server's own subsystems: performances become **noise** the core
hearing pipeline delivers, mood changes flow through **`AffectComponent`**, tips scale with
each listener's **`SocialBond`**, the become-renowned ambition rides the core persona/goals
`GoalComponent`, a famous act registers a core **storyteller** incident, and worldgen tagging
happens through the standard generation-event hooks. Synergy partners (festival, museum,
storyteller) are **recommended, never required** — bardsim runs standalone.

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
  with `InstrumentComponent`, and gives a generated musician the become-renowned goal.
- `spawn_lute`, `spawn_fiddle`, `spawn_drum`, `spawn_musician` - spawn factories.

### v2 surfaces

- `VenueComponent` - marks a room as a performance venue with a name and prestige tier (1-5).
- `GigComponent` / `GigConsequence` - a gig seeds a scored performance; the consequence grants
  renown (scaled by venue prestige, crowd size, and ensemble), publishes a `ContestEntry`, and
  registers a storyteller incident when a performer becomes famous — each gig scored once.
- `CompositionComponent` / `Composed` (edge) - an original song, owned by its author.
- `BandmateOf` (edge) - a symmetric band-membership tie between two musicians.
- `Reputation` - the shared performing-standing connector surface (renown → unknown…renowned).
- `ContestEntryComponent` - a published gig entry a festival pack can host as a competition.
- `reputation_fragments` / `venue_fragments` / `ensemble_fragments` / `composition_fragments`.

### Verbs

- `perform` - play a known song on a held instrument, filling the room with an audible tune.
- `learn-song` - add a song to your repertoire.
- `open-venue` - turn the room you are in into a named performance venue (prestige 1-5).
- `perform-gig` - play a known song at a venue to build your reputation.
- `form-ensemble` - band together with another musician under a shared ensemble name.
- `compose-song` - write an original song, learn it, and add it to your body of work.

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
