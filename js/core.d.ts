// Type definitions for airportvector (OAVG v2.1).

export type Precision = "1km" | "100m" | "10m" | "1m";

export interface Anchor { code: string; name: string; lat: number; lon: number; status?: "active" | "retired"; }
export type AnchorRow = [code: string, lat: number, lon: number, name: string] | Anchor;

export interface ParsedCode {
  anchor: string;          // IATA code, e.g. "TRZ"
  sector: "A" | "B" | "C" | "D";   // NE, SE, SW, NW
  band: 0 | 1 | 2;         // near (<100 km), regional (<1,000 km), far (<10,000 km)
  letter: string;          // A–L
  x: number;               // cells East (A/B) or West (C/D)
  y: number;               // cells North (A/D) or South (B/C)
  base: number;            // base digits per axis (2–5)
  digits: number;          // digits per axis (base + band)
  cellSize: number;        // metres
  precision: Precision;
  code: string;            // canonical form
  display: string;         // with a dot between X and Y
}

export declare class OAVGError extends Error {}

export interface OAVG {
  version: string;
  SPEC_VERSION: string;
  PRECISIONS: Readonly<Record<Precision, number>>;
  DEFAULT_PRECISION: Precision;
  OAVGError: typeof OAVGError;
  /** Load the airport registry (already done for you by the main entry point). */
  loadRegistry(rows: AnchorRow[]): void;
  getAnchor(code: string): Anchor;
  /** lat/lon (WGS84 degrees) → code, from the nearest airport unless `anchor` is given. */
  encode(lat: number, lon: number, precision?: Precision, anchor?: string | null): string;
  encodeGrid(anchor: string, x: number, y: number, precision?: Precision): string;
  /** code → centre of its cell. */
  decode(code: string): { lat: number; lon: number };
  decodeGrid(code: string): { anchor: string; x: number; y: number };
  parse(code: string): ParsedCode;
  /** e.g. "5.5 km NW of TRZ (Tiruchirappalli International Airport)" */
  describe(code: string): string;
  /** Ground distance in metres between two codes. */
  distance(code1: string, code2: string): number;
  distanceM(lat1: number, lon1: number, lat2: number, lon2: number): number;
  /** Exact ground distance in metres from the airport: √(X² + Y²). */
  distanceFromAnchorM(code: string): number;
  move(code: string, eastCells: number, northCells?: number): string;
  shorten(code: string, precision: Precision): string;
  normalize(code: string): string;
  cellPolygon(code: string): [number, number][];
  nearestAnchor(lat: number, lon: number): Anchor;
  toGrid(anchor: string, lat: number, lon: number): { x: number; y: number };
  fromGrid(anchor: string, x: number, y: number): { lat: number; lon: number };
}

declare const OAVG: OAVG;
export default OAVG;
export declare const version: OAVG["version"], SPEC_VERSION: OAVG["SPEC_VERSION"], PRECISIONS: OAVG["PRECISIONS"],
  DEFAULT_PRECISION: OAVG["DEFAULT_PRECISION"], loadRegistry: OAVG["loadRegistry"], getAnchor: OAVG["getAnchor"],
  encode: OAVG["encode"], encodeGrid: OAVG["encodeGrid"], decode: OAVG["decode"], decodeGrid: OAVG["decodeGrid"],
  parse: OAVG["parse"], describe: OAVG["describe"], distance: OAVG["distance"], distanceM: OAVG["distanceM"],
  distanceFromAnchorM: OAVG["distanceFromAnchorM"], move: OAVG["move"], shorten: OAVG["shorten"],
  normalize: OAVG["normalize"], cellPolygon: OAVG["cellPolygon"], nearestAnchor: OAVG["nearestAnchor"],
  toGrid: OAVG["toGrid"], fromGrid: OAVG["fromGrid"];
