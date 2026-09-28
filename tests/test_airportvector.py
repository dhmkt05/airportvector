"""Conformance tests for OAVG v2.0 (see docs/spec-v2.pdf, Section 8).

Run:  pip install -r requirements-dev.txt  &&  pytest
"""
import os
import random
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import airportvector as av  # noqa: E402

P = (10.7950461, 78.6793020)  # illustrative point near Trichy Central Bus Stand


# --- Spec Section 8: conformance vectors ------------------------------------

@pytest.mark.parametrize("precision,expected", [
    ("1km", "TRZ-D0303"),
    ("100m", "TRZ-D033033"),
    ("10m", "TRZ-D03320331"),
    ("1m", "TRZ-D0332403312"),
])
def test_encode_vectors(precision, expected):
    assert av.encode(*P, precision=precision) == expected


def test_default_precision_is_10m():
    assert av.encode(*P) == "TRZ-D03320331"


@pytest.mark.parametrize("code,expected", [
    ("TRZ-D03320331", (10.795068, 78.679296)),
    ("TRZ-D0332403312", (10.795045, 78.679301)),
])
def test_decode_vectors(code, expected):
    assert av.decode(code) == expected


def test_tie_rule_axis_counts_as_east_north():
    assert av.encode_grid("TRZ", 0.0, 1500.0) == "TRZ-A00000150"
    assert av.encode_grid("TRZ", -0.4, 1500.0) == "TRZ-D00000150"
    assert av.encode_grid("TRZ", 0.0, 0.0) == "TRZ-A00000000"
    assert av.encode(10.7651, 78.7097) == "TRZ-A00000000"


def test_parse_display_form_and_case():
    c = av.parse("trz-d0332.0331")
    assert (c.anchor, c.sector, c.x, c.y, c.cell_size_m) == ("TRZ", "D", 332, 331, 10)
    assert c.display() == "TRZ-D0332.0331"
    assert av.normalize("trz-d0332.0331") == "TRZ-D03320331"


def test_out_of_range():
    with pytest.raises(av.OAVGError):
        av.encode_grid("TRZ", 100_000, 0)
    with pytest.raises(av.OAVGError):
        av.encode_grid("TRZ", 0, -100_000)


# --- Spec Section 7: neighbours and crossing ---------------------------------

@pytest.mark.parametrize("east,north,expected", [
    (0, 50, "TRZ-D03320381"),     # 500 m North
    (0, -50, "TRZ-D03320281"),    # 500 m South
    (50, 0, "TRZ-D02820331"),     # 500 m East
    (-50, 0, "TRZ-D03820331"),    # 500 m West
    (340, 0, "TRZ-A00070331"),    # 3.4 km East: crosses the axis D -> A
])
def test_move(east, north, expected):
    assert av.move("TRZ-D03320331", east, north) == expected


def test_axis_cells_are_neighbours():
    assert av.move("TRZ-D00000331", 1, 0) == "TRZ-A00000331"
    assert av.move("TRZ-A00000331", -1, 0) == "TRZ-D00000331"
    assert av.move("TRZ-A03310000", 0, -1) == "TRZ-B03310000"
    assert av.move("TRZ-C00000000", 1, 1) == "TRZ-A00000000"


def test_move_matches_real_movement():
    """Moving 10 cells should match encoding a point 100 m away."""
    _, e, n = av.decode_grid("TRZ-D03320331")
    assert av.move("TRZ-D03320331", 10, -7) == av.encode_grid("TRZ", e + 100, n - 70)


# --- Truncation & prefix property ---------------------------------------------

def test_coarse_code_is_prefix_of_fine_code():
    assert av.shorten("TRZ-D0332403312", "10m") == "TRZ-D03320331"
    assert av.shorten("TRZ-D0332403312", "100m") == "TRZ-D033033"
    assert av.shorten("TRZ-D0332403312", "1km") == "TRZ-D0303"
    for prec in ("1km", "100m", "10m"):
        assert av.shorten(av.encode(*P, "1m"), prec) == av.encode(*P, prec)


def test_truncates_never_rounds_and_never_overflows():
    assert av.encode_grid("TRZ", 99_999.99, 99_999.99, "1m") == "TRZ-A9999999999"
    assert av.encode_grid("TRZ", 99_999.99, 99_999.99, "1km") == "TRZ-A9999"
    assert av.encode_grid("TRZ", 19.99, 0, "10m") == "TRZ-A00010000"


