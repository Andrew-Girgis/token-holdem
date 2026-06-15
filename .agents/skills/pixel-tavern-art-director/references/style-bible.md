# Token Hold'em Pixel Tavern Style Bible

## Visual Thesis

Create a warm, premium pixel-art tavern poker room: stone walls, candlelight, a bar and bartender in the background, and a large central poker table. The scene should feel cozy, charming, readable, and game-ready. It should support repeated gameplay, not only look good as a standalone illustration.

## Composition

- Anchor the scene on a large central poker table with clear felt surface, readable edge silhouette, and enough open space for cards, chips, pot, player positions, and controls.
- Place the bar and bartender in the background, centered or slightly off-center, visible but lower contrast than the table.
- Use stone walls, wooden beams, shelves, mugs, bottles, candles, and subtle tavern props to establish place.
- Keep the foreground and table zone clean. Put detail density around the outer edges and background.
- Prefer a three-quarter top-down camera for gameplay readability unless the product layout specifies another angle.
- Avoid dramatic perspective that distorts card slots, chip stacks, or player seating.

## Palette

Core palette:

- Candle amber: warm highlights for flames, rim light, and small accents.
- Deep walnut: furniture, beams, bar counter, table trim.
- Moss or forest green: poker felt, used as the gameplay anchor.
- Warm gray stone: walls and floor, kept muted so UI and table read clearly.
- Burgundy or muted brass: premium accents, small trim, curtains, bottle labels, coin highlights.

Palette rules:

- Keep saturation controlled. The table felt and candle accents may be the richest colors.
- Use warm highlights and cool-neutral shadows for depth.
- Do not let the whole scene collapse into one brown/orange wash.
- Reserve high contrast for cards, chips, active seats, and interactive objects.

## Lighting

- Primary mood: candlelit warmth with soft amber pools of light.
- Put the strongest readable light on the central table.
- Use small candle and lantern sources around the room, but keep them subordinate to gameplay clarity.
- Let the bar recede with softer, dimmer light.
- Avoid harsh noir lighting, neon, fog-heavy fantasy lighting, or bright daylight.

## Pixel Rendering

- Use crisp pixel art with deliberate clusters, clean silhouettes, and readable material separation.
- Prefer limited-detail textures: stone blocks, wood grain, felt nap, bottle glints, candle halos.
- Use simple dither or cluster shading sparingly; do not create noisy microtexture.
- Avoid anti-aliased painterly brushwork, photorealism, 3D render language, and overly smooth gradients.
- Match asset scale across table, props, bartender, candles, and UI-adjacent objects.

## Background And Environment Prompts

Use these as prompt modules. Combine only after checking layout constraints.

Base prompt:

```text
cozy premium pixel-art tavern poker room, large central green felt poker table, warm candlelight, stone walls, wooden beams, bar counter and friendly bartender in the background, shelves with bottles and mugs, charming handcrafted game background, three-quarter top-down camera, readable gameplay composition, clean silhouettes, warm amber highlights, muted stone grays, deep walnut wood, restrained burgundy and brass accents, crisp pixel clusters, game-ready environment art
```

Layout-safe exploration prompt:

```text
pixel-art tavern poker environment concept, central poker table reserved as a clean gameplay zone, background bar with bartender kept lower contrast, stone wall texture, candlelit atmosphere, cozy premium card-game mood, clear UI-safe areas, readable card and chip placement space, no final crop, composition study, game art direction sheet
```

Prompt additions by need:

- More cozy: `soft candle pools, lived-in tavern details, warm wood, gentle shadows, inviting mood`
- More premium: `polished brass trim, refined felt table, elegant bottle silhouettes, clean composition, restrained ornament`
- More readable: `low-detail background, clear table silhouette, quiet UI-safe margins, separated value contrast`
- More pixel-authentic: `limited palette, crisp hard pixel edges, deliberate clusters, small controlled dithering`

## Negative Prompts

Use or adapt:

```text
photorealistic, 3D render, painterly, smooth airbrush, blurry, low resolution smear, noisy microdetail, over-detailed background, cluttered table, unreadable cards, warped perspective, fisheye lens, extreme closeup, empty tavern, no poker table, no bartender, cold neon lighting, bright daylight, horror mood, grimy dungeon, generic fantasy castle, medieval battlefield, anime character focus, UI text, logos, watermarks
```

Add when final-art constraints are missing:

```text
final production background, locked crop, baked-in UI, fixed card positions, irreversible composition
```

## Consistency Rules

- Always include the stone-walled tavern, candlelight, bar, bartender, and central poker table unless the user explicitly revises the game concept.
- Keep the poker table the visual and functional focal point.
- Maintain warm tavern charm without sacrificing card and chip readability.
- Let the bartender read as background life, not a primary character portrait.
- Keep background props subordinate to the table and UI.
- Ensure generated prompt notes name missing constraints explicitly instead of pretending the final composition is ready.
- Reuse the same palette language across prompts and critiques.

## Visual QA Checklist

- Does the image clearly read as a cozy tavern poker room within one second?
- Are stone walls, candlelight, bar, bartender, and central poker table all present?
- Is the central table clean enough for cards, chips, pot, seats, and controls?
- Are high-detail areas away from likely gameplay UI zones?
- Is the bar visible but lower priority than the table?
- Is the palette warm and premium without becoming a muddy brown/orange scene?
- Are pixel edges crisp, with controlled clusters and minimal noisy texture?
- Does the camera support gameplay readability?
- Are lighting and contrast guiding attention to the table?
- Are there any baked-in UI labels, illegible text, watermarks, or composition locks that would block implementation?
