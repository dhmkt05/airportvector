# Copyright (c) 2026 AirportVector Authors
# This source code is licensed under the Business Source License 1.1 (BSL).
# Free for development, non-commercial use, and internal deployment.
# Commercial SaaS hosting or paid API distribution is strictly prohibited.
# See LICENSE.md in the root directory for full terms.
"""
AirportVector - reference implementation of the Open Airport Vector Grid (OAVG) v4.

Every point on Earth is coded from its NEAREST commercial airport, on a
"phone keypad" grid centred on that airport:

    TRZ 55511 79566  =  Trichy airport, then 10 keypad digits (about 4 m)

Each square is split 3 x 3 and each part is named like a phone keypad:

    1 2 3      NW  N  NE
    4 5 6  =   W   *   E          5 is always the part that holds the airport
    7 8 9      SW  S  SE

- First group (5 digits): the 1 km square, inside a 243 km zone round the airport.
  Places farther away get a longer first group (6-9 digits); leading 5s are implied.
- Second group (0-5 digits): position inside the 1 km square (333 m ... 4 m).
- Count the leading 5s for distance: 5 = within 40 km, 55 = 13.5 km, 555 = 4.5 km.
- Any start of a code is a square, so area search is a prefix search.

Written TRZ-55511-79566 in links, TRZ 55511 79566 for people.
Pure Python, no dependencies, works offline. Full spec: https://github.com/dhmkt05/airportvector/blob/main/docs/SPEC-v4.md
"""
from __future__ import annotations

import csv
import math
import os
import re
from dataclasses import dataclass

__version__ = "4.0.0"
SPEC_VERSION = "4.0"

# --------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------

#: precision name -> number of digits in the second group. Cell = 1000 / 3**n metres.
PRECISIONS = {"1km": 0, "333m": 1, "111m": 2, "37m": 3, "12m": 4, "4m": 5}
_PRECISION_NAME = {v: k for k, v in PRECISIONS.items()}
DEFAULT_PRECISION = "4m"

BASE_ZONE_M = 243_000            # the 5-digit zone: 243 km square centred on the airport
COARSE_DIGITS = 5                # first group, inside the base zone (ends at 1 km)
FINE_DIGITS = 5                  # second group at full precision
MAX_EXTRA = 4                    # up to 4 implied outer levels: 19,683 km zone (every place is
                                 # within 3,600 km of its nearest airport on each axis)
KEYPAD_DIRECTIONS = {1: "NW", 2: "N", 3: "NE", 4: "W", 5: "centre", 6: "E", 7: "SW", 8: "S", 9: "SE"}

DEFAULT_REGISTRY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "anchors.csv")

_CODE_RE = re.compile(r"^([A-Z]{3})[ -]*([0-9]+)(?:[ .-]+([0-9]+))?$", re.ASCII)
_STATUSES = ("active", "retired")


class OAVGError(ValueError):
    """Any invalid input, unknown anchor, or out-of-range location."""


class _NoConvergence(OAVGError):
    """Vincenty's inverse method did not converge (nearly antipodal points)."""


# --------------------------------------------------------------------------
# Anchor registry
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Anchor:
    code: str
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
            if not re.fullmatch(r"[A-Z]{3}", code):
                raise OAVGError(f"Registry code {code!r} must be 3 letters")
            if code in anchors:
                raise OAVGError(f"Registry has duplicate code {code!r}")
            name = (row.get("name") or "").strip()
            status = (row.get("status") or "active").strip().lower()
            try:
                lat, lon = float(row["lat"]), float(row["lon"])
            except (TypeError, ValueError):
                raise OAVGError(f"Registry row {code}: lat/lon must be numbers") from None
            if not (math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180):
                raise OAVGError(f"Registry row {code}: lat/lon out of range ({lat}, {lon})")
            if not name:
                raise OAVGError(f"Registry row {code}: name is empty")
            if status not in _STATUSES:
                raise OAVGError(f"Registry row {code}: status must be one of {_STATUSES}, got {status!r}")
            anchors[code] = Anchor(code, name, lat, lon, status)
    return anchors


_registry: dict[str, Anchor] | None = None
_active: list[tuple[Anchor, float, float, float]] | None = None