def test_roundtrip_every_sector_every_precision():
    random.seed(42)
    for anchor in ("TRZ", "LAX"):
        for _ in range(5000):
            e, n = random.uniform(-99_999, 99_999), random.uniform(-99_999, 99_999)
            lat, lon = av.from_grid(anchor, e, n)
            for prec, d in av.PRECISIONS.items():
                code = av.encode(lat, lon, prec, anchor=anchor)
                _, de, dn = av.decode_grid(code)
                half = 10 ** (5 - d) / 2
                assert abs(de - e) <= half + 1e-6 and abs(dn - n) <= half + 1e-6, code


# --- Validation -----------------------------------------------------------------

@pytest.mark.parametrize("bad", [
    "TRZD03320331",       # no hyphen
    "TRZ-E03320331",      # bad sector
    "TRZ-D0332033",       # odd digit count
    "TRZ-D033",           # too short
    "TRZ-D033203310000",  # too long (14)
    "TRZ-D033.03310",     # uneven halves
    "XXX-D03320331",      # unknown anchor
    "TRZ-D0332O331",      # letter O instead of zero
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
    with pytest.raises(av.OAVGError):
        av.encode(0.0, -150.0)  # middle of the Pacific: no anchor in range
    with pytest.raises(av.OAVGError):
        av.encode(0.0, 78.7097 - 90.0)  # exactly 90 deg of longitude from TRZ must not crash


# --- Anchor selection -----------------------------------------------------------

def test_nearest_anchor_is_canonical():
    assert av.encode(13.05, 80.25).startswith("MAA-")
    assert av.encode(10.80, 78.68).startswith("TRZ-")


def test_alternate_anchor_decodes_to_same_place():
    # A point between TRZ and MAA? They are ~300 km apart, so use a synthetic registry.
    reg = dict(av.registry())
    reg["TST"] = av.Anchor("TST", "IATA", "Test", 10.90, 78.70, "active")
    av.use_registry(reg)
    try:
        lat, lon = 10.83, 78.70
        canonical = av.encode(lat, lon, "1m")
        alternate = av.encode(lat, lon, "1m", anchor="TRZ" if canonical.startswith("TST") else "TST")
        assert canonical[:3] != alternate[:3]
        a, b = av.decode(canonical), av.decode(alternate)
        assert abs(a[0] - b[0]) < 2e-5 and abs(a[1] - b[1]) < 2e-5
    finally:
        av.use_registry(av.load_registry())


def test_retired_anchor_decodes_but_does_not_encode():
    reg = dict(av.registry())
    reg["OLD"] = av.Anchor("OLD", "IATA", "Closed", 10.5, 78.5, "retired")
    av.use_registry(reg)
    try:
        assert av.decode("OLD-A00000000")
        with pytest.raises(av.OAVGError):
            av.encode(10.5, 78.5, anchor="OLD")
        assert not av.encode(10.5, 78.5).startswith("OLD")
    finally:
        av.use_registry(av.load_registry())


# --- Projection cross-check (skipped if pyproj is not installed) ------------------

def test_projection_matches_pyproj():
    pyproj = pytest.importorskip("pyproj")
    random.seed(7)
    for a in av.registry().values():
        t = pyproj.Transformer.from_crs(
            "EPSG:4326",
            f"+proj=tmerc +lat_0={a.lat} +lon_0={a.lon} +k=1 +x_0=0 +y_0=0 +ellps=WGS84",
            always_xy=True)
        for _ in range(500):
            e, n = random.uniform(-99_999, 99_999), random.uniform(-99_999, 99_999)
            lon, lat = t.transform(e, n, direction="INVERSE")
            ge, gn = av.to_grid(a, lat, lon)
            assert abs(ge - e) < 1e-3 and abs(gn - n) < 1e-3


# --- CLI --------------------------------------------------------------------------

def test_cli(capsys):
    assert av._main(["encode", "10.7950461", "78.6793020"]) == 0
    assert capsys.readouterr().out.strip() == "TRZ-D03320331"
    assert av._main(["decode", "TRZ-D03320331"]) == 0
    assert capsys.readouterr().out.strip() == "10.795068, 78.679296"
    assert av._main(["decode", "bad"]) == 1
