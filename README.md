# AirportVector

**Every place on Earth, named from its nearest airport.**

```
TRZ-D04200355   →   5.5 km north-west of Tiruchirappalli airport (10 m square)
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
av.encode(10.7950461, 78.6793020)      # 'TRZ-D04200355'
av.describe("TRZ-D04200355")           # '5.5 km NW of TRZ (Tiruchirappalli International Airport)'
```

```js
import av from "airportvector";
av.encode(51.5074, -0.1278);           // "LCY-D12710024"
```

## How a code works

```
TRZ-D04200355
│   │└──┬┘└──┬┘
│   │   │    └── Y: 0355 cells North  (3,550 m)
│   │   └─────── X: 0420 cells West   (4,200 m)
│   └─────────── Letter D = North-West, near (under 100 km)
└─────────────── Nearest airport: TRZ (Tiruchirappalli)
```

| Letter | Direction | Distance from airport | Digits per axis |
|---|---|---|---|
| A B C D | NE SE SW NW | under 100 km | normal |
| E F G H | NE SE SW NW | 100 – 999 km | +1 |
| I J K L | NE SE SW NW | 1,000 – 9,999 km | +2 |

Precision: 1 km, 100 m, 10 m (default) or 1 m. √(X² + Y²) is the exact ground distance to the airport.
Full specification: [docs/spec-v2.1.pdf](docs/spec-v2.1.pdf).

## Repository layout

```
python/   Python package (source of truth for the airport registry: python/src/airportvector/anchors.csv)
js/       JavaScript package (js/build.mjs generates the entry points and anchors.json from the CSV)
docs/     Specification
```

Run all tests:

```
pip install ./python pytest pyproj && pytest python/tests
cd js && node build.mjs && npm test
```

## Status & license

Draft specification v2.1 — airport coordinates are being verified against official sources.
Not for navigation, aviation or emergency-services use.

Source-available under the **Business Source License 1.1** — see [LICENSE.md](LICENSE.md):
free for development, non-commercial use and internal deployment; offering a paid hosted API/SaaS
to third parties is not permitted. Converts to Apache 2.0 on 1 October 2029.
