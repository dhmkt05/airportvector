# airportvector

**Every place on Earth, named from its nearest airport.**

```
TRZ 55511 79566   →   5.5 km north-west of Tiruchirappalli airport (4 m square)
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

av.encode(10.7950461, 78.679302);           // "TRZ-55511-79566"   nearest airport, 4 m
av.encode(10.7950461, 78.679302, "1km");    // "TRZ-55511"
av.display("TRZ-55511-79566");              // "TRZ 55511 79566"   for people
av.decode("TRZ 55511 79566");               // { lat: 10.79506…, lon: 78.67928… }  cell centre
av.describe("TRZ-55511-79566");             // "5.5 km NW of TRZ (Tiruchirappalli International Airport)"
av.distanceFromAnchorM("TRZ-55511-79566");  // 5507.3  exact metres to the airport
av.move("TRZ-55511-79566", 1, 0);           // "TRZ-55511-79644"   one cell East
av.neighbors("TRZ-55511-79566");            // the 8 cells around it
av.shorten("TRZ-55511-79566", "37m");       // "TRZ-55511-795"
av.parse("trz 55511 79566");                // { anchor: "TRZ", coarse: "55511", fine: "79566", leadingFives: 3, … }
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
<script src="https://cdn.jsdelivr.net/npm/airportvector@4.0.0/oavg.js"></script>
<script>
  OAVG.loadRegistry(await (await fetch("https://cdn.jsdelivr.net/npm/airportvector@4.0.0/anchors.json")).json());
  OAVG.encode(51.5074, -0.1278);  // "LCY-55444-38173"
</script>
```

## Reading a code

Every square splits 3 × 3, named like a phone keypad. `5` is always the part with the airport.

```
1 2 3      NW  N  NE
4 5 6  =   W   ●   E
7 8 9      SW  S  SE
```

- First group (5 digits): the 1 km square. Second group (up to 5 digits): the spot inside it, down to 4 m.
- Count the leading 5s for distance: `5` within 40 km, `55` 13.5 km, `555` 4.5 km.
- Places over 121 km from their airport get a longer first group (leading 5s are implied).
- Any start of a code is a square, so area search is a prefix search. Check `neighbors()` too.

Precision: `"1km"`, `"333m"`, `"111m"`, `"37m"`, `"12m"` or `"4m"` (default).

Results match the Python package (`pip install airportvector`) exactly — both are tested against the same vectors.

## Links

- Live map & logistics zone calculator: <https://airportvector.org> · <https://airportvector.org/logistics>
- Specification v4: <https://github.com/dhmkt05/airportvector/blob/main/docs/SPEC-v4.md>
- Source: <https://github.com/dhmkt05/airportvector>

## Status & license

Draft specification v4 — airport coordinates are being verified against official sources.
Not for navigation, aviation or emergency-services use.

Source-available under the **Business Source License 1.1** (see `LICENSE.md`): free for development,
non-commercial use and internal deployment; offering a paid hosted API/SaaS to third parties is not permitted.
Converts to Apache 2.0 on 1 October 2029.
