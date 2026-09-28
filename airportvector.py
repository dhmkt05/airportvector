# Copyright (c) 2026 AirportVector Authors
# This source code is licensed under the Business Source License 1.1 (BSL).
# Free for development, non-commercial use, and internal deployment.
# Commercial SaaS hosting or paid API distribution is strictly prohibited.
# See LICENSE.md in the root directory for full terms.
"""
AirportVector - reference implementation of the Open Airport Vector Grid (OAVG) v2.0.

    TRZ-D03320331  =  Trichy airport, North-West sector,
                      X = 0332 (3,320 m West), Y = 0331 (3,310 m North), 10 m cell

Pure Python, no dependencies, works offline. See docs/spec-v2.pdf for the full spec.

Quick use:
    >>> import airportvector as av
    >>> av.encode(10.7950461, 78.6793020)            # nearest airport, 10 m cells
    'TRZ-D03320331'
    >>> av.decode("TRZ-D03320331")                   # centre of the cell
    (10.795068, 78.679296)
"""
from __future__ import annotations

import csv
import math
import os
import re
from dataclasses import dataclass
from functools import lru_cache

__version__ = "2.0.0"
SPEC_VERSION = "2.0"

# --------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------

#: precision name -> digits per axis. Cell size = 10 ** (5 - digits) metres.
PRECISIONS = {"1km": 2, "100m": 3, "10m": 4, "1m": 5}
DEFAULT_PRECISION = "10m"

#: |E| and |N| must be below this (metres) to be encodable from an anchor.
MAX_OFFSET_M = 100_000
#: Nominal zone radius: 50 miles.
NOMINAL_ZONE_M = 80_467

DEFAULT_REGISTRY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "anchors.csv")

_CODE_RE = re.compile(r"^([A-Z]{3,4})-([ABCD])(\d+)(?:\.(\d+))?$")


class OAVGError(ValueError):
    """Any invalid input, unknown anchor, or out-of-range location."""


# --------------------------------------------------------------------------
# Anchor registry
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Anchor:
    code: str
    type: str       # IATA (3 letters) or ICAO (4 letters)
    name: str
    lat: float
    lon: float
    status: str     # active | retired  (retired = decode only)


def load_registry(path: str = DEFAULT_REGISTRY) -> dict[str, Anchor]:
    """Load the anchor registry CSV into {code: Anchor}."""
    anchors: dict[str, Anchor] = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            code = row["code"].strip().upper()
            kind = row["type"].strip().upper()
            if kind not in ("IATA", "ICAO") or len(code) != (3 if kind == "IATA" else 4):
                raise OAVGError(f"Registry row {code!r}: type/length mismatch")
            if code in anchors:
                raise OAVGError(f"Registry has duplicate code {code!r}")
            anchors[code] = Anchor(code, kind, row["name"].strip(), float(row["lat"]),
                                   float(row["lon"]), row["status"].strip().lower())
    return anchors


_registry: dict[str, Anchor] | None = None


def registry() -> dict[str, Anchor]:
    """The loaded default registry (loaded once, on first use)."""
    global _registry
    if _registry is None:
        _registry = load_registry()
    return _registry


def use_registry(anchors: dict[str, Anchor]) -> None:
    """Swap in a different registry (e.g. for tests or a bigger anchor list)."""
    global _registry
    _registry = anchors


def get_anchor(code: str) -> Anchor:
    try:
        return registry()[code.strip().upper()]
    except KeyError:
        raise OAVGError(f"Unknown anchor code {code!r}") from None


# --------------------------------------------------------------------------
# Transverse Mercator on WGS84 (Krueger series, same maths as UTM).
# Grid centred on the anchor, scale factor 1, no false easting/northing.
# --------------------------------------------------------------------------

_A = 6378137.0
_F = 1 / 298.257223563
_E = math.sqrt(_F * (2 - _F))
_N = _F / (2 - _F)
_n = [_N ** i for i in range(7)]
_AR = _A / (1 + _N) * (1 + _n[2] / 4 + _n[4] / 64 + _n[6] / 256)  # rectifying radius