def registry() -> dict[str, Anchor]:
    """The loaded default registry (loaded once, on first use)."""
    global _registry
    if _registry is None:
        use_registry(load_registry())
    return _registry  # type: ignore[return-value]


def use_registry(anchors: dict[str, Anchor]) -> None:
    """Swap in a different registry (e.g. for tests)."""
    global _registry, _active
    _registry = anchors
    _active = [(a, *_unit(a.lat, a.lon)) for a in anchors.values() if a.status == "active"]


def get_anchor(code: str) -> Anchor:
    try:
        return registry()[code.strip().upper()]
    except KeyError:
        raise OAVGError(f"Unknown anchor code {code!r}") from None


# --------------------------------------------------------------------------
# Geodesy on the WGS84 ellipsoid (Vincenty's formulae, ~0.1 mm accuracy).
# The grid is an Azimuthal Equidistant projection centred on the anchor:
#     X = s * sin(azimuth),  Y = s * cos(azimuth)
# where s = true ground distance from the anchor. So sqrt(X^2 + Y^2) is
# exactly the distance to the airport, anywhere on the globe.
# --------------------------------------------------------------------------

_A = 6378137.0
_F = 1 / 298.257223563
_B = _A * (1 - _F)


def _reduced(lat_rad: float) -> tuple[float, float]:
    u = math.atan2((1 - _F) * math.sin(lat_rad), math.cos(lat_rad))
    return math.sin(u), math.cos(u)


def _ab(cos2_alpha: float) -> tuple[float, float]:
    u2 = cos2_alpha * (_A * _A - _B * _B) / (_B * _B)
    big_a = 1 + u2 / 16384 * (4096 + u2 * (-768 + u2 * (320 - 175 * u2)))
    big_b = u2 / 1024 * (256 + u2 * (-128 + u2 * (74 - 47 * u2)))
    return big_a, big_b


def _delta_sigma(big_b: float, sin_s: float, cos_s: float, cos2sm: float) -> float:
    return big_b * sin_s * (cos2sm + big_b / 4 * (cos_s * (-1 + 2 * cos2sm ** 2)
                            - big_b / 6 * cos2sm * (-3 + 4 * sin_s ** 2) * (-3 + 4 * cos2sm ** 2)))


def geodesic_inverse(lat1: float, lon1: float, lat2: float, lon2: float) -> tuple[float, float]:
    """Distance (m) and initial azimuth (radians, clockwise from North) from point 1 to point 2."""
    sin_u1, cos_u1 = _reduced(math.radians(lat1))
    sin_u2, cos_u2 = _reduced(math.radians(lat2))
    big_l = math.radians(((lon2 - lon1 + 540.0) % 360.0) - 180.0)
    lam = big_l
    for _ in range(200):
        sin_l, cos_l = math.sin(lam), math.cos(lam)
        sin_s = math.hypot(cos_u2 * sin_l, cos_u1 * sin_u2 - sin_u1 * cos_u2 * cos_l)
        if sin_s == 0:
            return 0.0, 0.0
        cos_s = sin_u1 * sin_u2 + cos_u1 * cos_u2 * cos_l
        sigma = math.atan2(sin_s, cos_s)
        sin_alpha = cos_u1 * cos_u2 * sin_l / sin_s
        cos2_alpha = 1 - sin_alpha ** 2
        cos2sm = cos_s - 2 * sin_u1 * sin_u2 / cos2_alpha if cos2_alpha != 0 else 0.0
        c = _F / 16 * cos2_alpha * (4 + _F * (4 - 3 * cos2_alpha))
        lam_prev = lam
        lam = big_l + (1 - c) * _F * sin_alpha * (sigma + c * sin_s * (cos2sm + c * cos_s * (-1 + 2 * cos2sm ** 2)))
        if abs(lam - lam_prev) < 1e-13:
            break
    else:
        raise _NoConvergence("Points are nearly antipodal; geodesic did not converge")
    big_a, big_b = _ab(cos2_alpha)
    s = _B * big_a * (sigma - _delta_sigma(big_b, sin_s, cos_s, cos2sm))
    az = math.atan2(cos_u2 * math.sin(lam), cos_u1 * sin_u2 - sin_u1 * cos_u2 * math.cos(lam))
    return s, az


