"""Conformance tests for OAVG v2.1 (see docs/spec-v2.1.pdf).

Run:  pip install -r requirements-dev.txt  &&  pytest
"""
import os
import random
import sys

import pytest

import airportvector as av  # noqa: E402

P = (10.7950461, 78.6793020)  # illustrative point near Trichy Central Bus Stand


# --- Near band (A-D): spec vectors -------------------------------------------

@pytest.mark.parametrize("precision,expected", [
    ("1km", "TRZ-D0403"),
    ("100m", "TRZ-D042035"),
    ("10m", "TRZ-D04200355"),
    ("1m", "TRZ-D0420303554"),
])
def test_encode_near(precision, expected):
    assert av.encode(*P, precision=precision) == expected


def test_default_precision_is_10m():
    assert av.encode(*P) == "TRZ-D04200355"


@pytest.mark.parametrize("code,expected", [
    ("TRZ-D04200355", (10.795052, 78.679291)),
    ("TRZ-D0420303554", (10.795047, 78.679305)),
])
def test_decode_near(code, expected):
    assert av.decode(code) == expected


# --- Every band: real far-away places, nearest airport -----------------------

@pytest.mark.parametrize("lat,lon,expected", [
    (51.5074, -0.1278, "LCY-D12710024"),          # London: near band
    (23.5, 12.0, "DJG-F2590508465"),              # Sahara: regional band, SE
    (0.0, -30.0, "FEN-E2699342596"),              # mid-Atlantic: regional band, NE
    (-48.8767, -123.3933, "IPC-K104561248302"),   # Point Nemo: far band, SW
    (-75.85, 67.95, "PLZ-J117660500993"),         # farthest point from any airport
    (-90.0, 0.0, "USH-J000000392217"),            # South Pole
])
def test_encode_global(lat, lon, expected):
    assert av.encode(lat, lon) == expected


def test_every_point_on_globe_gets_a_code():
    random.seed(11)
    for _ in range(300):
        lat, lon = random.uniform(-90, 90), random.uniform(-180, 180)
        code = av.encode(lat, lon)
        dlat, dlon = av.decode(code, 9)
        assert av.distance_m(lat, lon, dlat, dlon) < 10  # within one 10 m cell diagonal


# --- Band letters ---------------------------------------------------------------

@pytest.mark.parametrize("x,y,letter", [
    (50_000, 50_000, "A"), (50_000, -50_000, "B"), (-50_000, -50_000, "C"), (-50_000, 50_000, "D"),
    (150_000, 5, "E"), (5, -150_000, "F"), (-150_000, -5, "G"), (-5, 150_000, "H"),
    (1_500_000, 0, "I"), (0, -1_500_000, "J"), (-1_500_000, -1, "K"), (-1_500_000, 0, "L"),
])
def test_letter_is_sector_plus_band(x, y, letter):
    assert av.encode_grid("TRZ", x, y, "1km")[4] == letter


def test_band_uses_larger_axis_and_adds_digits():
    assert av.encode_grid("TRZ", 99_999.9, 99_999.9, "1m") == "TRZ-A9999999999"
    assert av.encode_grid("TRZ", 100_000.0, 0, "1m") == "TRZ-E100000000000"
    assert av.encode_grid("TRZ", -8_899_000, 1_000, "1km") == "TRZ-L88990001"   # D + 8 = L
    with pytest.raises(av.OAVGError):
        av.encode_grid("TRZ", 10_000_000, 0)


def test_band_bonus_distance_is_exact():
    lat, lon = av.from_grid("TRZ", -3000.0, 4000.0)
    assert av.distance_m(10.762915, 78.717741, lat, lon) == pytest.approx(5000.0, abs=1e-3)


# --- Movement, sector and band crossings ----------------------------------------

@pytest.mark.parametrize("east,north,expected", [
    (0, 50, "TRZ-D04200405"),
    (0, -50, "TRZ-D04200305"),
    (50, 0, "TRZ-D03700355"),
    (-50, 0, "TRZ-D04700355"),
    (430, 0, "TRZ-A00090355"),     # crosses the N-S axis: D -> A
])
def test_move(east, north, expected):
    assert av.move("TRZ-D04200355", east, north) == expected


