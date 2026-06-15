---
name: gradio-game-scene-composer
description: Turn Gradio apps into full-page, immersive, game-like scenes using custom HTML, CSS, and layered layout architecture. Use when Codex is asked for full-page game UI, immersive Gradio layout, replacing generic Gradio panels, background scene composition, HUD/sidebar/action bar layout, CSS layering, z-index strategy, responsive game scene design, or Token Hold'em tavern poker scene composition.
---

# Gradio Game Scene Composer

## Purpose

Use this skill to make a Gradio app feel like an integrated game screen rather than a demo. For Token Hold'em, the tavern environment should be the full-page background, with the poker table, avatars, HUD panels, speech bubbles, sidebars, and action buttons layered above it.

Preserve gameplay behavior. Do not change poker engine logic, state transitions, or callback semantics unless the user explicitly asks. Prefer edits to render helpers, CSS, HTML templates, layout wrappers, and component placement.

## First Pass

1. Inspect `app.py` and rendering/layout helpers before editing. In Token Hold'em, start with `token_holdem/render.py` for HTML/CSS table rendering and only touch `token_holdem/engine.py` if a rendering bug proves engine-adjacent.
2. Identify which Gradio components are functional controls or outputs, then decide whether each belongs in the game scene, a HUD layer, a side drawer, an action bar, or a hidden plumbing role.
3. Keep Gradio event wiring intact. Move or restyle components through `elem_id`, `elem_classes`, layout containers, `gr.HTML`, and CSS rather than rewriting callbacks.
4. Produce or follow the scene plan before large edits: scene layout architecture, DOM layer plan, CSS strategy, breakpoints, component integration, and checklist.

## Scene Architecture

Use a root scene shell that owns the viewport and isolates game visuals from generic Gradio framing:

```html
<div class="game-scene">
  <div class="scene-bg"></div>
  <main class="scene-stage">
    <section class="table-layer">...</section>
    <section class="avatar-layer">...</section>
    <section class="speech-layer">...</section>
  </main>
  <aside class="hud hud-left">...</aside>
  <aside class="hud hud-right">...</aside>
  <footer class="action-bar">...</footer>
</div>
```

Map the app's actual DOM to this model. If Gradio must render controls outside the custom HTML block, style its rows/columns as scene overlays with stable IDs/classes.

Recommended layer order:

1. `scene-bg`: tavern environment, full viewport, non-interactive.
2. `scene-lighting`: optional vignette/candlelight/material overlays, non-interactive.
3. `scene-stage`: poker table and player positions.
4. `table-felt` and card/chip objects.
5. `avatar-layer`: player portraits and status badges.
6. `speech-layer`: bubbles, model thoughts, current action callouts.
7. `hud` panels: hand status, logs, settings, history, model info.
8. `action-bar`: player controls, bet slider/input, primary actions.
9. `modal/toast` layer: blocking dialogs and transient alerts.

Use explicit z-index tokens instead of scattered numbers:

```css
:root {
  --z-bg: 0;
  --z-stage: 10;
  --z-table: 20;
  --z-avatars: 30;
  --z-speech: 40;
  --z-hud: 50;
  --z-actions: 60;
  --z-modal: 100;
}
```

## CSS Strategy

- Make the app root fill the viewport: set `min-height: 100dvh` on the Gradio container and the scene shell.
- Hide or neutralize generic demo framing only inside the app scope. Avoid global CSS that breaks Gradio internals, dropdowns, modals, or accessibility.
- Use CSS Grid for page-level composition: background, stage, left/right HUD, bottom action bar.
- Use absolute positioning only inside stable scene containers such as the poker table or avatar layer.
- Use Flexbox for compact HUD panel content, button groups, chip rows, and speech bubble internals.
- Use stable dimensions with `clamp()`, `aspect-ratio`, `minmax()`, and fixed card/control slots so changing labels do not shift the scene.
- Keep decorative backgrounds behind readable UI. Add scrims, shadows, or panel surfaces where text crosses detailed art.
- Prefer class and ID hooks on Gradio components. Avoid brittle selectors based on generated DOM depth unless no better hook exists.

