# airportvector
An open, human-readable coordinate-to-grid protocol anchored to global airports.
Reference implementation of the **Open Airport Vector Grid (OAVG) v2.0** — full spec in [`docs/spec-v2.pdf`](docs/spec-v2.pdf).

```
TRZ-D03320331
│   │└──┬┘└──┬┘
│   │   │    └── Y: 0331 cells North  (3,310 m)
│   │   └─────── X: 0332 cells West   (3,320 m)
│   └─────────── Sector D = North-West of the airport
└─────────────── Anchor: TRZ (Tiruchirappalli airport)
```

Read it as: *"about 3.3 km north-west of Trichy airport, 10 m square."*

## How codes work

| Sector | Direction | X means | Y means |
|---|---|---|---|
| A | North-East | metres East | metres North |
| B | South-East | metres East | metres South |
| C | South-West | metres West | metres South |
| D | North-West | metres West | metres North |

Precision is set by the number of digits (X and Y always the same length):

| Digits | Cell size | Example |
|---|---|---|
| 2 + 2 | 1 km | `TRZ-D0303` |
| 3 + 3 | 100 m | `TRZ-D033033` |
| 4 + 4 | 10 m (default) | `TRZ-D03320331` |
| 5 + 5 | 1 m | `TRZ-D0332403312` |

- Every level reaches up to 99,999 m from the airport (the nominal zone is 50 miles / 80 km).
- Digits are **truncated**, so a short code is always the start of a longer one.
- A dot may be added for reading: `TRZ-D0332.0331`.

## Install & use

Pure Python 3.9+, **no dependencies**, works offline. Copy `airportvector.py` and `anchors.csv` into your project.

```python
import airportvector as av

av.encode(10.7950461, 78.6793020)              # 'TRZ-D03320331'  (nearest airport, 10 m)
av.encode(10.7950461, 78.6793020, "1m")        # 'TRZ-D0332403312'
av.decode("TRZ-D03320331")                     # (10.795068, 78.679296)  centre of the cell
av.move("TRZ-D03320331", east_cells=50)        # 'TRZ-D02820331'  500 m East
av.shorten("TRZ-D0332403312", "100m")          # 'TRZ-D033033'
av.parse("trz-d0332.0331")                     # OAVGCode(anchor='TRZ', sector='D', x=332, y=331, digits=4)
```

Command line:

```
python airportvector.py encode 10.7950461 78.6793020 10m
python airportvector.py decode TRZ-D03320331
```

## Anchor registry

Airports live in [`anchors.csv`](anchors.csv). Rules (spec Section 2):

- Coordinates are **frozen** once added — never edit a lat/lon, or every existing code for that airport moves.
- Closed airports stay in the file with `status = retired` (they still decode).
- A code is never re-pointed to a different airport.
- `verified = no` means the coordinates have not yet been checked against the official Aerodrome Reference Point.

## Run the tests

```
pip install -r requirements-dev.txt
pytest
```

The tests include every conformance vector from the spec and cross-check the projection maths against PROJ (`pyproj`).

## Version history

See [CHANGELOG.md](CHANGELOG.md). v2 codes are **not** compatible with v1.

## Licensing & Commercial Use
AirportVector is source-available under the **Business Source License 1.1**.
* **For Developers & Hobbyists:** It is 100% free to use, modify, and build into your own apps.
* **For Commercial Enterprise:** You cannot wrap this code into a paid, hosted API service to compete with the official network.
