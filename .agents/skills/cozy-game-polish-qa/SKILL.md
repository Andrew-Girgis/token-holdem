---
name: cozy-game-polish-qa
description: Review and improve Token Hold'em final UI polish, UX quality, game feel, animations, hover/focus states, readability, accessibility, responsive behavior, and premium cozy tavern presentation. Use when Codex is asked for UI polish, UX review, game feel, animations, hover states, readability, accessibility, final quality pass, polish punch list, prioritized improvements, mobile checks, or a premium feel review for the Token Hold'em app.
---

# Cozy Game Polish QA

## Purpose

Use this skill to make Token Hold'em feel like a polished cozy tavern poker game rather than a functional demo. Focus on clarity, charm, responsiveness, readable game state, accessible interactions, and satisfying feedback.

## Workflow

1. Inspect the running app or relevant UI code before making recommendations. If feasible, run the app and capture desktop and mobile views.
2. Review the experience as a player, not only as an implementer: evaluate whether the current turn, pot, stacks, bet size, player status, available actions, and result state are immediately legible.
3. Produce a prioritized polish punch list before editing when the request is review-only. If the user asks to improve the app, implement the highest-impact items directly.
4. Keep changes coherent with a cozy tavern poker fantasy: warm, tactile, readable, playful, and calm under repeated play.
5. Verify the result after changes with screenshots or interaction checks when a browser is available.

## Review Checklist

### Readability and Game State

- Ensure the active player, dealer/button, blinds, folded/all-in/sitting-out states, pot, current bet, call amount, and winner/result messages are visible without hunting.
- Prefer concise table labels over verbose explanatory text.
- Make numeric values scannable with consistent formatting, spacing, and alignment.
- Check that cards, chips, player names, and action controls remain readable against textured or illustrated backgrounds.
- Avoid hiding essential state inside hover-only UI.

### Interaction Feel

- Add clear hover, active, disabled, selected, focus-visible, and loading states for buttons, cards, seats, and controls.
- Make primary actions feel deliberate: call/check/bet/raise/fold should have distinct weight and clear affordance.
- Use transitions for state changes that benefit comprehension, such as chips moving to the pot, active seat changes, revealed cards, winner highlight, and hand reset.
- Keep animation durations short enough for repeated play, usually 120-300ms for UI feedback and 300-700ms for celebratory or spatial motion.
- Respect `prefers-reduced-motion`; provide non-motion emphasis such as color, outline, glow, or opacity changes.

### Cozy Tavern Premium Feel

- Look for tactile material cues: felt, wood, brass, parchment, candlelight, soft shadows, bevels, chip depth, and warm highlights.
- Use charm in small doses: subtle ambient details, satisfying chip/card motion, clear win celebration, and personable status copy.
- Avoid clutter, novelty fonts for critical text, overdone glow, muddy contrast, and single-hue palettes.
- Make the first screen feel like the game is already alive: table centered, players seated, core controls visible, and no empty demo scaffolding.

### Accessibility

- Verify text contrast for critical controls and state labels.
- Ensure all interactive elements are keyboard reachable with visible focus.
- Use semantic buttons for actions and avoid click-only divs.
- Ensure disabled controls communicate why an action is unavailable through nearby state or labels.
- Confirm target sizes are comfortable on touch screens, roughly 44px minimum for primary controls.

### Mobile and Responsive

- Check narrow screens for overlapping cards, clipped buttons, cramped labels, and unreadable chip counts.
- Prioritize the current player hand, available actions, pot/current bet, and active opponent status on mobile.
- Let decorative tavern elements yield space before game-critical information does.
- Use stable dimensions for cards, chips, seats, toolbars, and controls so hover states and changing labels do not shift the layout.

## Output Format

When reviewing, return:

- `Polish punch list`: grouped by visual polish, game-state clarity, interaction feel, accessibility, and responsive behavior.
- `Prioritized improvements`: order by player impact and implementation risk, with `P0`, `P1`, or `P2`.
- `Animation recommendations`: include what should move, why it helps, suggested duration/easing, and reduced-motion fallback.
- `Mobile/responsive checks`: list specific viewports or layout states to test.
- `Premium feel review`: summarize whether the current build feels like a cozy tavern poker game and name the biggest missing ingredient.

When editing code, include a concise final summary of changed files and verification performed.
