"use client";

import { useMemo, useRef } from "react";
import { planConnectionScene, type SceneConnection } from "./core";

/** Plan the complete settled scene, then let the material carry it throughout a drag. */
export function useMapRoutes(scene: SceneConnection[], viewport: { width: number; height: number }, dragging: boolean) {
  const snapshot = useRef(scene);
  if (!dragging) snapshot.current = scene;
  const revision = JSON.stringify(snapshot.current);
  return useMemo(() => {
    const saved = snapshot.current;
    const paths = planConnectionScene(saved, viewport);
    return saved.map((edge) => ({ ...edge, route: paths.get(edge.id) }));
    // The serialized geometry deliberately excludes hover, colors and animation frames.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [revision, viewport.width, viewport.height]);
}
