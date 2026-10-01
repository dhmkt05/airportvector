# AirportVector

**Every place on Earth, named from its nearest airport.**

```
TRZ 55511 79566   →   5.5 km north-west of Tiruchirappalli airport (4 m square)
```

Try it live: **[airportvector.org](https://airportvector.org)** · For couriers: **[airportvector.org/logistics](https://airportvector.org/logistics)**

## Install

| Language | Install | Docs |
|---|---|---|
| Python 3.9+ | `pip install airportvector` | [python/README.md](python/README.md) |
| JavaScript / TypeScript (Node, browsers) | `npm install airportvector` | [js/README.md](js/README.md) |

Both are dependency-free, work offline, ship the same 4,133-airport registry and are tested to give identical results.

```python
import airportvector as av
av.encode(10.7950461, 78.6793020)      # 'TRZ-55511-79566'
av.describe("TRZ 55511 79566")         # '5.5 km NW of TRZ (Tiruchirappalli International Airport)'
```

```js
import av from "airportvector";
av.encode(51.5074, -0.1278);           // "LCY-55444-38173"
```

## How a code works

Every square splits 3 × 3, named like a phone keypad. `5` is always the part with the airport.

```
1 2 3      NW  N  NE
4 5 6  =   W   ●   E
7 8 9      SW  S  SE
```

```
TRZ 55511 79566
│   └─┬─┘ └─┬─┘
│     │     └── Second group: the spot inside that square (333 m → 111 m → 37 m → 12 m → 4 m)
│     └──────── First group: the 1 km square (81 → 27 → 9 → 3 → 1 km), three 5s = within 4.5 km
└────────────── Nearest airport: TRZ (Tiruchirappalli)
```

- Count the leading 5s for distance: `5` within 40 km, `55` 13.5 km, `555` 4.5 km, `5555` 1.5 km.
- Places over 121 km from their airport get a longer first group (leading 5s are implied).
- Any start of a code is a square, so area search is a prefix search.
- Written `TRZ 55511 79566` for people and `TRZ-55511-79566` in links.

Full specification: [docs/SPEC-v4.md](docs/SPEC-v4.md).

## Repository layout

```
python/   Python package (source of truth for the airport registry: python/src/airportvector/anchors.csv)
js/       JavaScript package (js/build.mjs generates the entry points and anchors.json from the CSV)
docs/     Specification (SPEC-v4.md; spec-v2.1.pdf kept for history)
```

Run all tests:

```
pip install ./python pytest pyproj && pytest python/tests
cd js && node build.mjs && npm test
```

## Status & license

Draft specification v4 — airport coordinates are being verified against official sources.
Not for navigation, aviation or emergency-services use.

Source-available under the **Business Source License 1.1** — see [LICENSE.md](LICENSE.md):
free for development, non-commercial use and internal deployment; offering a paid hosted API/SaaS
to third parties is not permitted. Converts to Apache 2.0 on 1 October 2029.
