# Copyright (c) 2026 AirportVector Authors
# This source code is licensed under the Business Source License 1.1 (BSL).
# Free for development, non-commercial use, and internal deployment.
# Commercial SaaS hosting or paid API distribution is strictly prohibited.
# See LICENSE.md in the root directory for full terms.
"""
AirportVector - reference implementation of the Open Airport Vector Grid (OAVG) v2.1.

Every point on Earth is coded from its NEAREST commercial airport:

    TRZ-D04200355  =  Trichy airport, North-West (near band),
                      X = 0420 (4,200 m West), Y = 0355 (3,550 m North), 10 m cell

The sector letter shows direction AND distance band:
    A B C D  = NE SE SW NW, under 100 km          (digits as normal)
    E F G H  = NE SE SW NW, 100 - 999 km          (+1 digit per axis)
    I J K L  = NE SE SW NW, 1,000 - 9,999 km      (+2 digits per axis)

Pure Python, no dependencies, works offline. Full spec: https://airportvector.org/spec-v2.1.pdf
"""
from __future__ import annotations

import csv
import math
import os
import re
from dataclasses import dataclass

__version__ = "2.1.1"
SPEC_VERSION = "2.1"

# --------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------

#: precision name -> base digits per axis. Cell size = 10 ** (5 - base) metres.
PRECISIONS = {"1km": 2, "100m": 3, "10m": 4, "1m": 5}
_PRECISION_NAME = {v: k for k, v in PRECISIONS.items()}
DEFAULT_PRECISION = "10m"

SECTORS = "ABCD"                 # NE, SE, SW, NW (clockwise)
MAX_BAND = 2                     # bands 0..2 -> letters A..L
LETTERS = "ABCDEFGHIJKL"
BAND_NAMES = ("near", "regional", "far")
DIRECTIONS = ("North-East", "South-East", "South-West", "North-West")

#: band b holds points with max(|X|, |Y|) < BAND_LIMIT_M[b]
BAND_LIMIT_M = tuple(100_000 * 10 ** b for b in range(MAX_BAND + 1))

DEFAULT_REGISTRY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "anchors.csv")

_CODE_RE = re.compile(r"^([A-Z]{3})-([A-L])([0-9]+)(?:\.([0-9]+))?$", re.ASCII)
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
    sector: str     # A=NE, B=SE, C=SW, D=NW  (quadrant, independent of band)
    band: int       # 0 near (A-D), 1 regional (E-H), 2 far (I-L)
    x: int          # cells East (NE/SE) or West (SW/NW)
    y: int          # cells North (NE/NW) or South (SE/SW)
    base: int       # base digits per axis from precision (2..5)

    @property
    def digits(self) -> int:
        return self.base + self.band

    @property
    def cell_size_m(self) -> int:
        return 10 ** (5 - self.base)

    @property
    def precision(self) -> str:
        return _PRECISION_NAME[self.base]

    @property
    def letter(self) -> str:
        return LETTERS[SECTORS.index(self.sector) + 4 * self.band]

    def __str__(self) -> str:
        d = self.digits
        return f"{self.anchor}-{self.letter}{self.x:0{d}d}{self.y:0{d}d}"

    def display(self) -> str:
        """Human-friendly form with a dot between X and Y, e.g. TRZ-D0420.0355."""
        d = self.digits
        return f"{self.anchor}-{self.letter}{self.x:0{d}d}.{self.y:0{d}d}"


def _base_for(precision: str | int) -> int:
    if isinstance(precision, int) and precision in PRECISIONS.values():
        return precision
    key = str(precision).lower().replace(" ", "")
    if key not in PRECISIONS:
        raise OAVGError(f"Unknown precision {precision!r}; use one of {list(PRECISIONS)}")
    return PRECISIONS[key]


def _sector(x: float, y: float) -> str:
    # Tie rule: exactly zero counts as East / North.
    if x >= 0:
        return "A" if y >= 0 else "B"
    return "D" if y >= 0 else "C"


def _band_of(ax: float, ay: float) -> int:
    if not (math.isfinite(ax) and math.isfinite(ay)):
        raise OAVGError("Grid distances must be finite numbers")
    m = max(ax, ay)
    for b, limit in enumerate(BAND_LIMIT_M):
        if m < limit:
            return b
    raise OAVGError(f"Location is {m / 1000:,.3f} km from the anchor on one axis; "
                    f"it must be under {BAND_LIMIT_M[-1] / 1000:,.0f} km")


