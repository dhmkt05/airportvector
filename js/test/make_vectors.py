"""Regenerate vectors.json from the Python package:  python js/test/make_vectors.py"""
import json
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "python", "src"))
import airportvector as av  # noqa: E402

rnd = random.Random(20261001)
pts = [(rnd.uniform(-90, 90), rnd.uniform(-180, 180)) for _ in range(250)]
pts += [(rnd.uniform(10.5, 11.0), rnd.uniform(78.4, 79.0)) for _ in range(100)]   # around Trichy
pts += [(10.7950461, 78.679302), (51.5074, -0.1278), (-90.0, 0.0), (90.0, 0.0), (0.0, 180.0)]
rows = []
for lat, lon in pts:
    r = {"lat": lat, "lon": lon}
    for p in av.PRECISIONS:
        r[p] = av.encode(lat, lon, p)
    full = r[av.DEFAULT_PRECISION]
    r["describe"] = av.describe(full)
    r["dlat"], r["dlon"] = av.decode(full, 9)
    rows.append(r)
invalid = ["TRZ-5551", "TRZ-55511-795661", "TRZ-55510-79566", "XXX-55511-79566", "TRZ-D04200355",
           "TRZ-55511-7956O", "", "TRZ-1234567891-11111", "bad"]
json.dump({"version": av.__version__, "encode": rows, "invalid": invalid}, open(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "vectors.json"), "w"), separators=(",", ":"))
print(f"wrote {len(rows)} points")
