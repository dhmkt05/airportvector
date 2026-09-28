# Changelog

## 2.0.0 — 2026-09-28
Implements OAVG spec v2.0 (`docs/spec-v2.pdf`). **Breaking:** v1 codes are not compatible.

### Fixed
- Codes could only reach 999 m from the airport; now every precision reaches 99,999 m.
- Code length meant different cell sizes in the code vs. the spec; now 4/6/8/10 digits = 1 km/100 m/10 m/1 m.
- Rounding could create a code with too many digits; now always truncates.
- Flat "× 111,000" maths was off by ~250 m at 80 km; now uses Transverse Mercator on WGS84 (matches PROJ to < 1 mm).
- Decode returned the cell corner; now returns the cell centre.
- Parser accepted malformed codes; now fully validated with clear errors.

### Added
- Automatic nearest-airport selection; optional `anchor=` for alternate codes.
- `move()` (handles sector crossings), `shorten()`, `parse()`, `bounds()`, `normalize()`.
- Anchor registry moved to `anchors.csv` with status and verification columns.
- Command-line interface.
- Test suite with the spec's conformance vectors.

## 1.0.0
- Initial prototype.
