import { Icon } from '@wellbe/ui';
import type { MapMiniatureItem } from '@wellbe/ui/map';
import { miniatureAppearance, type MiniGraphItem } from './graphMiniatures';

/** A domain adapter: source/concept identity becomes a plain visual descriptor.
 * The same descriptor is used in any orbit, at any configured miniature size.
 */
export function presentGraphMiniature(item: MiniGraphItem): MapMiniatureItem {
  const visual = miniatureAppearance(item);
  return {
    id: item.id, label: item.label, color: visual.color, shape: visual.shape, kind: item.kind,
    glyph: <Icon name={visual.icon} size={24} strokeWidth={2} />,
    attributes: { 'data-mini-source': item.kind === 'source' ? item.source : undefined, 'data-mini-type': visual.type, 'data-mini-icon': visual.icon },
  };
}
