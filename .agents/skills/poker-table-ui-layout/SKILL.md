---
name: poker-table-ui-layout
description: Design and implement the actual Token Hold'em poker table UI/UX layout. Use when Codex is asked for seat positioning, an 8-player poker table layout, dealer button movement, community cards, player stack display, pot display, action indicators, responsive poker UI, readable table zones, card placement rules, or implementation checklists for the Token Hold'em table.
---

# Poker Table UI Layout

## Core Requirements

Use this skill to produce a practical table layout plan before implementing poker UI changes. Preserve these invariants:

- Use exactly 8 seats.
- Put the human player at seat 0, bottom-center.
- Put the 7 LLM players at seats 1-7.
- Put community cards in the center of the table.
- Render the dealer button as a visible chip that rotates around all 8 seats.
- Keep labels, stacks, current action, cards, pot, and controls readable before making the table decorative.

## Seat Coordinate Map

Use normalized table coordinates where `(0, 0)` is the top-left of the table container and `(100, 100)` is the bottom-right. Convert to CSS with percentages or container-relative positioning.

| Seat | Player | Position | Anchor | Notes |
| --- | --- | --- | --- | --- |
| 0 | Human | `(50, 88)` | bottom-center | Largest seat panel; show hole cards and primary action controls nearby. |
| 1 | LLM | `(23, 78)` | bottom-left | Keep above/beside human controls on narrow screens. |
| 2 | LLM | `(8, 54)` | left-mid | Stack vertically; avoid overlapping table edge. |
| 3 | LLM | `(18, 24)` | upper-left | Angle toward center only if text remains horizontal. |
| 4 | LLM | `(50, 12)` | top-center | Good place for compact seat panel. |
| 5 | LLM | `(82, 24)` | upper-right | Mirror seat 3. |
| 6 | LLM | `(92, 54)` | right-mid | Mirror seat 2. |
| 7 | LLM | `(77, 78)` | bottom-right | Mirror seat 1. |

Implementation rule: keep seat content horizontal even when the table art is elliptical. Use transforms only for panel placement, not for readable text.

## Table Zones

- Center zone: community cards, pot, hand phase, and optional board labels. Reserve roughly `left: 28%-72%`, `top: 35%-62%`.
- Seat ring: player panels and action states. Reserve roughly the outer 18%-25% of the table container.
- Human action zone: bottom band below or overlapping the lower table edge. Keep controls reachable and never hidden by seat 0.
- Status zone: hand id, blinds, street, and turn timer. Put this outside the center card row or in a compact top bar.
- Log/chat zone: keep outside the table on desktop; collapse behind a tab, drawer, or lower sheet on mobile.

## Dealer Button Orbit

Treat the dealer button as a small chip positioned near the active dealer seat, between that seat panel and the table center. Use the same seat index order as gameplay state: `0 -> 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 0`.

| Seat | Button Position |
| --- | --- |
| 0 | `(50, 74)` |
| 1 | `(30, 69)` |
| 2 | `(20, 54)` |
| 3 | `(28, 32)` |
| 4 | `(50, 24)` |
| 5 | `(72, 32)` |
| 6 | `(80, 54)` |
| 7 | `(70, 69)` |

Render the button as a circular chip with `D` or a dealer icon, high contrast, and a z-index above felt/card graphics but below modals. Animate movement only when it helps orientation; the final position must be unambiguous.

## Card Placement Rules

- Community cards: render a single centered row of up to 5 cards in the center zone. Keep fixed card dimensions and consistent gaps so flop, turn, and river do not shift unrelated UI.
- Human hole cards: render larger and bottom-centered inside or directly above seat 0. Keep them visually connected to the human panel.
- LLM hole cards: render as backs, compact placeholders, or hidden cards near each LLM seat depending on game state. Do not show private information unless the game state explicitly allows it.
- Burn/deck/muck indicators: optional, small, and secondary. Place near the community-card row without competing with the pot.
- Responsive cards: shrink cards by container width using bounded sizes; do not let card labels become illegible. Prefer fewer decorative card details on small screens.

## Player Panel Rules

Every seat panel should have stable slots for:

- Player name or model label.
- Stack amount.
- Current bet or committed chips.
- Status: folded, all-in, sitting out, thinking, winner, eliminated.
- Action indicator: current turn highlight, countdown/progress, or last action text.
- Cards or card placeholders.

Prioritize density and scanning. Use compact chips, icons, and short labels. Avoid large avatar art unless it does not reduce chip/card readability.

## Responsive Rules

- Desktop: use an elliptical table with absolute-positioned seats from the coordinate map.
- Tablet: keep the ellipse, reduce seat panel width, and move logs/sidebars below the table.
- Mobile portrait: switch to a stacked or compressed ring only if the 8-seat ellipse becomes unreadable. Keep the human seat and action controls fixed at the bottom, center/community cards above, and LLM seats in a scrollable or two-row opponent strip.
- Keep minimum touch targets near 44px for action controls.
- Verify the longest player/model names and large stack values do not overflow panels.

## UI Component Layout Plan

When asked to design or implement the table, produce or follow this plan:

1. Define a `SEAT_COORDS` map for 8 seats and a `DEALER_BUTTON_COORDS` map for the 8 dealer positions.
2. Build a table container with a stable aspect ratio, preferably around `16 / 10` on desktop.
3. Render felt/table art as background only; keep functional elements in semantic components above it.
4. Render the center zone with pot, community cards, and street/status.
5. Render all 8 seat panels from game state by seat index.
6. Render the dealer button from the dealer seat index using the orbit map.
7. Render the human action controls in a dedicated bottom action zone.
8. Add responsive breakpoints and text-overflow handling.
9. Test desktop, tablet, and mobile viewports for overlap, clipping, and legibility.

## Implementation Checklist

- Confirm exactly 8 seats are rendered.
- Confirm seat 0 is the human player at bottom-center.
- Confirm seats 1-7 are LLM players around the table.
- Confirm the dealer button is visible at every dealer index and follows gameplay order.
- Confirm community cards remain centered for 0-5 board cards.
- Confirm pot and current bet displays are readable.
- Confirm the active player is obvious without relying only on color.
- Confirm folded/all-in/winner states are visually distinct.
- Confirm action controls remain usable on mobile.
- Confirm no seat panel, card row, dealer chip, pot, or controls overlap at target breakpoints.
