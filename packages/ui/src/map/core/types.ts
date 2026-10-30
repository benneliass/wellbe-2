export type Point = { x: number; y: number };
export type MapExtent = { width: number; height: number };
export type MapCamera = { k: number; tx: number; ty: number };
export type MapPositions = Record<string, Point>;
export type MapRoutePoint = Point & {
  r: number; labelWidth?: number; labelTop?: number; labelBottom?: number;
  labelOnly?: boolean; allowUnderLabel?: boolean;
};
export type MapBounds = Point & { id: string; hw: number; up: number; down: number };
