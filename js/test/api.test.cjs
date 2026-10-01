const test = require("node:test");
const assert = require("node:assert/strict");

test("CommonJS entry has the registry pre-loaded", () => {
  const av = require("..");
  assert.equal(av.version, "2.1.1");
  assert.equal(av.encode(10.7950461, 78.679302), "TRZ-D04200355");
  assert.equal(av.describe("TRZ-D04200355"), "5.5 km NW of TRZ (Tiruchirappalli International Airport)");
  assert.equal(av.move("TRZ-D04200355", 50, 0), "TRZ-D03700355");
  assert.equal(av.shorten("TRZ-D0420303554", "100m"), "TRZ-D042035");
  assert.equal(av.normalize("trz-d0420.0355"), "TRZ-D04200355");
  assert.equal(av.cellPolygon("TRZ-D04200355").length, 4);
  assert.equal(av.nearestAnchor(13.0, 80.2).code, "MAA");
  assert.ok(Math.abs(av.distanceFromAnchorM("TRZ-D04200355") - 5506.4) < 0.1);
});

test("ESM entry: default and named exports", async () => {
  const mod = await import("../index.mjs");
  assert.equal(mod.default.encode(51.5074, -0.1278), "LCY-D12710024");
  assert.equal(mod.encode(51.5074, -0.1278), "LCY-D12710024");
  assert.equal(typeof mod.OAVGError, "function");
});

test("core entry ships without data and needs loadRegistry()", () => {
  // run in a fresh process: the main entry and /core share one module instance
  const { spawnSync } = require("node:child_process");
  const code = `
    const core = require("airportvector/core");
    let threw = false; try { core.encode(0, 0); } catch (e) { threw = e instanceof core.OAVGError; }
    if (!threw) throw new Error("expected OAVGError before loadRegistry");
    core.loadRegistry([["TRZ", 10.762915, 78.717741, "Tiruchirappalli International Airport"]]);
    if (core.encode(10.7950461, 78.679302) !== "TRZ-D04200355") throw new Error("bad encode");
    import("airportvector/core").then(m => { if (typeof m.encode !== "function") process.exit(3); });`;
  const r = spawnSync(process.execPath, ["-e", code], { cwd: __dirname, encoding: "utf8" });
  assert.equal(r.status, 0, r.stderr);
});

test("package exports resolve", () => {
  assert.ok(require.resolve("airportvector/anchors.json"));
  assert.ok(require.resolve("airportvector/core"));
});
