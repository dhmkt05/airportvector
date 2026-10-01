# airportvector

**Every place on Earth, named from its nearest airport.**

```
TRZ-D04200355   →   5.5 km north-west of Tiruchirappalli airport (10 m square)
```

No dependencies, works offline, Node and browsers. 4,133 commercial airports (IATA) cover the whole globe.
Try it live at **[airportvector.org](https://airportvector.org)**.

## Install

```
npm install airportvector
```

## Use

```js
import av from "airportvector";            // or: const av = require("airportvector");

av.encode(10.7950461, 78.679302);           // "TRZ-D04200355"   nearest airport, 10 m
av.encode(10.7950461, 78.679302, "1m");     // "TRZ-D0420303554"
av.decode("TRZ-D04200355");                 // { lat: 10.79505…, lon: 78.67929… }  cell centre
av.describe("TRZ-D04200355");               // "5.5 km NW of TRZ (Tiruchirappalli International Airport)"
av.distanceFromAnchorM("TRZ-D04200355");    // 5506.4  exact metres to the airport
av.move("TRZ-D04200355", 50, 0);            // "TRZ-D03700355"   500 m East
av.shorten("TRZ-D0420303554", "100m");      // "TRZ-D042035"
av.parse("trz-d0420.0355");                 // { anchor: "TRZ", sector: "D", band: 0, x: 420, y: 355, … }
```

Named imports work too: `import { encode, decode } from "airportvector"`. TypeScript types are included.

### Smaller browser bundle

The main entry bundles the airport list (~230 KB, ~100 KB gzipped). To load it yourself instead:

```js
import av from "airportvector/core";
av.loadRegistry(await (await fetch("https://airportvector.org/anchors.json")).json());
```

(`airportvector` and `airportvector/core` share one airport list — use one or the other in an app.)

### Plain `<script>` tag

```html
<script src="https://cdn.jsdelivr.net/npm/airportvector@2.1.1/oavg.js"></script>
<script>
  OAVG.loadRegistry(await (await fetch("https://cdn.jsdelivr.net/npm/airportvector@2.1.1/anchors.json")).json());
  OAVG.encode(51.5074, -0.1278);  // "LCY-D12710024"
</script>
```

## Reading a code

| Letter | Direction | Distance from airport | Digits per axis |
|---|---|---|---|
| A B C D | NE SE SW NW | under 100 km | normal |
| E F G H | NE SE SW NW | 100 – 999 km | +1 |
| I J K L | NE SE SW NW | 1,000 – 9,999 km | +2 |

Precision: `"1km"`, `"100m"`, `"10m"` (default) or `"1m"`. √(X² + Y²) is the exact ground distance to the airport.

Results match the Python package (`pip install airportvector`) exactly — both are tested against the same vectors.

## Links

- Live map & logistics zone calculator: <https://airportvector.org> · <https://airportvector.org/logistics>
- Specification v2.1: <https://airportvector.org/spec-v2.1.pdf>
- Source: <https://github.com/dhmkt05/airportvector>

## Status & license

Draft specification v2.1 — airport coordinates are being verified against official sources.
Not for navigation, aviation or emergency-services use.

Source-available under the **Business Source License 1.1** (see `LICENSE.md`): free for development,
non-commercial use and internal deployment; offering a paid hosted API/SaaS to third parties is not permitted.
Converts to Apache 2.0 on 1 October 2029.