def test_move_across_band_edge():
    assert av.move("TRZ-A9900", 1, 0) == "TRZ-E100000"
    assert av.move("TRZ-E100000", -1, 0) == "TRZ-A9900"
    assert av.move("TRZ-D00000331", 1, 0) == "TRZ-A00000331"
    assert av.move("TRZ-C00000000", 1, 1) == "TRZ-A00000000"


def test_move_matches_real_movement():
    _, x, y = av.decode_grid("TRZ-D04200355")
    assert av.move("TRZ-D04200355", 10, -7) == av.encode_grid("TRZ", x + 100, y - 70)


# --- Truncation & prefix property --------------------------------------------------

def test_shorten_near_and_far():
    assert av.shorten("TRZ-D0420303554", "10m") == "TRZ-D04200355"
    assert av.shorten("TRZ-D0420303554", "1km") == "TRZ-D0403"
    far = av.encode(-48.8767, -123.3933, "1m")
    for prec in ("1km", "100m", "10m"):
        assert av.shorten(far, prec) == av.encode(-48.8767, -123.3933, prec)


def test_roundtrip_every_band_every_precision():
    random.seed(42)
    for anchor in ("TRZ", "LAX"):
        for limit in (99_999, 999_999, 9_999_999):
            for _ in range(400):
                x, y = random.uniform(-limit, limit), random.uniform(-limit, limit)
                if (x * x + y * y) ** 0.5 > 14_000_000:
                    continue
                lat, lon = av.from_grid(anchor, x, y)
                for prec, base in av.PRECISIONS.items():
                    code = av.encode(lat, lon, prec, anchor=anchor)
                    _, dx, dy = av.decode_grid(code)
                    half = 10 ** (5 - base) / 2
                    assert abs(dx - x) <= half + 1e-3 and abs(dy - y) <= half + 1e-3, code


# --- Parsing & validation ------------------------------------------------------------

def test_parse_display_form_and_case():
    c = av.parse("trz-d0420.0355")
    assert (c.anchor, c.sector, c.band, c.x, c.y, c.cell_size_m) == ("TRZ", "D", 0, 420, 355, 10)
    assert c.display() == "TRZ-D0420.0355"
    assert av.normalize("trz-d0420.0355") == "TRZ-D04200355"
    far = av.parse("IPC-K104561248302")
    assert (far.sector, far.band, far.precision) == ("C", 2, "10m")


