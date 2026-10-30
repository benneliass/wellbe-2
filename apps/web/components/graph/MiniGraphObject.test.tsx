import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { MapMiniature } from "@wellbe/ui/map";
import { presentGraphMiniature } from "./graphMiniaturePresentation";
import { RECORD_KINDS } from './marks';
import type { SourceType } from './graphData';

describe('source miniatures', () => {
  it.each([
    ['lab', 'flask-conical', RECORD_KINDS.result.color],
    ['doc', 'file-text', RECORD_KINDS.document.color],
    ['note', 'file-text', RECORD_KINDS.note.color],
    ['wearable', 'activity', RECORD_KINDS.result.color],
    ['reported', 'message-circle', RECORD_KINDS.note.color],
    ['research', 'globe', RECORD_KINDS.other.color],
  ] as const)('uses the %s source glyph and shared kind palette', (source: SourceType, icon, color) => {
    const { container } = render(<svg><MapMiniature item={presentGraphMiniature({ kind: 'source', id: 'source', label: 'Source', source })} radius={8} /></svg>);
    const miniature = container.querySelector('[data-mini-object]')!;
    expect(miniature.getAttribute('data-mini-icon')).toBe(icon);
    expect(miniature.getAttribute('data-mini-color')).toBe(color);
    expect(container.querySelector('[data-mini-silhouette]')).not.toBeNull();
  });
});
