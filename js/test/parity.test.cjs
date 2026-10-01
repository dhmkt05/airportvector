// Parity with the Python reference implementation (vectors from make_vectors.py, airportvector 4.0.0).
const test = require("node:test");
const assert = require("node:assert/strict");
const av = require("..");
const V = require("./vectors.json");
const PRECS = ["1km", "333m", "111m", "37m", "12m", "4m"];

test("vectors come from the same version", () => {
  assert.equal(V.version, av.version);
});
test("encode matches Python at every precision", () => {
  for (const r of V.encode) for (const p of PRECS)
    assert.equal(av.encode(r.lat, r.lon, p), r[p], `${r.lat},${r.lon} @${p}`);
});
test("decode matches Python to 1e-8 degrees", () => {
  for (const r of V.encode) {
    const d = av.decode(r["4m"]);
    assert.ok(Math.abs(d.lat - r.dlat) < 1e-8 && Math.abs(((d.lon - r.dlon + 540) % 360) - 180) < 1e-8, r["4m"]);
  }
});
test("describe matches Python exactly", () => {
  for (const r of V.encode) assert.equal(av.describe(r["4m"]), r.describe);
});
test("invalid codes throw OAVGError", () => {
  for (const c of V.invalid) assert.throws(() => av.parse(c), av.OAVGError, JSON.stringify(c));
});