def geodesic_direct(lat1: float, lon1: float, azimuth: float, s: float) -> tuple[float, float]:
    """Point reached from (lat1, lon1) travelling s metres at initial azimuth (radians)."""
    if s == 0:
        return lat1, lon1
    sin_u1, cos_u1 = _reduced(math.radians(lat1))
    sin_a1, cos_a1 = math.sin(azimuth), math.cos(azimuth)
    sigma1 = math.atan2(sin_u1, cos_u1 * cos_a1)
    sin_alpha = cos_u1 * sin_a1
    cos2_alpha = 1 - sin_alpha ** 2
    big_a, big_b = _ab(cos2_alpha)
    sigma = s / (_B * big_a)
    for _ in range(200):
        cos2sm = math.cos(2 * sigma1 + sigma)
        sin_s, cos_s = math.sin(sigma), math.cos(sigma)
        sigma_prev = sigma
        sigma = s / (_B * big_a) + _delta_sigma(big_b, sin_s, cos_s, cos2sm)
        if abs(sigma - sigma_prev) < 1e-13:
            break
    cos2sm = math.cos(2 * sigma1 + sigma)
    sin_s, cos_s = math.sin(sigma), math.cos(sigma)
    tmp = sin_u1 * sin_s - cos_u1 * cos_s * cos_a1
    lat2 = math.atan2(sin_u1 * cos_s + cos_u1 * sin_s * cos_a1, (1 - _F) * math.hypot(sin_alpha, tmp))
    lam = math.atan2(sin_s * sin_a1, cos_u1 * cos_s - sin_u1 * sin_s * cos_a1)
    c = _F / 16 * cos2_alpha * (4 + _F * (4 - 3 * cos2_alpha))
    big_l = lam - (1 - c) * _F * sin_alpha * (sigma + c * sin_s * (cos2sm + c * cos_s * (-1 + 2 * cos2sm ** 2)))
    lon2 = ((lon1 + math.degrees(big_l) + 540.0) % 360.0) - 180.0
    return math.degrees(lat2), lon2


def distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """True ground distance in metres between two lat/lon points (WGS84).

    For nearly antipodal points (over ~19,000 km apart) Vincenty's method can fail;
    then the exact Karney method is used if `geographiclib` is installed, otherwise
    a spherical estimate (within ~0.5%)."""
    try:
        return geodesic_inverse(lat1, lon1, lat2, lon2)[0]
    except _NoConvergence:
        try:
            from geographiclib.geodesic import Geodesic  # optional
            return Geodesic.WGS84.Inverse(lat1, lon1, lat2, lon2)["s12"]
        except ImportError:
            return _spherical_m(lat1, lon1, lat2, lon2)


def _spherical_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * 6371008.8 * math.asin(min(1.0, math.sqrt(h)))


def to_grid(anchor: Anchor | str, lat: float, lon: float) -> tuple[float, float]:
    """lat/lon (degrees) -> (X, Y) metres from the anchor. X+ = East, Y+ = North."""
    a = get_anchor(anchor) if isinstance(anchor, str) else anchor
    _check_latlon(lat, lon)
    try:
        s, az = geodesic_inverse(a.lat, a.lon, lat, lon)
    except _NoConvergence:
        raise OAVGError(f"Location is on the far side of the Earth from {a.code}; out of range") from None
    if abs(lat) == 90:          # at a pole the bearing is exactly due North or South
        return 0.0, (s if lat > 0 else -s)
    x, y = s * math.sin(az), s * math.cos(az)
    # snap floating-point noise so points exactly on an axis get one sector
    return (0.0 if abs(x) < 1e-6 else x), (0.0 if abs(y) < 1e-6 else y)


def from_grid(anchor: Anchor | str, x: float, y: float) -> tuple[float, float]:
    """(X, Y) metres from the anchor -> lat/lon degrees."""
    a = get_anchor(anchor) if isinstance(anchor, str) else anchor
    return geodesic_direct(a.lat, a.lon, math.atan2(x, y), math.hypot(x, y))


def _check_latlon(lat: float, lon: float) -> None:
    for v in (lat, lon):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            raise OAVGError(f"Latitude/longitude must be finite numbers, got {v!r}")
    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        raise OAVGError(f"Latitude/longitude out of range: {lat}, {lon}")


def _unit(lat: float, lon: float) -> tuple[float, float, float]:
    p, l = math.radians(lat), math.radians(lon)
    return math.cos(p) * math.cos(l), math.cos(p) * math.sin(l), math.sin(p)


