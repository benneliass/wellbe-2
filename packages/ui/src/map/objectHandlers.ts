import type { PointerEvent, SVGProps } from 'react';

export type MapObjectActions = {
  activate: () => void; context?: () => void; focus?: () => void; blur?: () => void;
  holdStart?: () => void; holdEnd?: () => void;
  navigate?: (key: string) => void; nudge?: (key: string, big: boolean) => void;
  dragStart?: (event: PointerEvent) => void; dragMove?: (event: PointerEvent) => void; dragEnd?: (event: PointerEvent) => void;
};

/** Accessible input binding shared by any adapter using the map object model.
 * Callbacks decide what activation, navigation and context mean in their domain.
 */
export type MapObjectHandlers = Pick<SVGProps<SVGGElement>,
  'onClick' | 'onKeyDown' | 'onContextMenu' | 'onMouseEnter' | 'onMouseLeave' |
  'onFocus' | 'onBlur' | 'onPointerDown' | 'onPointerMove' | 'onPointerUp' | 'onPointerCancel' | 'onPointerLeave'>;

export function mapObjectHandlers(actions: MapObjectActions): MapObjectHandlers {
  return {
    onClick: (event) => { event.stopPropagation(); actions.activate(); },
    onKeyDown: (event) => {
      if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); actions.activate(); }
      else if ((event.key === 'ContextMenu' || event.shiftKey && event.key === 'F10') && actions.context) { event.preventDefault(); actions.context(); }
      else if (event.key.startsWith('Arrow')) {
        const handler = event.altKey ? actions.navigate : actions.nudge;
        if (handler) { event.preventDefault(); if (event.altKey) actions.navigate?.(event.key); else actions.nudge?.(event.key, event.shiftKey); }
      }
    },
    onContextMenu: actions.context ? (event) => { event.preventDefault(); actions.context?.(); } : undefined,
    onMouseEnter: actions.focus, onMouseLeave: actions.blur, onFocus: actions.focus, onBlur: actions.blur,
    onPointerDown: (event) => { actions.holdStart?.(); actions.dragStart?.(event); },
    onPointerMove: actions.dragMove,
    onPointerUp: (event) => { actions.holdEnd?.(); actions.dragEnd?.(event); },
    onPointerCancel: (event) => { actions.holdEnd?.(); actions.dragEnd?.(event); },
    onPointerLeave: actions.holdEnd,
  };
}
