---
name: art-asset-generator
description: Generate final visual image assets for Token Hold'em and save them as real repo files under assets/. Use when Codex is asked to generate actual image files, create tavern background art, create LLM avatar portraits, create poker table assets, create transparent PNG/WebP sprites, use image generation to create assets, save generated assets into the repo, update the asset manifest, integrate generated art through CSS/HTML/token_holdem/render.py, or replace CSS placeholders with real art assets. This skill must produce actual generated files when image generation is available, not just prompts.
---

# Art Asset Generator

## Overview

Generate, save, optimize, manifest, integrate, and QA production image assets for Token Hold'em. Prefer real repo artifacts over prompt-only output; use prompt-only fallbacks only when Codex image generation is unavailable in the current environment.

## Coordination

Load companion skills when their responsibility applies:

- Use `pixel-tavern-art-director` for visual direction, palette, lighting, composition, negative prompts, and QA criteria.
- Use `image-asset-pipeline` for manifest shape, naming, asset slots, dimensions, optimization, and UI integration rules.
- Use `llm-avatar-personification` for LLM avatar concepts that avoid exact company logos, mascots, or wordmarks.
- Use `poker-table-ui-layout` for seat/table/community-card constraints before making table, overlay, chip, or card assets.
- Use `gradio-game-scene-composer` when integrating assets into full-page Gradio scene structure or CSS layering.

Always inspect current repo state before generating:

- `assets/token-holdem/manifest.json`
- `token_holdem/render.py`
- `app.py`
- Any existing `docs/token-holdem-*` prompt, persona, or visual direction files
- Existing generated assets under `assets/`

## Workflow

1. Read visual direction, layout constraints, and the asset manifest.
2. Identify the exact asset slot to generate, including manifest `id`, target use site, and displayed CSS size.
3. Decide dimensions, format, alpha, filename, and destination path before generation.
4. Use Codex's available image generation capability to create the actual image file.
5. Save the generated file under the repo's `assets/` tree, normally `assets/token-holdem/`.
6. Inspect the generated asset visually. Check art direction, transparency, crop safety, readability, and absence of baked UI text or logos.
7. Regenerate or refine poor assets instead of accepting unusable output.
8. Optimize or convert when needed for Hugging Face Spaces. Prefer PNG for alpha-critical art and WebP for full-scene/background assets when quality remains acceptable.
9. Update `assets/token-holdem/manifest.json` with filename, path, dimensions, format, purpose/role, where it is used, source, prompt summary, and QA notes.
10. Wire the asset into the Gradio app through CSS, HTML, or helpers in `token_holdem/render.py` where appropriate.
11. Run checks that prove the app still imports and loads. Prefer `uv run pytest`; for UI-impacting changes, also run `uv run python app.py` and inspect the Gradio URL.

## Asset Decisions

Use these defaults unless the manifest or layout requires something else:

- Tavern backgrounds: `1920x1080` or `2560x1440`, no alpha, full-scene composition, dark quiet center for table/cards/seats.
- Poker table art: `1536x864` or `2048x1152`, transparent PNG when layered over tavern art, no baked cards, chips, labels, or pot text.
- LLM avatars: `512x512` transparent PNG or WebP with alpha when supported, consistent camera angle and tavern rim light, no exact company marks.
- Sprites, chips, candles, props, overlays, seat frames: transparent PNG with tight but safe padding.
- Card backs: high-resolution rectangular PNG/WebP matching the current CSS card proportions, no ranks, suits, brands, watermarks, or readable words.

Use kebab-case filenames with dimensions, for example `tavern-bg-main-1920x1080.webp`, `table-felt-top-1536x864.png`, `avatar-gpt-architect-neutral-512.png`, or `prop-candle-lit-256x512.png`.

## Image Generation Requirements

The expected output is actual generated image files committed to the repo workspace. Do not stop at writing prompts when image generation is available.

When calling image generation, include:

- Token Hold'em as the project context.
- Exact canvas dimensions and aspect ratio.
- Pixel-art cozy tavern poker style, warm candle/hearth lighting, premium game UI readability.
- Required alpha/transparent background when appropriate.
- Composition safe areas and any live UI that must remain readable.
- Negative constraints: no text unless explicitly required, no logos, no exact company mascots, no watermarks, no baked cards/chips/pot/player labels unless the asset is specifically that object.

If image generation is unavailable, explicitly state that limitation and provide fallback output only:

- Final generation prompts.
- Planned filenames and destination paths.
- Manifest entries marked as pending generation.
- Integration notes marked blocked until assets exist.

## Manifest Update

Preserve the existing manifest schema. For generated assets, ensure each relevant entry has:

- `file`: repo-root-relative or app-servable path used by the code.
- `dimensions`: actual pixel dimensions.
- `format`: actual file format.
- `alpha`: whether the final file has transparency.
- `source`: mark as generated, including the generation tool/model if known.
- `purpose` or `role`: what the file is for.
- `usedBy` or equivalent notes: CSS selector, HTML/render helper, or file where it is wired.
- `prompt` or concise prompt summary.
- `qa`: brief checks performed and any known limitations.

If the existing manifest entry is a placeholder, update it in place rather than creating a duplicate ID. Keep IDs stable.

## Integration Rules

Wire assets only where they improve the actual game UI:

- Use CSS background layers for tavern scene art and table surfaces.
- Use `<img>` or render helper output for semantic or positioned assets only when needed.
- Keep live gameplay information rendered by code: cards, pot, player names, stacks, action state, buttons, timers, and status labels.
- Set explicit dimensions, aspect ratios, `object-fit`, `object-position`, and `pointer-events` behavior.
- Preserve the current 8-seat layout: human seat bottom-center, seats 1-7 around the table, community cards in the fixed center zone, action buttons outside table art.
- Avoid external asset URLs. All final assets must live under the repo.

## QA Output

End asset-generation tasks with a concise report:

- Files generated and saved.
- Manifest entries changed.
- App integration locations changed, such as CSS selectors or `token_holdem/render.py` helpers.
- Visual QA notes: match to art direction, readability, transparency, crop safety, no prohibited logos/text.
- Checks run and results.
