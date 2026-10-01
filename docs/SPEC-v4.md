# Open Airport Vector Grid (OAVG) — Specification v4.0

Status: draft, 1 October 2026. Replaces v2.1 (letter sectors A–L). v2.1 codes are no longer valid.

## 1. The idea

Every place on Earth is named from its **nearest commercial airport**, on a grid of squares centred
on that airport. Each square is split 3 × 3 and each part is named like a **phone keypad**:

```
1 2 3      NW  N  NE
4 5 6  =   W   ●   E        ● = the part that holds the airport
7 8 9      SW  S  SE
```

`5` is always the middle part, so it always contains the airport.

## 2. Code format

```
TRZ 55511 79566        written for people (spaces)
TRZ-55511-79566        canonical form for links, files and databases (hyphens)
```

| Part | Meaning |
|---|---|
| `TRZ` | IATA code of the anchor airport (3 letters) |
| First group, 5 digits | The 1 km square, inside a 243 km zone centred on the airport (81 → 27 → 9 → 3 → 1 km) |
| Second group, 0–5 digits | Position inside the 1 km square (333 m → 111 m → 37 m → 12 m → 4.1 m) |

Digits are always 1–9. `0` is never used.

### Precision

| Name | Second group | Cell |
|---|---|---|
| `1km` | none (`TRZ 55511`) | 1 km |
| `333m` | 1 digit | 333 m |
| `111m` | 2 digits | 111 m |
| `37m` | 3 digits | 37 m |
| `12m` | 4 digits | 12.3 m |
| `4m` (default) | 5 digits | 4.1 m |

Dropping digits from the end of the second group gives the same place at lower precision.

### Places far from an airport

The 5-digit first group covers ±121.5 km. Farther places get a **longer first group**: each extra
digit is one more 3 × 3 level outward (zone 729 km, 2,187 km, …), up to 9 digits (±9,841 km).
Leading 5s are implied: `TRZ 55511` and `TRZ 555511` are the same square, and the canonical code
is always the shortest. So a first group longer than 5 digits never starts with `5`.

## 3. Reading a code by eye

- Count the leading 5s: `5` = within 40 km, `55` = 13.5 km, `555` = 4.5 km, `5555` = 1.5 km
  (distances along the square's sides).
- The first digit that is not 5 gives the direction from the airport.
- A first group longer than 5 digits means the place is more than 121 km away.

## 4. Grid

1. **Anchor:** the nearest active airport in the registry by true ground distance (WGS84);
   exact ties alphabetical. A code may also be made from any other airport (decoding works the same).
2. **Projection:** Azimuthal Equidistant on WGS84 centred on the anchor (Vincenty): X metres east,
   Y metres north. √(X² + Y²) is the exact ground distance to the airport.
3. **Zone:** choose the smallest `e` (0–4) with max(|X|, |Y|) < 121,500 × 3^e. Zone width Z = 243,000 × 3^e m,
   half-width H = Z / 2.
4. **Cells:** with L = 5 + e + (second-group digits) and N = 3^L:
   - col = floor((X + H) × N / Z), clamped to 0 … N−1 (counted from the west edge)
   - row = N − 1 − floor((Y + H) × N / Z), clamped to 0 … N−1 (counted from the north edge)
5. **Digits:** for level k = L−1 down to 0: digit = 3 × trit_k(row) + trit_k(col) + 1, where trit_k
   is the k-th base-3 digit. The first 5 + e digits form the first group, the rest the second group.
6. **Decoding** reverses steps 4–5 and returns the centre of the cell: X = (col + ½) × Z/N − H,
   Y = H − (row + ½) × Z/N, then the inverse projection.

The encoder truncates; it never rounds.

## 5. Parsing

- Letters are case-insensitive. Spaces, hyphens or a dot may separate the groups.
- A single block of digits with no separator is a full code (last 5 digits = second group) when it has
  10 or more digits, otherwise a first group only. Shortened codes should keep the separator.
- The first group has 5–9 digits; the second group at most 5.

## 6. Area search

Any start of a code is a square: `TRZ 5527` is a 3 km square, `TRZ 55511` a 1 km square. Nearby search
should look at a code **and its 8 neighbours** (`neighbors()`), because two places just either side of a
grid line can share few leading digits.

## 7. Registry

4,133 IATA airports with scheduled service (OurAirports, public domain), in
`python/src/airportvector/anchors.csv`. Airports are only added in a new spec version, so codes do not
change when an airport opens. Retired airports stay in the registry for decoding only.

## 8. Reference vectors

| Point | Code |
|---|---|
| 10.7950461, 78.6793020 (Trichy) | `TRZ-55511-79566` (1 km: `TRZ-55511`) |
| 51.5074, −0.1278 (London) | `LCY-55444-38173` |
| 23.5, 12.0 (Sahara) | `DJG-686479-26417` |
| −48.8767, −123.3933 (Point Nemo) | `IPC-84772643-65933` |
| −90, 0 (South Pole) | `USH-822858828-82252` |

The Python package is the reference implementation; the JavaScript package is tested against it.
