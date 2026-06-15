---
name: pixel-tavern-art-director
description: Define and maintain the visual art direction for Token Hold'em, a cozy pixel-art tavern poker game. Use when Codex is asked for tavern atmosphere, pixel art direction, background or environment prompts, lighting, palette, mood, camera angle, visual consistency, style bibles, image generation prompts, negative prompts, visual QA, or premium game-ready tavern poker scene guidance. Do not use to generate final background art until gameplay layout constraints are known.
---

# Pixel Tavern Art Director

## Overview

Use this skill to keep Token Hold'em's tavern poker visuals coherent across planning, prompt writing, implementation, and QA. Always preserve the core scene: warm cozy tavern, stone walls, candlelight, bar and bartender in the background, and a large central poker table.

## Hard Gate

Do not generate or request final background art until the gameplay layout constraints are known. First ask for or infer the required layout facts:

- Target aspect ratio and resolution.
- Poker table footprint and UI safe zones.
- Camera angle and crop.
- Seat, card, chip, button, pot, and player avatar positions.
- Areas that must stay visually quiet for text, controls, and card readability.

If constraints are missing, produce a style bible, exploration prompts, composition studies, or placeholder-safe prompt drafts only.

## Workflow

1. Read `references/style-bible.md` before producing art direction, prompts, QA notes, or visual consistency guidance.
2. Identify the requested artifact: style bible, prompt set, negative prompt, consistency rules, QA checklist, or critique.
3. State any missing gameplay layout constraints when the request implies final background art.
4. Keep the art direction premium, charming, readable, and game-ready rather than painterly, noisy, generic fantasy, or decorative-only.
5. Output practical artifacts that can be reused by design, implementation, or image-generation work.

## Output Shapes

For a style bible, include: visual thesis, composition, palette, lighting, materials, props, characters, camera, pixel rendering, readability rules, and exclusions.

For image generation prompts, include:

- Positive prompt.
- Negative prompt.
- Layout assumptions or missing constraints.
- Notes for keeping the result editable/game-ready.

For visual QA, evaluate:

- Tavern identity and poker-table focus.
- Readability of gameplay areas.
- Palette and lighting consistency.
- Pixel-art discipline.
- Background depth without UI competition.
- Bartender/bar presence without stealing focus.