_ALPHA = (
    _n[1] / 2 - 2 * _n[2] / 3 + 5 * _n[3] / 16 + 41 * _n[4] / 180 - 127 * _n[5] / 288 + 7891 * _n[6] / 37800,
    13 * _n[2] / 48 - 3 * _n[3] / 5 + 557 * _n[4] / 1440 + 281 * _n[5] / 630 - 1983433 * _n[6] / 1935360,
    61 * _n[3] / 240 - 103 * _n[4] / 140 + 15061 * _n[5] / 26880 + 167603 * _n[6] / 181440,
    49561 * _n[4] / 161280 - 179 * _n[5] / 168 + 6601661 * _n[6] / 7257600,
    34729 * _n[5] / 80640 - 3418889 * _n[6] / 1995840,
    212378941 * _n[6] / 319334400,
)
_BETA = (
    _n[1] / 2 - 2 * _n[2] / 3 + 37 * _n[3] / 96 - _n[4] / 360 - 81 * _n[5] / 512 + 96199 * _n[6] / 604800,
    _n[2] / 48 + _n[3] / 15 - 437 * _n[4] / 1440 + 46 * _n[5] / 105 - 1118711 * _n[6] / 3870720,
    17 * _n[3] / 480 - 37 * _n[4] / 840 - 209 * _n[5] / 4480 + 5569 * _n[6] / 90720,
    4397 * _n[4] / 161280 - 11 * _n[5] / 504 - 830251 * _n[6] / 7257600,
    4583 * _n[5] / 161280 - 108847 * _n[6] / 3991680,
    20648693 * _n[6] / 638668800,
)


def _conformal_lat(phi: float) -> float:
    s = math.sin(phi)
    return math.atan(math.sinh(math.atanh(s) - _E * math.atanh(_E * s)))


def _geodetic_lat(chi: float) -> float:
    phi = chi
    for _ in range(15):
        s = math.sin(phi)
        nxt = 2 * math.atan(math.tan(math.pi / 4 + chi / 2) * ((1 + _E * s) / (1 - _E * s)) ** (_E / 2)) - math.pi / 2
        if abs(nxt - phi) < 1e-15:
            return nxt
        phi = nxt
    return phi


def _tm_forward(lat: float, dlon: float) -> tuple[float, float]:
    """(lat, lon - lon0) in radians -> (x, y) metres; y measured from the equator."""
    t = math.tan(_conformal_lat(lat))
    xi = math.atan2(t, math.cos(dlon))
    eta = math.atanh(math.sin(dlon) / math.sqrt(1 + t * t))
    x, y = eta, xi
    for j, a in enumerate(_ALPHA, start=1):
        x += a * math.cos(2 * j * xi) * math.sinh(2 * j * eta)
        y += a * math.sin(2 * j * xi) * math.cosh(2 * j * eta)
    return _AR * x, _AR * y


def _tm_inverse(x: float, y: float) -> tuple[float, float]:
    """(x, y) metres (y from equator) -> (lat, lon - lon0) in radians."""
    xi, eta = y / _AR, x / _AR
    xi_p, eta_p = xi, eta
    for j, b in enumerate(_BETA, start=1):
        xi_p -= b * math.sin(2 * j * xi) * math.cosh(2 * j * eta)
        eta_p -= b * math.cos(2 * j * xi) * math.sinh(2 * j * eta)
    chi = math.asin(math.sin(xi_p) / math.cosh(eta_p))
    return _geodetic_lat(chi), math.atan2(math.sinh(eta_p), math.cos(xi_p))


@lru_cache(maxsize=4096)
def _y0(anchor_lat: float) -> float:
    return _tm_forward(math.radians(anchor_lat), 0.0)[1]


def to_grid(anchor: Anchor | str, lat: float, lon: float) -> tuple[float, float]:
    """lat/lon (degrees) -> (E, N) metres from the anchor. E+ = East, N+ = North."""
    a = get_anchor(anchor) if isinstance(anchor, str) else anchor
    _check_latlon(lat, lon)
    dlon = math.radians(((lon - a.lon + 540.0) % 360.0) - 180.0)
    x, y = _tm_forward(math.radians(lat), dlon)
    return x, y - _y0(a.lat)


def from_grid(anchor: Anchor | str, e: float, n: float) -> tuple[float, float]:
    """(E, N) metres from the anchor -> lat/lon degrees."""
    a = get_anchor(anchor) if isinstance(anchor, str) else anchor
    lat, dlon = _tm_inverse(e, n + _y0(a.lat))
    lon = ((a.lon + math.degrees(dlon) + 540.0) % 360.0) - 180.0
    return math.degrees(lat), lon


