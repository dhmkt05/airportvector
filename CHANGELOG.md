# Changelog

## 2.1.0 — 2026-09-28
Implements OAVG spec v2.1 (`docs/spec-v2.1.pdf`). **Global coverage.** Codes differ from 2.0.

### Changed
- **Every point on Earth** is now coded from its nearest commercial airport — no gaps, no fallbacks.
- Sector letters A–L: direction + distance band (A–D near < 100 km, E–H regional < 1,000 km, I–L far < 10,000 km). Each band adds one digit per axis.
- Projection: Azimuthal Equidistant on WGS84 (Vincenty), replacing Transverse Mercator. Works globally, and √(X² + Y²) is the exact distance to the airport. Matches PROJ to 0.1 mm.
- Registry: 4,133 commercial IATA airports seeded from OurAirports (was 3). Anchor coordinates changed (e.g. TRZ now 10.762915, 78.717741).
- Removed ICAO and Plus Code fallbacks from the spec (no longer needed).

### Added
- `describe()` — plain-language reading, e.g. "5.5 km NW of TRZ".
- `distance()` between any two codes, `distance_from_anchor_m()`.
- `move()` now also crosses band edges.
- Parser rejects codes placed in the wrong band.

## 2.0.0 — 2026-09-28
- Spec-compliant rewrite: full 80 km zone, Transverse Mercator projection, truncation, sector-crossing rule, validation, registry file, tests.

## 1.0.0
- Initial prototype.