@pytest.mark.parametrize("bad", [
    "TRZD04200355",        # no hyphen
    "TRZ-M04200355",       # letter beyond L
    "TRZ-D0420035",        # odd digit count
    "TRZ-D033",            # too short
    "TRZ-D042003550000",   # too long for band 0 (6 per axis)
    "TRZ-E0100",           # band 1 needs 3-6 digits per axis
    "TRZ-E050050",         # non-minimal: fits band 0 -> must be A
    "TRZ-D042.03550",      # uneven halves
    "XXX-D04200355",       # unknown anchor
    "TRZ-D0420O355",       # letter O instead of zero
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


# --- Anchors ------------------------------------------------------------------------

def test_nearest_anchor():
    assert av.encode(13.0, 80.2).startswith("MAA-")
    assert av.encode(10.80, 78.68).startswith("TRZ-")


def test_registry_is_three_letter_unique():
    reg = av.registry()
    assert len(reg) > 4000
    assert all(len(c) == 3 and c.isalpha() for c in reg)


def test_retired_anchor_decodes_but_does_not_encode():
    reg = dict(av.registry())
    reg["QQQ"] = av.Anchor("QQQ", "Closed", 10.5, 78.5, "retired")
    av.use_registry(reg)
    try:
        assert av.decode("QQQ-A00000000")
        with pytest.raises(av.OAVGError):
            av.encode(10.5, 78.5, anchor="QQQ")
        assert not av.encode(10.5, 78.5).startswith("QQQ")
    finally:
        av.use_registry(av.load_registry())


# --- Human helpers ---------------------------------------------------------------------

def test_describe_and_distance():
    assert av.describe("TRZ-D04200355") == "5.5 km NW of TRZ (Tiruchirappalli International Airport)"
    assert av.describe("IPC-K104561248302").startswith("2,694 km SSW of IPC")
    assert av.distance_from_anchor_m("TRZ-D04200355") == pytest.approx((4205 ** 2 + 3555 ** 2) ** 0.5)
    assert av.distance("TRZ-D04200355", "TRZ-D04200405") == pytest.approx(500, abs=1)
    assert 280_000 < av.distance("TRZ-D04200355", av.encode(13.0, 80.2)) < 300_000


# --- Cross-check against PROJ (skipped if pyproj is not installed) ---------------------

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


# --- CLI ---------------------------------------------------------------------------------

def test_cli(capsys):
    assert av._main(["encode", "10.7950461", "78.6793020"]) == 0
    assert capsys.readouterr().out.strip() == "TRZ-D04200355"
    assert av._main(["decode", "TRZ-D04200355"]) == 0
    out = capsys.readouterr().out
    assert "10.795052, 78.679291" in out and "5.5 km NW of TRZ" in out
    assert av._main(["decode", "bad"]) == 1


# --- v2.1.1 regression tests (QC findings) ----------------------------------------------

def test_poles_have_one_code_regardless_of_longitude():
    for lat in (90.0, -90.0):
        codes = {av.encode(lat, lon) for lon in range(-180, 181, 3)}
        assert len(codes) == 1, codes
    assert av.encode(-90.0, 0.0) == "USH-J000000392217"
    assert av.encode(90.0, 0.0).startswith("LYR-I")


def test_dateline_same_code():
    assert av.encode(0.0, 180.0) == av.encode(0.0, -180.0)
    assert av.encode(-17.8, 180.0) == av.encode(-17.8, -180.0)


def test_nearest_matches_brute_force():
    random.seed(5)
    active = [a for a in av.registry().values() if a.status == "active"]
    for _ in range(25):
        lat, lon = random.uniform(-90, 90), random.uniform(-180, 180)
        best = min(active, key=lambda a: (av.distance_m(lat, lon, a.lat, a.lon), a.code))
        assert av.nearest_anchor(lat, lon).code == best.code


def test_stable_roundtrip_with_same_anchor():
    random.seed(9)
    for _ in range(300):
        lat, lon = random.uniform(-85, 85), random.uniform(-180, 180)
        for prec in av.PRECISIONS:
            c = av.encode(lat, lon, prec)
            dlat, dlon = av.decode(c, 9)
            assert av.encode(dlat, dlon, prec, anchor=c[:3]) == c


def test_rejects_non_ascii_and_bad_types():
    for bad in ("TRZ-D٠٤٢٠٠٣٥٥", "ıpc-k104561248302", "TRZ-D０４２００３５５", "A" * 1000):
        with pytest.raises(av.OAVGError):
            av.parse(bad)
    for args in (("10", "78"), (True, 78.0), (float("nan"), 78.0), (10.0, float("inf"))):
        with pytest.raises(av.OAVGError):
            av.encode(*args)
    with pytest.raises(av.OAVGError):
        av.move("TRZ-D04200355", 1.5, 0)
    with pytest.raises(av.OAVGError):
        av.move("TRZ-D04200355", True, 0)
    with pytest.raises(av.OAVGError):
        av.encode_grid("TRZ", 5, float("nan"))


def test_move_beyond_far_band_errors():
    with pytest.raises(av.OAVGError):
        av.move("TRZ-L99990001", -1, 0)


def test_antipodal_distance_does_not_crash():
    d = av.distance_m(10.0, 20.0, -10.0, -160.0)   # exact antipodes
    assert 19_900_000 < d < 20_100_000
    with pytest.raises(av.OAVGError, match="out of range"):
        av.encode(-10.7629, 78.7177 - 180, anchor="TRZ")


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


def test_registry_shape():
    reg = av.registry()
    assert len(reg) == 4133
    assert {a.status for a in reg.values()} == {"active"}


def test_cell_polygon():
    poly = av.cell_polygon("TRZ-D04200355")
    assert len(poly) == 4
    for lat, lon in poly:
        assert av.distance_m(lat, lon, *av.decode("TRZ-D04200355", 9)) < 8  # half-diagonal of 10 m cell ~7.07 m


def test_cli_rejects_extra_args():
    assert av._main(["encode", "1", "1", "10m", "junk"]) == 2