def _check_latlon(lat: float, lon: float) -> None:
    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        raise OAVGError(f"Latitude/longitude out of range: {lat}, {lon}")


def ground_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in metres (mean Earth radius). Used to pick the nearest anchor."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371008.8 * math.asin(min(1.0, math.sqrt(h)))


# --------------------------------------------------------------------------
# Codes
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class OAVGCode:
    anchor: str
    sector: str     # A=NE, B=SE, C=SW, D=NW
    x: int          # cells East (A,B) or West (C,D)
    y: int          # cells North (A,D) or South (B,C)
    digits: int     # digits per axis (2..5)

    @property
    def cell_size_m(self) -> int:
        return 10 ** (5 - self.digits)

    @property
    def precision(self) -> str:
        return {2: "1km", 3: "100m", 4: "10m", 5: "1m"}[self.digits]

    def __str__(self) -> str:
        return f"{self.anchor}-{self.sector}{self.x:0{self.digits}d}{self.y:0{self.digits}d}"

    def display(self) -> str:
        """Human-friendly form with a dot between X and Y, e.g. TRZ-D0332.0331."""
        return f"{self.anchor}-{self.sector}{self.x:0{self.digits}d}.{self.y:0{self.digits}d}"


def _digits_for(precision: str | int) -> int:
    if isinstance(precision, int) and precision in PRECISIONS.values():
        return precision
    key = str(precision).lower().replace(" ", "")
    if key not in PRECISIONS:
        raise OAVGError(f"Unknown precision {precision!r}; use one of {list(PRECISIONS)}")
    return PRECISIONS[key]


def _sector(e: float, n: float) -> str:
    # Tie rule: exactly zero counts as East / North.
    if e >= 0:
        return "A" if n >= 0 else "B"
    return "D" if n >= 0 else "C"