# --------------------------------------------------------------------------
# Codes
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class OAVGCode:
    anchor: str
    coarse: str     # first group: 5-10 keypad digits, ends at the 1 km square
    fine: str       # second group: 0-5 keypad digits inside the 1 km square

    @property
    def extra(self) -> int:
        """Implied outer levels (0 for places inside the 243 km zone)."""
        return len(self.coarse) - COARSE_DIGITS

    @property
    def levels(self) -> int:
        return len(self.coarse) + len(self.fine)

    @property
    def zone_m(self) -> int:
        return BASE_ZONE_M * 3 ** self.extra

    @property
    def cell_size_m(self) -> float:
        return 1000 / 3 ** len(self.fine)

    @property
    def precision(self) -> str:
        return _PRECISION_NAME[len(self.fine)]

    @property
    def leading_fives(self) -> int:
        """Number of leading 5s in the first group (0 if the code has implied outer levels)."""
        n = 0
        while n < len(self.coarse) and self.coarse[n] == "5":
            n += 1
        return n

    def __str__(self) -> str:
        """Canonical form for links and storage, e.g. TRZ-55511-79566."""
        return f"{self.anchor}-{self.coarse}" + (f"-{self.fine}" if self.fine else "")

    def display(self) -> str:
        """Form for people, e.g. TRZ 55511 79566."""
        return f"{self.anchor} {self.coarse}" + (f" {self.fine}" if self.fine else "")


def _fine_for(precision: str | int) -> int:
    if isinstance(precision, int) and not isinstance(precision, bool) and precision in _PRECISION_NAME:
        return precision
    key = str(precision).lower().replace(" ", "")
    if key not in PRECISIONS:
        raise OAVGError(f"Unknown precision {precision!r}; use one of {list(PRECISIONS)}")
    return PRECISIONS[key]


def _extra_for(x: float, y: float) -> int:
    """Smallest number of implied outer levels whose zone contains (x, y)."""
    if not (math.isfinite(x) and math.isfinite(y)):
        raise OAVGError("Grid distances must be finite numbers")
    m = max(abs(x), abs(y))
    for e in range(MAX_EXTRA + 1):
        if m < BASE_ZONE_M * 3 ** e / 2:
            return e
    raise OAVGError(f"Location is {m / 1000:,.3f} km from the anchor on one axis; out of range")


