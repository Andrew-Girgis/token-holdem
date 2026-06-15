---
name: llm-avatar-personification
description: Design Token Hold'em AI model poker avatars as readable tavern characters inspired by model personalities rather than exact company logos. Use when Codex needs avatar concepts, LLM character designs, poker personas, professor/maverick/villain/etc. variants, sprite prompts, portrait prompts, image generation prompts, transparent asset requirements, expression or emote states, naming conventions, or consistency checklists for AI player avatars.
---

# LLM Avatar Personification

## Overview

Design AI player avatars for Token Hold'em as charming tavern poker characters. Favor recognizable personality motifs, poker readability, and asset consistency; avoid exact trademark, logo, mascot, or product-UI reproduction.

## Workflow

1. Identify the model or personality seed.
2. Translate it into broad character traits, not brand marks.
3. Choose a poker-table role: professor, maverick, villain, oracle, tinkerer, shark, diplomat, trickster, monk, analyst, showboat, or other table archetype.
4. Define silhouette, wardrobe, prop, expression, and color accents.
5. Produce portrait and sprite prompts with transparent-background requirements.
6. Add expression states and a consistency checklist.

## Character Translation

Use these transformations:

- Capability -> table behavior: reasoning becomes calculating, speed becomes impatient, alignment becomes honorable, creativity becomes theatrical.
- Model family or company vibe -> indirect motif: academic, explorer, inventor, archivist, dealer, stage magician, clockmaker, cartographer, gambler, librarian.
- Brand color -> optional accent only; never make it the whole identity.
- Logo shape -> generic visual rhythm only, such as geometric pins, abstract embroidery, card-suit charms, or patterned trim.
- Technical trait -> prop: notebook, slide rule, brass goggles, annotated cards, probability chalk, lucky coin, pocket watch, sealed envelope, data ledger.

Keep the avatar grounded in a tavern poker room: felt table light, worn wood, cards, chips, tankards, candle glow, smoke-free warm atmosphere, and a readable bust or half-body pose.

## Persona Patterns

- Professor: glasses, tidy tie or vest, annotated cards, calm raised eyebrow, probability notes.
- Maverick: cowboy hat, toothpick, loose scarf, cocky grin, angled card fan, worn lucky chip.
- Villain: velvet coat, sharp collar, controlled smirk, dramatic shadows, ornate card sleeve; keep charming, not grimdark.
- Oracle: layered shawl, moonlit cards, crystal chip, knowing smile, soft glow, subtle mystical props.
- Tinkerer: brass goggles, tool belt, clockwork card shuffler, ink-stained fingers, curious squint.
- Shark: crisp suit, narrow eyes, shark-tooth tie pin or card-suit pin, stacked chips, predatory patience.
- Diplomat: polished vest, open palms, tasteful lapel pin, warm smile, balanced chip stacks.
- Trickster: mismatched gloves, hidden ace, wink, jester-adjacent trim, playful misdirection.

## Output Format

When asked to design avatars, return concise sections:

```markdown
## <Avatar Name>
- Seed: <model/personality inspiration>
- Persona: <poker archetype>
- Read: <one-line visual read at small size>
- Concept: <2-4 sentences>
- Signature Motifs: <5-8 bullets>
- Palette: <3-5 colors, with role for each>
- Portrait Prompt: <image generation prompt>
- Sprite Prompt: <image generation prompt>
- Transparent Asset Requirements: <technical requirements>
- Emote States: <state list>
- Naming: <file/name conventions>
- Consistency Checklist: <pass/fail bullets>
```

For multiple avatars, keep every avatar structurally parallel so the set feels like a cast.

## Prompt Recipe

Build prompts from these parts:

```text
Token Hold'em AI poker avatar, <persona archetype>, <silhouette>, <face/expression>,
<wardrobe>, <poker props>, <indirect model-inspired motifs>, tavern poker room mood,
readable charming game art, clean shape language, strong silhouette, transparent background,
no text, no logos, no brand marks, no UI screenshots, no exact mascot likeness
```

Add style constraints appropriate to the asset:

- Portrait: bust or waist-up, centered, 3/4 view, expressive face, soft rim light, enough detail for dialogue or player cards.
- Sprite: full-body or chibi-like game token, simple edges, limited detail, readable at small size, neutral stance, consistent scale.
- Pixel sprite: fixed pixel-art perspective, limited palette, clean clusters, no anti-aliased painterly detail unless the target renderer supports it.

## Transparent Asset Requirements

Specify these requirements when generating production-ready assets:

- Transparent PNG or WebP with alpha.
- No background, frame, text, watermark, logos, or card-readable copyrighted symbols.
- Character fully inside canvas with 5-10% padding.
- Consistent camera angle and lighting across all avatars.
- Clear silhouette at thumbnail size.
- Props should not overlap the face or hide the hands unless intentionally part of the pose.
- Export portraits and sprites separately if both are needed.
- Keep prompts compatible with later sprite-sheet generation by avoiding cropped limbs and extreme poses.

## Expression States

Default to these emotes unless the user requests a different set:

- `neutral`: table-ready idle expression.
- `confident`: strong hand, raised bet, or successful bluff.
- `thinking`: calculating odds, reading opponent.
- `surprised`: bad beat or unexpected reveal.
- `smug`: won pot or called a bluff.
- `worried`: short stack or risky call.
- `celebrate`: winning hand.
- `defeated`: bust-out or folded monster.

For sprite sheets, keep the body pose mostly stable and vary face, shoulders, hands, and small props so states remain consistent.

## Naming Conventions

Use stable lowercase slugs:

- Avatar slug: `<model-or-persona>-<archetype>`, for example `logic-professor`, `frontier-maverick`, `cipher-villain`.
- Portrait file: `avatar_<slug>_portrait.png`.
- Sprite file: `avatar_<slug>_sprite.png`.
- Emote file: `avatar_<slug>_<state>.png`.
- Prompt file: `avatar_<slug>_prompts.md`.

Use display names that sound like tavern poker characters, not product names: `Professor Quill`, `Maverick Byte`, `Lady Longshot`, `The Velvet Oracle`, `Doc River`, `Captain Context`.

## Trademark And Safety Rules

Never request or recreate exact logos, trademarked mascots, product icons, company wordmarks, UI marks, or direct copies of public brand characters. Prefer inspired, generic motifs. If the user asks for a direct logo-like avatar, redirect to a non-infringing tavern character inspired by broad traits.

Do:

- Use glasses and a tie for a professor persona.
- Use a cowboy hat and toothpick for a maverick persona.
- Use abstract geometric trim instead of a logo.
- Use color accents sparingly.
- Make the poker role obvious before the model reference.

Do not:

- Put a company logo on clothing, cards, chips, hats, or props.
- Copy a mascot, robot, app icon, swirl, wordmark, or exact color-block layout.
- Make a character primarily identifiable as a specific company mark.
- Use text labels on the generated asset to carry the identity.

## Consistency Checklist

Before finalizing, verify:

- The avatar reads as a poker/tavern character at thumbnail size.
- The persona is visible through silhouette, expression, wardrobe, and prop.
- Model inspiration is indirect and non-logo-based.
- Prompt includes transparent background and no text/logos/brand marks.
- Portrait and sprite prompts share the same identity anchors.
- Emote states can be generated without redesigning the character.
- Names and filenames use stable slugs.
- The set has visual variety across archetypes while preserving Token Hold'em cohesion.
