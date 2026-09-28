# airportvector
An open, human-readable coordinate-to-grid protocol anchored to global airports.
Reference implementation of the **Open Airport Vector Grid (OAVG) v2.1** — full spec in [`docs/spec-v2.1.pdf`](docs/spec-v2.1.pdf).

**Every point on Earth gets a code from its nearest commercial airport.**

```
TRZ-D04200355
│   │└──┬┘└──┬┘
│   │   │    └── Y: 0355 cells North  (3,550 m)
│   │   └─────── X: 0420 cells West   (4,200 m)
│   └─────────── Letter D = North-West, near (under 100 km)
└─────────────── Anchor: TRZ (Tiruchirappalli airport)
```

Read it as: *"about 5.5 km north-west of Trichy airport, 10 m square."*

## The letter = direction + distance band

| | North-East | South-East | South-West | North-West | Digits per axis |
|---|---|---|---|---|---|
| **Near** (under 100 km) | A | B | C | D | normal |
| **Regional** (100–999 km) | E | F | G | H | +1 |
| **Far** (1,000–9,999 km) | I | J | K | L | +2 |

Rule of thumb: **every 4 letters = 10× further**. The farthest any place on Earth gets from its nearest commercial airport is about 5,150 km (inside Antarctica), so A–L covers the whole globe.

Examples (10 m precision):

| Place | Code | Meaning |
|---|---|---|
| Near Trichy bus stand | `TRZ-D04200355` | 5.5 km NW of Trichy airport |
| Central London | `LCY-D12710024` | 13 km W of London City airport |
| Sahara | `DJG-F2590508465` | 273 km ESE of Djanet airport |
| Point Nemo (Pacific) | `IPC-K104561248302` | 2,694 km SSW of Easter Island airport |

## Precision

| Base digits per axis | Cell size | Near example |
|---|---|---|
| 2 + 2 | 1 km | `TRZ-D0403` |
| 3 + 3 | 100 m | `TRZ-D042035` |
| 4 + 4 | 10 m (default) | `TRZ-D04200355` |
| 5 + 5 | 1 m | `TRZ-D0420303554` |

- Regional codes add 1 digit per axis, far codes add 2.
- Digits are **truncated**, so a short code is always the start of a longer one.
- A dot may be added for reading: `TRZ-D0420.0355`.
- √(X² + Y²) is the **exact** ground distance to the airport.

## Install & use

Pure Python 3.9+, **no dependencies**, works offline. Copy `airportvector.py` and `anchors.csv` into your project.

```python
import airportvector as av

av.encode(10.7950461, 78.6793020)              # 'TRZ-D04200355'  (nearest airport, 10 m)
av.encode(10.7950461, 78.6793020, "1m")        # 'TRZ-D0420303554'
av.decode("TRZ-D04200355")                     # (10.795052, 78.679291)  centre of the cell
av.describe("TRZ-D04200355")                   # '5.5 km NW of TRZ (Tiruchirappalli International Airport)'
av.distance("TRZ-D04200355", "TRZ-D04200405")  # 500.0  metres between two codes
av.move("TRZ-D04200355", east_cells=50)        # 'TRZ-D03700355'  500 m East
av.shorten("TRZ-D0420303554", "100m")          # 'TRZ-D042035'
```

Command line:

```
python airportvector.py encode 10.7950461 78.6793020 10m
python airportvector.py decode TRZ-D04200355
```

## Anchor registry

[`anchors.csv`](anchors.csv) holds 4,133 commercial airports (IATA code, scheduled service), seeded from [OurAirports](https://github.com/davidmegginson/ourairports-data) open data. Rules (spec Section 2):

- Coordinates are **frozen** once published — never edit a lat/lon, or every existing code for that airport moves.
- Closed airports stay in the file with `status = retired` (they still decode).
- A code is never re-pointed to a different airport.
- `verified = no` means the coordinates have not yet been checked against the official Aerodrome Reference Point. **Verify before a public launch.**

## Run the tests

```
pip install -r requirements-dev.txt
pytest
```

Includes every conformance vector from the spec and cross-checks the projection against PROJ (`pyproj`).

## Version history

See [CHANGELOG.md](CHANGELOG.md).

## Licensing & Commercial Use
AirportVector is source-available under the **Business Source License 1.1**.
* **For Developers & Hobbyists:** It is 100% free to use, modify, and build into your own apps.
* **For Commercial Enterprise:** You cannot wrap this code into a paid, hosted API service to compete with the official network.
