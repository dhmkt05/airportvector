// Type definitions for airportvector (OAVG v4). Airport registry pre-loaded.

export type Precision = "1km" | "333m" | "111m" | "37m" | "12m" | "4m";

export interface Anchor { code: string; name: string; lat: number; lon: number; status?: "active" | "retired"; }
export type AnchorRow = [code: string, lat: number, lon: number, name: string] | Anchor;

export interface ParsedCode {
  anchor: string;          // IATA code, e.g. "TRZ"
  coarse: string;          // first group: 5-9 keypad digits, ends at the 1 km square
  fine: string;            // second group: 0-5 keypad digits inside the 1 km square
  extra: number;           // implied outer levels (0 inside the 243 km zone)
  levels: number;          // coarse.length + fine.length
  zoneM: number;           // zone size in metres (243,000 x 3^extra)
  cellSize: number;        // metres (1000 / 3^fine.length)
  fineDigits: number;      // fine.length
  leadingFives: number;    // 5 = within 40 km, 55 = 13.5 km, 555 = 4.5 km ...
  precision: Precision;
  code: string;            // canonical form for links, e.g. "TRZ-55511-79566"
  display: string;         // form for people, e.g. "TRZ 55511 79566"
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
  /** The 8 cells around a code, same size, clockwise from North. */
  neighbors(code: string): string[];
  shorten(code: string, precision: Precision): string;
  normalize(code: string): string;
  /** Form for people, e.g. "TRZ 55511 79566". */
  display(code: string): string;
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
  distanceFromAnchorM: OAVG["distanceFromAnchorM"], move: OAVG["move"], neighbors: OAVG["neighbors"],
  shorten: OAVG["shorten"], normalize: OAVG["normalize"], display: OAVG["display"], cellPolygon: OAVG["cellPolygon"], nearestAnchor: OAVG["nearestAnchor"],
  toGrid: OAVG["toGrid"], fromGrid: OAVG["fromGrid"];