def _digits_from_index(col: int, row: int, levels: int) -> str:
    """Column (from the west edge) and row (from the north edge) -> keypad digits."""
    out = []
    for k in range(levels - 1, -1, -1):
        p = 3 ** k
        out.append(str((row // p) % 3 * 3 + (col // p) % 3 + 1))
    return "".join(out)


def _index_from_digits(digits: str) -> tuple[int, int]:
    col = row = 0
    for ch in digits:
        d = int(ch) - 1
        col = col * 3 + d % 3
        row = row * 3 + d // 3
    return col, row


def encode_grid(anchor: str, x: float, y: float, precision: str | int = DEFAULT_PRECISION) -> str:
    """Encode grid metres (X east, Y north) from an anchor. Truncates (never rounds)."""
    a = get_anchor(anchor)
    fine = _fine_for(precision)
    extra = _extra_for(x, y)
    levels = COARSE_DIGITS + extra + fine
    n = 3 ** levels
    zone = BASE_ZONE_M * 3 ** extra
    half = zone / 2
    col = min(n - 1, max(0, math.floor((x + half) * n / zone)))
    row = n - 1 - min(n - 1, max(0, math.floor((y + half) * n / zone)))
    digits = _digits_from_index(col, row, levels)
    split = COARSE_DIGITS + extra
    return str(OAVGCode(a.code, digits[:split], digits[split:]))


def nearest_anchor(lat: float, lon: float) -> Anchor:
    """Canonical anchor: the nearest ACTIVE airport by true ground distance.
    Exact ties are broken alphabetically."""
    _check_latlon(lat, lon)
    registry()
    if not _active:
        raise OAVGError("Registry has no active anchors")
    px, py, pz = _unit(lat, lon)
    # Fast pre-filter on the sphere, then exact ellipsoidal distance for close candidates.
    scored = sorted(((-(ux * px + uy * py + uz * pz), a.code, a) for a, ux, uy, uz in _active))
    best_dot = -scored[0][0]
    best_ang = math.acos(max(-1.0, min(1.0, best_dot)))
    margin = best_ang * 1.01 + 2e-4  # ~1% + ~1.3 km: ellipsoid vs sphere difference
    shortlist = [a for neg, _, a in scored if math.acos(max(-1.0, min(1.0, -neg))) <= margin]
    return min(shortlist, key=lambda a: (distance_m(lat, lon, a.lat, a.lon), a.code))


def encode(lat: float, lon: float, precision: str | int = DEFAULT_PRECISION, anchor: str | None = None) -> str:
    """lat/lon (degrees, WGS84) -> OAVG code, e.g. 'TRZ-55511-79566'.

    precision: "1km", "333m", "111m", "37m", "12m" or "4m" (default).
    anchor:    force a specific airport. Default = nearest airport (the canonical code).
    """
    if anchor is None:
        a = nearest_anchor(lat, lon)
    else:
        a = get_anchor(anchor)
        if a.status != "active":
            raise OAVGError(f"Anchor {a.code} is {a.status}; it can be decoded but not used for new codes")
    x, y = to_grid(a, lat, lon)
    return encode_grid(a.code, x, y, precision)


def parse(code: str) -> OAVGCode:
    """Validate and split a code. Accepts any letter case and spaces, hyphens or dots
    between the groups: 'TRZ 55511 79566', 'trz-55511-79566', 'TRZ5551179566'.

    One block of digits with no separator is read as a full-precision code when it has
    10 or more digits (the last 5 are the second group), otherwise as a first group only."""
    if not isinstance(code, str):
        raise OAVGError("Code must be a string")
    if not code.isascii() or len(code) > 40:
        raise OAVGError(f"Invalid OAVG code {code[:40]!r}: use only A-Z, 1-9, spaces and '-'")
    m = _CODE_RE.match(code.strip().upper())
    if not m:
        raise OAVGError(f"Invalid OAVG code {code!r}. Expected e.g. TRZ 55511 79566")
    anchor, coarse, fine = m.groups()
    if fine is None:
        whole = coarse
        if len(whole) >= COARSE_DIGITS + FINE_DIGITS:
            coarse, fine = whole[:-FINE_DIGITS], whole[-FINE_DIGITS:]
        else:
            coarse, fine = whole, ""
    if "0" in coarse + fine:
        raise OAVGError(f"Invalid code {code!r}: OAVG digits are 1-9 (0 is never used)")
    if not COARSE_DIGITS <= len(coarse) <= COARSE_DIGITS + MAX_EXTRA:
        raise OAVGError(f"Invalid code {code!r}: the first group needs "
                        f"{COARSE_DIGITS}-{COARSE_DIGITS + MAX_EXTRA} digits (got {len(coarse)})")
    if len(fine) > FINE_DIGITS:
        raise OAVGError(f"Invalid code {code!r}: the second group has at most {FINE_DIGITS} digits (got {len(fine)})")
    # implied 5s: a longer first group that starts with 5 is the same place written long
    while len(coarse) > COARSE_DIGITS and coarse[0] == "5":
        coarse = coarse[1:]
    get_anchor(anchor)  # raises if unknown
    return OAVGCode(anchor, coarse, fine)


def _cell_index(c: OAVGCode) -> tuple[int, int, int, float, float]:
    """(col, row, cells across, cell size m, half zone m) for a parsed code."""
    col, row = _index_from_digits(c.coarse + c.fine)
    n = 3 ** c.levels
    return col, row, n, c.zone_m / n, c.zone_m / 2


def decode_grid(code: str) -> tuple[str, float, float]:
    """Code -> (anchor, X, Y) of the cell centre, in metres."""
    c = parse(code)
    col, row, _, size, half = _cell_index(c)
    return c.anchor, (col + 0.5) * size - half, half - (row + 0.5) * size


def decode(code: str, ndigits: int = 6) -> tuple[float, float]:
    """Code -> (lat, lon) of the cell centre, rounded to `ndigits` decimals."""
    anchor, x, y = decode_grid(code)
    lat, lon = from_grid(anchor, x, y)
    return round(lat, ndigits), round(lon, ndigits)


def cell_polygon(code: str) -> list[tuple[float, float]]:
    """The cell's 4 corners as (lat, lon), in grid order: (-X,-Y), (+X,-Y), (+X,+Y), (-X,+Y).
    Use this to draw the cell on a map. (Near the dateline, longitudes may jump by 360.)"""
    c = parse(code)
    col, row, _, s, half = _cell_index(c)
    w, e = col * s - half, (col + 1) * s - half
    n, so = half - row * s, half - (row + 1) * s
    return [from_grid(c.anchor, gx, gy) for gx, gy in ((w, so), (e, so), (e, n), (w, n))]


def move(code: str, east_cells: int = 0, north_cells: int = 0) -> str:
    """Shift a code by whole cells of its own size (negative = West / South).
    The result can have a longer or shorter first group if it crosses a zone edge."""
    for v in (east_cells, north_cells):
        if isinstance(v, bool) or not isinstance(v, int):
            raise OAVGError(f"Cells to move must be whole numbers, got {v!r}")
    c = parse(code)
    col, row, _, s, half = _cell_index(c)
    x = (col + east_cells + 0.5) * s - half
    y = half - (row - north_cells + 0.5) * s
    return encode_grid(c.anchor, x, y, len(c.fine))


def neighbors(code: str) -> list[str]:
    """The 8 cells around a code, same size, clockwise from North.
    Search a code plus its neighbours so places just across a grid line are not missed."""
    steps = ((0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1))
    return [move(code, e, n) for e, n in steps]


def shorten(code: str, precision: str | int) -> str:
    """Reduce precision by dropping digits from the second group, e.g.
    TRZ-55511-79566 -> TRZ-55511 (1 km)."""
    c = parse(code)
    fine = _fine_for(precision)
    if fine > len(c.fine):
        raise OAVGError("Cannot add precision that the code does not have")
    return str(OAVGCode(c.anchor, c.coarse, c.fine[:fine]))


def normalize(code: str) -> str:
    """Canonical form for links and storage: upper case, groups joined by '-'."""
    return str(parse(code))


def display(code: str) -> str:
    """Form for people: groups separated by spaces, e.g. 'TRZ 55511 79566'."""
    return parse(code).display()


def distance_from_anchor_m(code: str) -> float:
    """Exact ground distance (m) from the airport to the cell centre: sqrt(X^2 + Y^2)."""
    _, x, y = decode_grid(code)
    return math.hypot(x, y)


def distance(code1: str, code2: str) -> float:
    """Ground distance in metres between two codes (works across different airports)."""
    return distance_m(*decode(code1, 9), *decode(code2, 9))


_COMPASS = ("N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW")


def describe(code: str) -> str:
    """Plain-language reading, e.g. '7.2 km NNW of TRZ (Tiruchirappalli International Airport)'."""
    c = parse(code)
    _, x, y = decode_grid(code)
    d = math.hypot(x, y)
    bearing = (math.degrees(math.atan2(x, y)) + 360) % 360
    point = _COMPASS[int((bearing + 11.25) // 22.5) % 16]
    dist = f"{d / 1000:.1f} km" if d < 10_000 else f"{d / 1000:,.0f} km"
    return f"{dist} {point} of {c.anchor} ({get_anchor(c.anchor).name})"


# --------------------------------------------------------------------------
# Command line:  airportvector encode 10.7950461 78.6793020 [4m]
#                airportvector decode "TRZ 55511 79566"
# --------------------------------------------------------------------------

def _main(argv: list[str]) -> int:
    usage = "usage: airportvector encode LAT LON [1km|333m|111m|37m|12m|4m]  |  decode CODE"
    try:
        if len(argv) in (3, 4) and argv[0] == "encode":
            print(display(encode(float(argv[1]), float(argv[2]), argv[3] if len(argv) > 3 else DEFAULT_PRECISION)))
        elif len(argv) == 2 and argv[0] == "decode":
            lat, lon = decode(argv[1])
            print(f"{lat}, {lon}")
            print(describe(argv[1]))
        else:
            print(usage)
            return 2
    except (OAVGError, ValueError) as exc:
        print(f"error: {exc}")
        return 1
    return 0


def main() -> None:
    """Entry point for the `airportvector` command."""
    import sys
    raise SystemExit(_main(sys.argv[1:]))


if __name__ == "__main__":
    main()
