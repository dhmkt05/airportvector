const test = require("node:test");
const assert = require("node:assert/strict");

test("CommonJS entry has the registry pre-loaded", () => {
  const av = require("..");
  assert.equal(av.version, "4.0.0");
  assert.equal(av.encode(10.7950461, 78.679302), "TRZ-55511-79566");
  assert.equal(av.display("trz-55511-79566"), "TRZ 55511 79566");
  assert.equal(av.describe("TRZ-55511-79566"), "5.5 km NW of TRZ (Tiruchirappalli International Airport)");
  assert.equal(av.move("TRZ-55511-79566", 1, 0), "TRZ-55511-79644");
  assert.equal(av.neighbors("TRZ-55511-79566").length, 8);
  assert.equal(av.shorten("TRZ-55511-79566", "1km"), "TRZ-55511");
  assert.equal(av.normalize("trz 55511 79566"), "TRZ-55511-79566");
  assert.equal(av.normalize("TRZ5551179566"), "TRZ-55511-79566");
  assert.equal(av.parse("TRZ 55511 79566").leadingFives, 3);
  assert.equal(av.cellPolygon("TRZ-55511-79566").length, 4);
  assert.equal(av.nearestAnchor(13.0, 80.2).code, "MAA");
  assert.ok(Math.abs(av.distanceFromAnchorM("TRZ-55511-79566") - 5507.3) < 0.1);
});

test("far places get a longer first group", () => {
  const av = require("..");
  assert.equal(av.encode(-48.8767, -123.3933), "IPC-84772643-65933");
  assert.equal(av.normalize("TRZ-555511-79566"), "TRZ-55511-79566");
});

test("ESM entry: default and named exports", async () => {
  const mod = await import("../index.mjs");
  assert.equal(mod.default.encode(51.5074, -0.1278), "LCY-55444-38173");
  assert.equal(mod.encode(51.5074, -0.1278), "LCY-55444-38173");
  assert.equal(typeof mod.neighbors, "function");
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
    if (core.encode(10.7950461, 78.679302) !== "TRZ-55511-79566") throw new Error("bad encode");
    import("airportvector/core").then(m => { if (typeof m.encode !== "function") process.exit(3); });`;
  const r = spawnSync(process.execPath, ["-e", code], { cwd: __dirname, encoding: "utf8" });
  assert.equal(r.status, 0, r.stderr);
});

test("package exports resolve", () => {
  assert.ok(require.resolve("airportvector/anchors.json"));
  assert.ok(require.resolve("airportvector/core"));
});