Example page grid:

```css
.game-scene {
  min-height: 100dvh;
  display: grid;
  grid-template-columns: minmax(220px, 18vw) 1fr minmax(260px, 22vw);
  grid-template-rows: minmax(0, 1fr) auto;
  grid-template-areas:
    "left stage right"
    "actions actions actions";
  position: relative;
  overflow: hidden;
}
```

## Responsive Breakpoints

Plan at least three states:

- Desktop wide: tavern fills the page, table centered, side HUDs visible, action bar fixed along the bottom.
- Tablet or narrow desktop: collapse one sidebar below or into a drawer; keep the table and action bar dominant.
- Mobile portrait: prioritize human hand, pot/current turn, action controls, and active opponent. Move logs/history into tabs, accordions, or a drawer.

Use responsive rules that preserve game legibility:

- Keep primary action controls at comfortable touch size, around 44px minimum.
- Reduce decorative tavern details before shrinking cards, chip counts, or player state below readability.
- Check long model names, large stack values, verbose action text, and disabled button labels.
- Avoid `100vh` alone on mobile; prefer `100dvh` with fallbacks if needed.

## Gradio Integration

- Use `gr.Blocks(css=...)` or a linked CSS file for the scene system; keep large CSS in helpers or constants if the repo already does.
- Assign `elem_id` or `elem_classes` to Gradio components that need scene placement.
- Use `gr.HTML` for complex layered visuals that are output-only, such as the tavern/table scene.
- Keep interactive controls as real Gradio components when they drive callbacks. Restyle and reposition them instead of replacing them with inert HTML.
- If custom HTML buttons are unavoidable, bridge them carefully without breaking existing event wiring; otherwise avoid this path.
- Keep hidden state components and callback dependencies present even if visually hidden. Use accessible hiding patterns where appropriate.
- Verify Gradio overlays, dropdown menus, and disabled states still render above the scene and remain clickable.

## Token Hold'em Constraints

- Do not change deterministic poker rules in `token_holdem/engine.py` for visual scene work.
- Keep exactly 8 seats unless the user explicitly requests a gameplay change.
- Keep seat 0 as the human bottom-center and seats 1-7 as LLM opponents around the table.
- Keep community cards in the fixed center table zone.
- Keep action buttons outside the table art as Gradio controls, visually integrated into the action bar.
- Preserve callback inputs/outputs in `app.py`; if moving components, keep their variables and event bindings intact.

## Implementation Checklist

When using this skill, produce or execute this checklist:

1. Define the full-screen scene shell and decide which existing Gradio blocks map to each scene layer.
2. Add stable DOM hooks: IDs/classes for scene root, stage, table, sidebars, HUD panels, logs, speech bubbles, and actions.
3. Establish z-index tokens and ensure non-interactive visual layers use `pointer-events: none`.
4. Build the CSS grid/flex structure for desktop, tablet, and mobile breakpoints.
5. Integrate the poker table and avatars into the scene stage without changing game state logic.
6. Place Gradio controls into the HUD/action layer while preserving event wiring.
7. Add readable surfaces, scrims, and contrast rules over the tavern background.
8. Check overflow, clipping, focus states, disabled states, and dropdown/modal stacking.
9. Run the app and inspect desktop plus mobile viewport screenshots when feasible.
10. Run the relevant tests, usually `uv run pytest` for Token Hold'em.

## Expected Output

For planning requests, return:

- `Scene layout architecture`: root shell, regions, and responsibilities.
- `DOM layer plan`: ordered layer list with z-index and interaction behavior.
- `CSS grid/flex strategy`: desktop structure and responsive adjustments.
- `Responsive breakpoints`: concrete viewport behaviors and priorities.
- `Gradio component integration plan`: which components become scene HTML, HUD, sidebars, action bar, or hidden state.
- `Implementation checklist`: ordered, testable steps.

For implementation requests, make scoped code changes, then summarize changed files and verification performed.
