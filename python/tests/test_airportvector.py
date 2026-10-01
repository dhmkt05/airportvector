"""Conformance tests for OAVG v4 (keypad grid).

Run:  pip install ./python pytest pyproj  &&  pytest python/tests
"""
import math
import random

import pytest

import airportvector as av  # noqa: E402

P = (10.7950461, 78.6793020)  # illustrative point near Trichy Central Bus Stand
FULL = "TRZ-55511-79566"


# --- Independent oracle: the keypad grid computed level by level ----------------------

def keypad_oracle(x, y, coarse, fine):
    """Split the zone 3 x 3 again and again, naming parts like a phone keypad."""
    size = av.BASE_ZONE_M * 3 ** (coarse - 5)
    cx = cy = 0.0
    out = ""
    for _ in range(coarse + fine):
        c = size / 3
        left, top = cx - size / 2, cy + size / 2
        col = min(2, max(0, int((x - left) // c)))
        row = min(2, max(0, int((top - y) // c)))
        out += str(row * 3 + col + 1)
        cx, cy, size = left + c * (col + 0.5), top - c * (row + 0.5), c
    return out


def test_matches_level_by_level_oracle():
    random.seed(3)
    for _ in range(3000):
        x, y = random.uniform(-121_000, 121_000), random.uniform(-121_000, 121_000)
        code = av.parse(av.encode_grid("TRZ", x, y))
        assert code.coarse + code.fine == keypad_oracle(x, y, 5, 5), (x, y)


def test_airport_is_all_fives():
    assert av.encode_grid("TRZ", 0.0, 0.0) == "TRZ-55555-55555"
    assert av.encode_grid("TRZ", 0.4, -0.4) == "TRZ-55555-55555"


@pytest.mark.parametrize("x,y,first", [
    (0, 60_000, "2"), (60_000, 0, "6"), (0, -60_000, "8"), (-60_000, 0, "4"),
    (60_000, 60_000, "3"), (-60_000, 60_000, "1"), (60_000, -60_000, "9"), (-60_000, -60_000, "7"),
])
def test_first_digit_is_keypad_direction(x, y, first):
    assert av.encode_grid("TRZ", x, y, "1km")[4] == first


def test_leading_fives_measure_distance():
    for km, fives in ((30, 1), (10, 2), (3, 3), (1, 4)):
        c = av.parse(av.encode_grid("TRZ", km * 1000.0, 0.0))
        assert c.leading_fives == fives, km


# --- Spec vectors near Trichy ----------------------------------------------------------

@pytest.mark.parametrize("precision,expected", [
    ("1km", "TRZ-55511"),
    ("333m", "TRZ-55511-7"),
    ("111m", "TRZ-55511-79"),
    ("37m", "TRZ-55511-795"),
    ("12m", "TRZ-55511-7956"),
    ("4m", FULL),
])
def test_encode_near(precision, expected):
    assert av.encode(*P, precision=precision) == expected


def test_default_precision_is_4m():
    assert av.encode(*P) == FULL
    assert av.display(FULL) == "TRZ 55511 79566"


def test_decode_near():
    assert av.decode(FULL) == (10.795057, 78.679284)
    assert av.distance_m(*P, *av.decode(FULL, 9)) < 3  # half-diagonal of a 4.1 m cell is 2.9 m


# --- Far places: longer first group, implied 5s ------------------------------------------

@pytest.mark.parametrize("lat,lon,expected", [
    (51.5074, -0.1278, "LCY-55444-38173"),               # London: inside the 243 km zone
    (23.5, 12.0, "DJG-686479-26417"),                     # Sahara: 1 implied level
    (0.0, -30.0, "FEN-2983825-54956"),                    # mid-Atlantic: 2 implied levels
    (-48.8767, -123.3933, "IPC-84772643-65933"),          # Point Nemo
    (-75.85, 67.95, "PLZ-837424116-41968"),               # farthest point from any airport
    (-90.0, 0.0, "USH-822858828-82252"),                  # South Pole
])
def test_encode_global(lat, lon, expected):
    assert av.encode(lat, lon) == expected


def test_zone_edges():
    assert len(av.parse(av.encode_grid("TRZ", 121_499.9, 0)).coarse) == 5
    assert len(av.parse(av.encode_grid("TRZ", 121_500.0, 0)).coarse) == 6
    assert len(av.parse(av.encode_grid("TRZ", -364_499.0, 0)).coarse) == 6
    assert len(av.parse(av.encode_grid("TRZ", 9_841_000, 0)).coarse) == 9
    with pytest.raises(av.OAVGError):
        av.encode_grid("TRZ", 9_841_500, 0)


def test_long_first_group_never_starts_with_5():
    random.seed(4)
    for _ in range(500):
        x, y = random.uniform(-9e6, 9e6), random.uniform(-9e6, 9e6)
        c = av.parse(av.encode_grid("TRZ", x, y, "1km"))
        assert c.extra == 0 or c.coarse[0] != "5"


def test_implied_fives_parse_to_the_same_place():
    assert av.normalize("TRZ-555511-79566") == FULL
    assert av.normalize("TRZ 5555511 79566") == FULL


def test_every_point_on_globe_gets_a_code():
    random.seed(11)
    for _ in range(300):
        lat, lon = random.uniform(-90, 90), random.uniform(-180, 180)
        code = av.encode(lat, lon)
        dlat, dlon = av.decode(code, 9)
        assert av.distance_m(lat, lon, dlat, dlon) < 3, code


# --- Prefix = area ----------------------------------------------------------------------

def test_prefix_is_a_square():
    random.seed(8)
    for _ in range(300):
        x, y = random.uniform(-120_000, 120_000), random.uniform(-120_000, 120_000)
        full = av.encode_grid("TRZ", x, y)
        for prec in av.PRECISIONS:
            assert full.startswith(av.encode_grid("TRZ", x, y, prec))


def test_shorten():
    assert av.shorten(FULL, "1km") == "TRZ-55511"
    assert av.shorten(FULL, "37m") == "TRZ-55511-795"
    far = av.encode(-48.8767, -123.3933)
    for prec in av.PRECISIONS:
        assert av.shorten(far, prec) == av.encode(-48.8767, -123.3933, prec)
    with pytest.raises(av.OAVGError):
        av.shorten("TRZ-55511", "4m")


# --- Movement and neighbours --------------------------------------------------------------

def test_move_matches_real_movement():
    _, x, y = av.decode_grid(FULL)
    s = av.parse(FULL).cell_size_m
    assert av.move(FULL, 10, -7) == av.encode_grid("TRZ", x + 10 * s, y - 7 * s)


def test_move_across_zone_edge():
    edge = av.encode_grid("TRZ", 121_000.0, 0.0, "1km")
    out = av.move(edge, 1, 0)
    assert len(av.parse(out).coarse) == 6
    assert av.move(out, -1, 0) == edge


def test_neighbors():
    ns = av.neighbors(FULL)
    assert len(ns) == 8 and len(set(ns)) == 8 and FULL not in ns
    assert ns[0] == av.move(FULL, 0, 1) and ns[2] == av.move(FULL, 1, 0)
    for n in ns:
        assert av.distance(FULL, n) < 6


# --- Round trips -----------------------------------------------------------------------------

def test_roundtrip_every_zone_every_precision():
    random.seed(42)
    for anchor in ("TRZ", "LAX"):
        for limit in (120_000, 360_000, 3_000_000, 9_000_000):
            for _ in range(150):
                x, y = random.uniform(-limit, limit), random.uniform(-limit, limit)
                if math.hypot(x, y) > 14_000_000:
                    continue
                lat, lon = av.from_grid(anchor, x, y)
                for prec, n in av.PRECISIONS.items():
                    code = av.encode(lat, lon, prec, anchor=anchor)
                    _, dx, dy = av.decode_grid(code)
                    half = 1000 / 3 ** n / 2
                    assert abs(dx - x) <= half + 1e-3 and abs(dy - y) <= half + 1e-3, code


def test_stable_roundtrip_with_same_anchor():
    random.seed(9)
    for _ in range(300):
        lat, lon = random.uniform(-85, 85), random.uniform(-180, 180)
        for prec in av.PRECISIONS:
            c = av.encode(lat, lon, prec)
            dlat, dlon = av.decode(c, 9)
            assert av.encode(dlat, dlon, prec, anchor=c[:3]) == c


# --- Parsing & validation ----------------------------------------------------------------------

@pytest.mark.parametrize("text", [
    "TRZ-55511-79566", "trz 55511 79566", "TRZ 55511-79566", "TRZ5551179566", "TRZ-5551179566",
    "  trz-55511-79566  ", "TRZ 55511.79566",
])
def test_accepts_written_forms(text):
    assert av.normalize(text) == FULL


def test_single_block_is_full_code_or_first_group():
    assert av.parse("TRZ5551179566").fine == "79566"
    assert av.parse("IPC8477264365933").coarse == "84772643"
    assert av.parse("IMP-684476").coarse == "684476"
    assert av.normalize("IMP 684476") == "IMP-684476"


def test_parse_fields():
    c = av.parse("trz 55511 795")
    assert (c.anchor, c.coarse, c.fine, c.precision, c.extra, c.leading_fives) == ("TRZ", "55511", "795", "37m", 0, 3)
    assert c.display() == "TRZ 55511 795" and str(c) == "TRZ-55511-795"
    assert av.parse("TRZ 55511").precision == "1km"
    far = av.parse("IPC-84772643-65933")
    assert (far.extra, far.zone_m) == (3, 243_000 * 27)


@pytest.mark.parametrize("bad", [
    "TRZ-5551",              # first group too short
    "TRZ-55511-795661",      # second group too long
    "TRZ-55510-79566",       # 0 is not a keypad digit
    "TRZ-55511796660",       # single block with a 0
    "TRZ-1234567891-11111",  # first group too long
    "XXX-55511-79566",       # unknown anchor
    "TRZ-D04200355",         # old v2 code
    "TRZ-55511-7956O",       # letter O
    "",
])
def test_rejects_invalid_codes(bad):
    with pytest.raises(av.OAVGError):
        av.parse(bad)


def test_rejects_bad_inputs():
    with pytest.raises(av.OAVGError):
        av.encode(91, 0)
    with pytest.raises(av.OAVGError):
        av.encode(*P, precision="5m")
    for bad in ("TRZ-٥٥٥١١", "TRZ-５５５１１", "A" * 1000):
        with pytest.raises(av.OAVGError):
            av.parse(bad)
    for args in (("10", "78"), (True, 78.0), (float("nan"), 78.0), (10.0, float("inf"))):
        with pytest.raises(av.OAVGError):
            av.encode(*args)
    for bad_move in ((1.5, 0), (True, 0)):
        with pytest.raises(av.OAVGError):
            av.move(FULL, *bad_move)
    with pytest.raises(av.OAVGError):
        av.encode_grid("TRZ", 5, float("nan"))


# --- Anchors -------------------------------------------------------------------------------------

def test_nearest_anchor():
    assert av.encode(13.0, 80.2).startswith("MAA-")
    assert av.encode(10.80, 78.68).startswith("TRZ-")


def test_nearest_matches_brute_force():
    random.seed(5)
    active = [a for a in av.registry().values() if a.status == "active"]
    for _ in range(25):
        lat, lon = random.uniform(-90, 90), random.uniform(-180, 180)
        best = min(active, key=lambda a: (av.distance_m(lat, lon, a.lat, a.lon), a.code))
        assert av.nearest_anchor(lat, lon).code == best.code


def test_registry_shape():
    reg = av.registry()
    assert len(reg) == 4133
    assert all(len(c) == 3 and c.isalpha() for c in reg)
    assert {a.status for a in reg.values()} == {"active"}


def test_retired_anchor_decodes_but_does_not_encode():
    reg = dict(av.registry())
    reg["QQQ"] = av.Anchor("QQQ", "Closed", 10.5, 78.5, "retired")
    av.use_registry(reg)
    try:
        assert av.decode("QQQ-55555-55555")
        with pytest.raises(av.OAVGError):
            av.encode(10.5, 78.5, anchor="QQQ")
        assert not av.encode(10.5, 78.5).startswith("QQQ")
    finally:
        av.use_registry(av.load_registry())


def test_registry_validation(tmp_path):
    good = "code,type,name,lat,lon,status\nAAA,IATA,Test,1,2,active\n"
    (tmp_path / "ok.csv").write_text(good)
    assert "AAA" in av.load_registry(str(tmp_path / "ok.csv"))
    for bad_row in ("AAA,IATA,Test,95,2,active", "AAA,IATA,Test,nan,2,active",
                    "AAA,IATA,Test,1,2,actve", "AAA,IATA,,1,2,active", "AA1,IATA,Test,1,2,active"):
        f = tmp_path / "bad.csv"
        f.write_text("code,type,name,lat,lon,status\n" + bad_row + "\n")
        with pytest.raises(av.OAVGError):
            av.load_registry(str(f))


# --- Human helpers -----------------------------------------------------------------------------------

def test_describe_and_distance():
    assert av.describe(FULL) == "5.5 km NW of TRZ (Tiruchirappalli International Airport)"
    assert av.describe("IPC-84772643-65933").startswith("2,694 km SSW of IPC")
    _, x, y = av.decode_grid(FULL)
    assert av.distance_from_anchor_m(FULL) == pytest.approx(math.hypot(x, y))
    assert 280_000 < av.distance(FULL, av.encode(13.0, 80.2)) < 300_000


def test_cell_polygon():
    poly = av.cell_polygon(FULL)
    assert len(poly) == 4
    for lat, lon in poly:
        assert av.distance_m(lat, lon, *av.decode(FULL, 9)) < 3.2  # half-diagonal of a 4.1 m cell


# --- Geodesy (unchanged from v2.1) ----------------------------------------------------------------------

def test_grid_distance_is_exact():
    lat, lon = av.from_grid("TRZ", -3000.0, 4000.0)
    a = av.get_anchor("TRZ")
    assert av.distance_m(a.lat, a.lon, lat, lon) == pytest.approx(5000.0, abs=1e-3)


def test_projection_matches_pyproj_aeqd():
    pyproj = pytest.importorskip("pyproj")
    random.seed(7)
    for code in ("TRZ", "LAX", "PLZ", "USH"):
        a = av.get_anchor(code)
        t = pyproj.Transformer.from_crs(
            "EPSG:4326", f"+proj=aeqd +lat_0={a.lat} +lon_0={a.lon} +ellps=WGS84 +units=m", always_xy=True)
        for _ in range(200):
            x, y = random.uniform(-9.9e6, 9.9e6), random.uniform(-9.9e6, 9.9e6)
            if (x * x + y * y) ** 0.5 > 14e6:
                continue
            lon, lat = t.transform(x, y, direction="INVERSE")
            gx, gy = av.to_grid(a, lat, lon)
            assert abs(gx - x) < 1e-3 and abs(gy - y) < 1e-3
            glat, glon = av.from_grid(a, x, y)
            assert abs(glat - lat) < 1e-8 and abs(((glon - lon + 180) % 360) - 180) < 1e-8


def test_poles_have_one_code_regardless_of_longitude():
    for lat in (90.0, -90.0):
        codes = {av.encode(lat, lon) for lon in range(-180, 181, 3)}
        assert len(codes) == 1, codes
    assert av.encode(90.0, 0.0).startswith("LYR-")


def test_dateline_same_code():
    assert av.encode(0.0, 180.0) == av.encode(0.0, -180.0)
    assert av.encode(-17.8, 180.0) == av.encode(-17.8, -180.0)


def test_antipodal_distance_does_not_crash():
    d = av.distance_m(10.0, 20.0, -10.0, -160.0)   # exact antipodes
    assert 19_900_000 < d < 20_100_000
    a = av.get_anchor("TRZ")
    with pytest.raises(av.OAVGError, match="out of range"):
        av.encode(-a.lat, a.lon - 180, anchor="TRZ")


# --- CLI ---------------------------------------------------------------------------------------------------

def test_cli(capsys):
    assert av._main(["encode", "10.7950461", "78.6793020"]) == 0
    assert capsys.readouterr().out.strip() == "TRZ 55511 79566"
    assert av._main(["decode", "TRZ 55511 79566"]) == 0
    out = capsys.readouterr().out
    assert "10.795057, 78.679284" in out and "5.5 km NW of TRZ" in out
    assert av._main(["decode", "bad"]) == 1
    assert av._main(["encode", "1", "1", "4m", "junk"]) == 2
