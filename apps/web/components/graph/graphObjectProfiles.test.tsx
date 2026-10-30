import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MapAccents, MapOrbit } from "@wellbe/ui/map";
import { graphAccentProfile } from "./graphObjectProfiles";
import { presentGraphMiniature } from "./graphMiniaturePresentation";
import type { GraphNode } from "./graphData";
import { SEED_NODES, type NodeType } from "./graphData";

function GraphNodeAccents({ node, radius, hue, bridgeColors, orbitItems = [] }: { node: GraphNode; radius: number; hue: string; bridgeColors?: string[]; orbitItems?: typeof children }) {
  return <MapAccents radius={radius} color={hue} profile={graphAccentProfile(node, Boolean(bridgeColors))} segments={bridgeColors}><MapOrbit radius={radius} items={orbitItems.map(presentGraphMiniature)} /></MapAccents>;
}
const types: NodeType[] = ["symptom", "context", "pending", "lab", "vital", "visit", "capture", "theory", "investigation", "external"];
const sample = (patch: Partial<GraphNode>): GraphNode => ({ ...SEED_NODES[0]!, ...patch });

const children = [
  {kind: "concept" as const, id: "child-note", label: "Note", type: "capture" as const, color: "#8b5cf6"},
  {kind: "concept" as const, id: "child-lab", label: "Result", type: "lab" as const, color: "#0ea5a4"},
  {kind: "concept" as const, id: "child-context", label: "Context", type: "context" as const, color: "#64748b"},
];

describe("graph object accents", () => {
  it.each(types)("covers %s objects without adding controls or changing their icon", (type) => {
    const { container } = render(<svg><GraphNodeAccents node={sample({ type })} radius={20} hue="#0ea5a4" orbitItems={[]} /></svg>);
    const accents = container.querySelector('[data-node-accents]')!;
    expect(accents.getAttribute('aria-hidden')).toBe('true');
    expect(accents.getAttribute('pointer-events')).toBe('none');
    if (graphAccentProfile(sample({ type })).kind === 'none') {
      expect(accents.querySelector('circle, rect, ellipse, [data-accent-rotate]')).toBeNull();
    } else expect(accents.querySelector('circle, rect, ellipse')).not.toBeNull();
    expect(accents.querySelector('text, foreignObject, [tabindex], [role="button"]')).toBeNull();
    expect(accents.querySelector('[data-node-orbit]')).toBeNull();
  });

  it("preserves metadata differences and the exact satellite count", () => {
    const { container } = render(<svg>
      <GraphNodeAccents node={sample({ ghost: true })} radius={20} hue="#0ea5a4" orbitItems={[]} />
      <GraphNodeAccents node={sample({ aggregate: true })} radius={20} hue="#64748b" orbitItems={[]} />
      <GraphNodeAccents node={sample({ bridge: ['a', 'b'] })} radius={20} hue="#0ea5a4" bridgeColors={['#0ea5a4', '#8b5cf6']} orbitItems={children} />
    </svg>);
    expect(container.querySelector('[data-node-accents="open-loop"]')).not.toBeNull();
    expect(container.querySelector('[data-node-accents="comparison"]')).not.toBeNull();
    const bridge = container.querySelector('[data-node-accents="bridge"]')!;
    expect(bridge.querySelectorAll('[data-bridge-accent]').length).toBe(2);
    expect(bridge.querySelectorAll('[data-orbit-dot]').length).toBe(3);
    expect(Array.from(bridge.querySelectorAll('[data-mini-object]')).map((item) => [item.getAttribute('data-mini-object'), item.getAttribute('data-mini-type')])).toEqual(children.map((item) => [item.id, item.type]));
  });

  it("removes the cue after the children are opened", () => {
    const { container, rerender } = render(<svg><GraphNodeAccents node={sample({})} radius={20} hue="#0ea5a4" orbitItems={children} /></svg>);
    expect(container.querySelectorAll('[data-orbit-dot]')).toHaveLength(3);
    rerender(<svg><GraphNodeAccents node={sample({})} radius={20} hue="#0ea5a4" orbitItems={[]} /></svg>);
    expect(container.querySelector('[data-node-orbit]')).toBeNull();
  });
});