def encode_grid(anchor: str, e: float, n: float, precision: str | int = DEFAULT_PRECISION) -> str:
    """Encode grid metres (E, N) from an anchor. Truncates (never rounds)."""
    a = get_anchor(anchor)
    d = _digits_for(precision)
    if abs(e) >= MAX_OFFSET_M or abs(n) >= MAX_OFFSET_M:
        raise OAVGError(f"Location is {abs(e):.0f} m / {abs(n):.0f} m from {a.code}; "
                        f"must be under {MAX_OFFSET_M:,} m on both axes")
    cell = 10 ** (5 - d)
    return str(OAVGCode(a.code, _sector(e, n), int(abs(e) // cell), int(abs(n) // cell), d))


def nearest_anchor(lat: float, lon: float) -> Anchor:
    """Canonical anchor: nearest ACTIVE anchor whose grid range contains the point.
    Ties are broken alphabetically."""
    _check_latlon(lat, lon)
    candidates = sorted(
        ((round(ground_distance_m(lat, lon, a.lat, a.lon), 3), a.code, a)
         for a in registry().values() if a.status == "active"),
        key=lambda t: (t[0], t[1]),
    )
    for dist, _, a in candidates:
        if dist > 150_000:  # beyond the square's corner (~141 km): nothing further can fit
            break
        e, n = to_grid(a, lat, lon)
        if abs(e) < MAX_OFFSET_M and abs(n) < MAX_OFFSET_M:
            return a
    raise OAVGError("No anchor within range. Spec fallback: use an Open Location Code (Plus Code) "
                    "prefixed 'OLC:' or add a supplementary ICAO anchor to the registry.")


def encode(lat: float, lon: float, precision: str | int = DEFAULT_PRECISION, anchor: str | None = None) -> str:
    """lat/lon (degrees, WGS84) -> OAVG code.

    precision: "1km", "100m", "10m" (default) or "1m".
    anchor:    force a specific airport (an 'alternate' code). Default = nearest (canonical).
    """
    if anchor is None:
        a = nearest_anchor(lat, lon)
    else:
        a = get_anchor(anchor)
        if a.status != "active":
            raise OAVGError(f"Anchor {a.code} is {a.status}; it can be decoded but not used for new codes")
    e, n = to_grid(a, lat, lon)
    return encode_grid(a.code, e, n, precision)


def parse(code: str) -> OAVGCode:
    """Validate and split a code. Accepts any letter case and the dotted display form."""
    if not isinstance(code, str):
        raise OAVGError("Code must be a string")
    m = _CODE_RE.match(code.strip().upper())
    if not m:
        raise OAVGError(f"Invalid OAVG code {code!r}. Expected e.g. TRZ-D03320331")
    anchor, sector, first, second = m.groups()
    if second is not None:
        if len(first) != len(second):
            raise OAVGError(f"Invalid code {code!r}: X and Y must have the same number of digits")
        digits = first + second
    else:
        digits = first
    if len(digits) not in (4, 6, 8, 10):
        raise OAVGError(f"Invalid code {code!r}: needs 4, 6, 8 or 10 digits (got {len(digits)})")
    get_anchor(anchor)  # raises if unknown
    d = len(digits) // 2
    return OAVGCode(anchor, sector, int(digits[:d]), int(digits[d:]), d)


def _signed_index(c: OAVGCode) -> tuple[int, int]:
    i = c.x if c.sector in "AB" else -c.x - 1
    j = c.y if c.sector in "AD" else -c.y - 1
    return i, j


def _from_index(anchor: str, i: int, j: int, d: int) -> OAVGCode:
    x = i if i >= 0 else -i - 1
    y = j if j >= 0 else -j - 1
    if x >= 10 ** d or y >= 10 ** d:
        raise OAVGError("Result is outside the anchor's range")
    sector = ("A" if j >= 0 else "B") if i >= 0 else ("D" if j >= 0 else "C")
    return OAVGCode(anchor, sector, x, y, d)


def decode_grid(code: str) -> tuple[str, float, float]:
    """Code -> (anchor, E, N) of the cell centre, in metres."""
    c = parse(code)
    i, j = _signed_index(c)
    size = c.cell_size_m
    return c.anchor, (i + 0.5) * size, (j + 0.5) * size


def decode(code: str, ndigits: int = 6) -> tuple[float, float]:
    """Code -> (lat, lon) of the cell centre, rounded to `ndigits` decimals."""
    anchor, e, n = decode_grid(code)
    lat, lon = from_grid(anchor, e, n)
    return round(lat, ndigits), round(lon, ndigits)


def bounds(code: str) -> dict:
    """Corner lat/lons of the cell: {'sw': (lat, lon), 'ne': (lat, lon)} (approximate box)."""
    c = parse(code)
    i, j = _signed_index(c)
    s = c.cell_size_m
    return {"sw": from_grid(c.anchor, i * s, j * s), "ne": from_grid(c.anchor, (i + 1) * s, (j + 1) * s)}


def move(code: str, east_cells: int = 0, north_cells: int = 0) -> str:
    """Shift a code by whole cells (negative = West / South). Handles sector crossings."""
    c = parse(code)
    i, j = _signed_index(c)
    return str(_from_index(c.anchor, i + east_cells, j + north_cells, c.digits))


def shorten(code: str, precision: str | int) -> str:
    """Reduce precision by truncation, e.g. TRZ-D0332403312 -> TRZ-D03320331."""
    c = parse(code)
    d = _digits_for(precision)
    if d > c.digits:
        raise OAVGError("Cannot add precision that the code does not have")
    cut = 10 ** (c.digits - d)
    return str(OAVGCode(c.anchor, c.sector, c.x // cut, c.y // cut, d))


def normalize(code: str) -> str:
    """Canonical form: upper case, no dot."""
    return str(parse(code))


# --------------------------------------------------------------------------
# Command line:  python airportvector.py encode 10.795 78.679 [10m]
#                python airportvector.py decode TRZ-D03320331
# --------------------------------------------------------------------------

def _main(argv: list[str]) -> int:
    usage = "usage: airportvector.py encode LAT LON [1km|100m|10m|1m]  |  decode CODE"
    try:
        if len(argv) >= 3 and argv[0] == "encode":
            print(encode(float(argv[1]), float(argv[2]), argv[3] if len(argv) > 3 else DEFAULT_PRECISION))
        elif len(argv) == 2 and argv[0] == "decode":
            lat, lon = decode(argv[1])
            print(f"{lat}, {lon}")
        else:
            print(usage)
            return 2
    except (OAVGError, ValueError) as exc:
        print(f"error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    import sys
    raise SystemExit(_main(sys.argv[1:]))