def encode_grid(anchor: str, x: float, y: float, precision: str | int = DEFAULT_PRECISION) -> str:
    """Encode grid metres (X, Y) from an anchor. Truncates (never rounds)."""
    a = get_anchor(anchor)
    base = _base_for(precision)
    band = _band_of(abs(x), abs(y))
    cell = 10 ** (5 - base)
    return str(OAVGCode(a.code, _sector(x, y), band, int(abs(x) // cell), int(abs(y) // cell), base))


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
    """lat/lon (degrees, WGS84) -> OAVG code.

    precision: "1km", "100m", "10m" (default) or "1m".
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
    """Validate and split a code. Accepts any letter case and the dotted display form."""
    if not isinstance(code, str):
        raise OAVGError("Code must be a string")
    if not code.isascii() or len(code) > 40:
        raise OAVGError(f"Invalid OAVG code {code[:40]!r}: use only A-Z, 0-9, '-' and '.'")
    m = _CODE_RE.match(code.strip().upper())
    if not m:
        raise OAVGError(f"Invalid OAVG code {code!r}. Expected e.g. TRZ-D04200355")
    anchor, letter, first, second = m.groups()
    if second is not None:
        if len(first) != len(second):
            raise OAVGError(f"Invalid code {code!r}: X and Y must have the same number of digits")
        digits = first + second
    else:
        digits = first
    idx = LETTERS.index(letter)
    sector, band = SECTORS[idx % 4], idx // 4
    if len(digits) % 2:
        raise OAVGError(f"Invalid code {code!r}: odd number of digits")
    d = len(digits) // 2
    base = d - band
    if base not in _PRECISION_NAME:
        lo, hi = 2 + band, 5 + band
        raise OAVGError(f"Invalid code {code!r}: sector {letter} needs {lo}-{hi} digits per axis (got {d})")
    x, y = int(digits[:d]), int(digits[d:])
    if band > 0 and max(x, y) < 10 ** (d - 1):
        raise OAVGError(f"Invalid code {code!r}: this location belongs in a nearer band "
                        f"(use letter {LETTERS[SECTORS.index(sector) + 4 * (band - 1)]})")
    get_anchor(anchor)  # raises if unknown
    return OAVGCode(anchor, sector, band, x, y, base)


def _signed_index(c: OAVGCode) -> tuple[int, int]:
    i = c.x if c.sector in "AB" else -c.x - 1
    j = c.y if c.sector in "AD" else -c.y - 1
    return i, j


def _from_index(anchor: str, i: int, j: int, base: int) -> OAVGCode:
    x = i if i >= 0 else -i - 1
    y = j if j >= 0 else -j - 1
    cell = 10 ** (5 - base)
    band = _band_of(x * cell, y * cell)   # a cell never straddles a band edge
    sector = ("A" if j >= 0 else "B") if i >= 0 else ("D" if j >= 0 else "C")
    return OAVGCode(anchor, sector, band, x, y, base)


def decode_grid(code: str) -> tuple[str, float, float]:
    """Code -> (anchor, X, Y) of the cell centre, in metres."""
    c = parse(code)
    i, j = _signed_index(c)
    size = c.cell_size_m
    return c.anchor, (i + 0.5) * size, (j + 0.5) * size


def decode(code: str, ndigits: int = 6) -> tuple[float, float]:
    """Code -> (lat, lon) of the cell centre, rounded to `ndigits` decimals."""
    anchor, x, y = decode_grid(code)
    lat, lon = from_grid(anchor, x, y)
    return round(lat, ndigits), round(lon, ndigits)


def cell_polygon(code: str) -> list[tuple[float, float]]:
    """The cell's 4 corners as (lat, lon), in grid order: (-X,-Y), (+X,-Y), (+X,+Y), (-X,+Y).
    Use this to draw the cell on a map. (Near the dateline, longitudes may jump by 360.)"""
    c = parse(code)
    i, j = _signed_index(c)
    s = c.cell_size_m
    return [from_grid(c.anchor, gx * s, gy * s) for gx, gy in ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))]


def move(code: str, east_cells: int = 0, north_cells: int = 0) -> str:
    """Shift a code by whole cells (negative = West / South). Handles sector and band changes."""
    for v in (east_cells, north_cells):
        if isinstance(v, bool) or not isinstance(v, int):
            raise OAVGError(f"Cells to move must be whole numbers, got {v!r}")
    c = parse(code)
    i, j = _signed_index(c)
    return str(_from_index(c.anchor, i + east_cells, j + north_cells, c.base))


def shorten(code: str, precision: str | int) -> str:
    """Reduce precision by truncating each half (X and Y), e.g. TRZ-D0420303554 -> TRZ-D04200355."""
    c = parse(code)
    base = _base_for(precision)
    if base > c.base:
        raise OAVGError("Cannot add precision that the code does not have")
    cut = 10 ** (c.base - base)
    return str(OAVGCode(c.anchor, c.sector, c.band, c.x // cut, c.y // cut, base))


def normalize(code: str) -> str:
    """Canonical form: upper case, no dot."""
    return str(parse(code))


def distance_from_anchor_m(code: str) -> float:
    """Exact ground distance (m) from the airport to the cell centre: sqrt(X^2 + Y^2)."""
    _, x, y = decode_grid(code)
    return math.hypot(x, y)


def distance(code1: str, code2: str) -> float:
    """Ground distance in metres between two codes (works across different airports)."""
    return distance_m(*decode(code1, 9), *decode(code2, 9))


_COMPASS = ("N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW")


def describe(code: str) -> str:
    """Plain-language reading, e.g. '5.5 km NW of TRZ (Tiruchirappalli International Airport)'."""
    c = parse(code)
    _, x, y = decode_grid(code)
    d = math.hypot(x, y)
    bearing = (math.degrees(math.atan2(x, y)) + 360) % 360
    point = _COMPASS[int((bearing + 11.25) // 22.5) % 16]
    dist = f"{d / 1000:.1f} km" if d < 10_000 else f"{d / 1000:,.0f} km"
    return f"{dist} {point} of {c.anchor} ({get_anchor(c.anchor).name})"


# --------------------------------------------------------------------------
# Command line:  python airportvector.py encode 10.795 78.679 [10m]
#                python airportvector.py decode TRZ-D04200355
# --------------------------------------------------------------------------

def _main(argv: list[str]) -> int:
    usage = "usage: airportvector encode LAT LON [1km|100m|10m|1m]  |  decode CODE"
    try:
        if len(argv) in (3, 4) and argv[0] == "encode":
            print(encode(float(argv[1]), float(argv[2]), argv[3] if len(argv) > 3 else DEFAULT_PRECISION))
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
