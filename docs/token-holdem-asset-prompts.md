# Token Hold'em Asset Prompts

Reusable prompt layer for future Token Hold'em UI art. These prompts are documentation only: no external assets, generated images, or production image files are included.

## Shared Direction

- Style: cozy pixel-art tavern poker UI, warm candle and hearth light, worn wood, green felt, brass accents, readable silhouettes.
- Camera: slightly above table height for room and prop assets; top-down or mild 3/4 view for table, cards, and chips.
- Output: no text, no logos, no UI screenshots, no watermark, no baked player names, no baked card ranks unless the slot explicitly requires card-face art.
- UI rule: live game information remains rendered by code, including pot, street, player names, stacks, actions, badges, card labels, and buttons.
- Palette guardrail: warm tavern neutrals plus green felt and brass accents; avoid a one-note brown/orange scene by including controlled green, burgundy, slate, and gold contrast.

## Tavern Background

```text
Token Hold'em game background, cozy pixel-art fantasy tavern poker room, camera slightly above table height, warm candle and hearth lighting, worn wood beams, green felt color echoes, brass accents, darker low-detail central area reserved for an overlaid poker table and center HUD, clear safe margins for seat panels around the table, no text, no logos, no playing cards in the background, no UI screenshot, 16:9 canvas, designed for full-bleed web game UI with desktop and tall mobile crop safety.
```

Slot notes:

- Target placeholder: `tavern-bg-main`.
- Preferred canvas: 1920x1080 or 2560x1440, no alpha.
- Keep important scene detail away from the table center and mobile lower seat area.

## Poker Table

```text
Token Hold'em poker table asset, cozy pixel-art oval green felt table, warm tavern lighting from upper left, worn wood rim, subtle stitched felt texture, quiet center area for live community cards and pot HUD, no baked cards, no chips, no labels, no player names, no UI screenshot, transparent background with clean alpha edges, centered with 8 percent padding, 3/4 top-down perspective matching a web poker table.
```

Slot notes:

- Target placeholder: `table-felt-top`.
- Preferred canvas: 1536x864 or 2048x1152, PNG alpha.
- The existing UI has 8 fixed seats around the ring; the rim must not fight seat panels.

## Dealer Button

```text
Single dealer button chip for Token Hold'em poker UI, cozy pixel-art ivory poker chip with brass edge, readable at 30 CSS pixels, simple centered dealer mark, warm tavern light from upper left, crisp circular silhouette, no extra objects, no brand marks, transparent background, centered with 12 percent padding, no baked shadow outside the object.
```

Slot notes:

- Target placeholder: `dealer-button-idle`.
- Preferred canvas: 256x256, PNG alpha.
- Must stay readable when positioned near any of the 8 seats.

## Card Back

```text
Token Hold'em hidden card back, cozy pixel-art playing card back, rounded rectangle, deep burgundy and green felt pattern with small brass corner details, readable at mini-card size, no rank, no suit, no text, no logo, no watermark, no extra objects, flat card face with subtle edge highlight, consistent poker UI proportions.
```

Slot notes:

- Target placeholder: `card-back-hidden`.
- Preferred canvas: 512x716, opaque PNG unless future renderer requires alpha.
- Pattern should still read at 24-28 CSS px wide.

## Seat Panel

```text
Token Hold'em player seat panel frame, cozy pixel-art tavern poker material, subtle wood, leather, and brass border, designed to sit behind live CSS text and avatar slot, clean inner safe area, no baked words, no labels, no badges, no cards, transparent background, compact readable edge treatment for repeated poker seats, idle state.
```

Variant modifiers:

- `active`: brighter brass rim and candle glint, not color-only.
- `folded`: dimmed desaturated edge, still legible.
- `all-in`: green-gold tension accent, no text.
- `empty`: softer low-contrast frame.

Slot notes:

- Target placeholder: `seat-panel-frame`.
- Preferred canvas: 768x384, PNG alpha.
- Must support compact desktop seats and two-column mobile seat cards.

## Ambient Candle

```text
Single tavern candle prop for Token Hold'em poker UI, cozy pixel-art candle in a small brass holder, warm flame, transparent background, isolated object, crisp silhouette, light from upper left, no text, no logo, no baked background, centered with 10 percent padding, no large glow outside the object.
```

Slot notes:

- Target placeholder: `ambient-candle-prop`.
- Preferred canvas: 256x512 or 512x1024, PNG alpha.
- Use only where it does not reduce text contrast or cover controls.

## QA Checklist

- Check desktop and mobile crops before generating final art.
- Verify transparent assets on both light and dark backgrounds.
- Confirm no baked words conflict with live Gradio labels.
- Confirm no prop blocks cards, pot, stacks, badges, or action buttons.
- Keep generated assets registered in `assets/token-holdem/manifest.json` before integration.
