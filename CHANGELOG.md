# Changelog

## 4.0.0 — 2026-10-01
New code format (OAVG v4). **Breaking: v2.1 codes such as `TRZ-D04200355` are no longer accepted.**

### Changed
- Codes use a phone-keypad grid centred on the airport: every square splits 3 × 3, digits 1–9 follow
  the keypad (1 NW … 5 centre … 9 SE). `TRZ 55511 79566` = 1 km square + spot inside it (about 4 m).
- Written with spaces for people (`TRZ 55511 79566`) and hyphens in links (`TRZ-55511-79566`).
  Input accepts spaces, hyphens, dots or no separator.
- Precisions are now `1km`, `333m`, `111m`, `37m`, `12m` and `4m` (default).
- Places over 121 km from their airport get a longer first group (6–9 digits, leading 5s implied).
- `parse()` returns `coarse`, `fine`, `extra`, `levels`, `leading_fives` (JS: `leadingFives`) instead of sector/band fields.

### Added
- `neighbors()` — the 8 cells around a code, for nearby search across grid lines.
- `display()` — the spaced form for people.
- Specification: `docs/SPEC-v4.md`.

### Unchanged
- Nearest-airport rule, WGS84 Azimuthal Equidistant projection, 4,133-airport registry.

## 2.1.1 — 2026-09-29
First release as installable packages: `pip install airportvector` and `npm install airportvector`.

### Fixed (from QC)
- Poles now get one code regardless of the longitude supplied.
- Points on the far side of the Earth give a clear "out of range" error; `distance()` no longer fails for nearly antipodal pairs.
- Parser accepts only ASCII (A–Z, 0–9, `-`, `.`), so each place has exactly one way to be written.
- Registry rows are validated (status, coordinate range, non-empty name).
- Bad input types raise `OAVGError`; `move()` requires whole numbers; CLI rejects extra arguments.
- `bounds()` replaced by `cell_polygon()` (4 grid corners).

### Added
- JavaScript/TypeScript package with CommonJS, ESM, type definitions and a browser `<script>` build.
- `airportvector` command-line tool.
- GitHub Actions: tests on Python 3.9/3.12 and Node 18/22 on every push.

### Changed
- Repository split into `python/` and `js/`; the JS airport list is generated from the Python CSV.

## 2.1.0 — 2026-09-28
- Global coverage from the nearest commercial airport; letters A–L show direction + distance band.
- Azimuthal Equidistant projection on WGS84 (exact distance to the airport).
- Registry of 4,133 IATA airports from OurAirports.

## 2.0.0 — 2026-09-28
- Spec-compliant rewrite with Transverse Mercator projection, truncation, tests.

## 1.0.0
- Initial prototype.
