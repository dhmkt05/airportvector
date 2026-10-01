# airportvector

**Every place on Earth, named from its nearest airport.**

```
TRZ-D04200355   →   5.5 km north-west of Tiruchirappalli airport (10 m square)
```

Pure Python, **no dependencies**, works offline. 4,133 commercial airports (IATA) cover the whole globe.
Try it live at **[airportvector.org](https://airportvector.org)**.

## Install

```
pip install airportvector
```

## Use

```python
import airportvector as av

av.encode(10.7950461, 78.6793020)          # 'TRZ-D04200355'   (nearest airport, 10 m)
av.encode(10.7950461, 78.6793020, "1m")    # 'TRZ-D0420303554'
av.decode("TRZ-D04200355")                 # (10.795052, 78.679291)   cell centre
av.describe("TRZ-D04200355")               # '5.5 km NW of TRZ (Tiruchirappalli International Airport)'
av.distance_from_anchor_m("TRZ-D04200355") # 5506.4  exact metres to the airport
av.distance("TRZ-D04200355", "LCY-D12710024")  # 8301811  metres between two codes
av.move("TRZ-D04200355", east_cells=50)    # 'TRZ-D03700355'   500 m East
av.shorten("TRZ-D0420303554", "100m")      # 'TRZ-D042035'
av.parse("trz-d0420.0355")                 # OAVGCode(anchor='TRZ', sector='D', band=0, x=420, y=355, base=4)
av.cell_polygon("TRZ-D04200355")           # 4 corners as (lat, lon)
```

Command line:

```
airportvector encode 10.7950461 78.6793020 10m
airportvector decode TRZ-D04200355
```

## Reading a code

| Letter | Direction | Distance from airport | Digits per axis |
|---|---|---|---|
| A B C D | NE SE SW NW | under 100 km | normal |
| E F G H | NE SE SW NW | 100 – 999 km | +1 |
| I J K L | NE SE SW NW | 1,000 – 9,999 km | +2 |

Precision: 1 km, 100 m, 10 m (default) or 1 m. √(X² + Y²) is the exact ground distance to the airport.

## Links

- Live map & zone calculator: <https://airportvector.org> · <https://airportvector.org/logistics>
- Specification v2.1: <https://airportvector.org/spec-v2.1.pdf>
- JavaScript version: `npm install airportvector`
- Source: <https://github.com/dhmkt05/airportvector>

## Status & license

Draft specification v2.1 — airport coordinates are being verified against official sources.
Not for navigation, aviation or emergency-services use.

Source-available under the **Business Source License 1.1** (see `LICENSE.md`): free for development,
non-commercial use and internal deployment; offering a paid hosted API/SaaS to third parties is not permitted.
Converts to Apache 2.0 on 1 October 2029.
