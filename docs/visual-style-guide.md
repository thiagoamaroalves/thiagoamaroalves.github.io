# Visual Style Guide

Use this guide for diagrams and illustrations in posts. Treat the existing diagrams in `public/images/priority-load-shedding/` as references for the site’s visual language.

## Visual language

- Use a restrained editorial, technical style with a warm paper background, a faint square grid, flat shapes, square corners, and thin borders.
- Keep the composition calm and spacious. Use arrows and a small number of labeled panels to explain a relationship or trade-off.
- Do not add gradients, drop shadows, decorative textures, or new colors without a clear reason.

## Color palette

| Token | Color | Use |
| --- | --- | --- |
| Background | `#FAF8F4` | Canvas and paper |
| Surface | `#F2EFE8` | Neutral cards and tracks |
| Panel | `#FFFDF9` | Raised content panels |
| Protected path | `#E7EDF5` | Protected routes, outcomes, or data |
| Constraint highlight | `#E9E2D6` | Pressure, degraded work, or decision points |
| Border | `#D8D2C8` | Dividers and card outlines |
| Ink | `#161616` | Headings and primary labels |
| Muted text | `#5A5A57` | Supporting labels |
| Navy accent | `#1F3A5F` | Grid, arrows, markers, and technical labels |

The grid uses the navy accent at roughly 6% opacity on a 24 px repeat. Avoid traffic-light colors such as saturated red and green, and avoid purple; communicate status with the established blue and warm neutral fills, labels, and shapes instead.

## Type and layout

- Build vector diagrams as SVG at 1200 px wide with a matching `viewBox`; choose the height for the content rather than squeezing labels.
- Use Inter (or a system sans-serif fallback) for headings and explanatory text. Use IBM Plex Mono (or a monospace fallback) for section numbers, metrics, and short technical labels.
- Keep text short, high contrast, and readable when the image scales to the post column. Leave generous outer margins and avoid crowded footnotes.

## English and Portuguese assets

- Keep a matched English and Portuguese version with the same dimensions, layout, palette, and data. Translate labels and descriptions; do not redesign the diagram per language.
- Store the English SVG in `public/images/priority-load-shedding/` and the Portuguese version at the same path under `pt/`, using the same kebab-case filename.
- Give each SVG a meaningful `<title>` and `<desc>`. In the post, use a localized `alt` description and `<figcaption>`; do not rely on color alone to convey meaning.

## Reusable image prompt

Start image-generation prompts with this direction, then describe the subject:

> Create a restrained editorial technical illustration for the Built to Change blog. Use warm paper `#FAF8F4`, a barely visible 24 px navy grid `#1F3A5F`, square flat panels, thin `#D8D2C8` borders, pale blue `#E7EDF5`, warm taupe `#E9E2D6`, and neutral `#F2EFE8`. Use dark ink `#161616`, muted gray `#5A5A57`, Inter-style explanatory text, and IBM Plex Mono-style technical labels. Keep the layout spacious and precise. Do not introduce gradients, shadows, saturated red or green, or purple.

For diagrams containing important labels, metrics, or exact text, prefer hand-authored SVG so the wording remains accurate. After adding an image, run `npm run build` and review it in the local preview at both desktop and mobile widths.
