# Repository Guidelines

## Project Structure

This is an English language technical blog built with Astro and published as a static site on GitHub Pages. Pages and layouts live in `src/pages/` and `src/layouts/`; global styles are in `src/styles/`; Markdown articles and their frontmatter are in `src/content/posts/`; public assets are in `public/`. Keep article content separate from presentation code.

## Development Commands

- `npm install` installs the dependencies recorded in `package-lock.json`.
- `npm run dev` starts Astro's local development server.
- `npm run build` generates the production site in `dist/`.
- `npm run preview` serves the built site locally for a final visual check.

## Writing & Coding Style

Write published pages and articles in English. Use sentence case headings, concise paragraphs, and descriptive link text. Name article files with lowercase kebab case (for example, `architecture-is-a-bet-on-change.md`). Every article needs a title, summary, publication date, category, and tags in its frontmatter. Use Astro components for reusable page structure, TypeScript for build-time content logic, and CSS variables in `src/styles/global.css` for shared visual tokens. Keep layouts responsive and keyboard accessible.

## Validation

Before publishing, run `npm run build` and resolve build errors. Review changed pages with the local preview and confirm that navigation, article links, RSS, and sitemap output work. There is no separate automated test suite yet.

## Commits & Pull Requests

Use concise imperative commit subjects, optionally scoped, such as `content: add article on modular boundaries`. Pull requests should explain the reader-facing change and list the validation performed. Include screenshots for visual changes. Since this repository is published publicly, do not commit credentials, private drafts, or personal information that is not intended for publication.

## Publishing

The `main` branch deploys through `.github/workflows/deploy.yml`. GitHub Pages serves the user site at `https://thiagoamaroalves.github.io`; keep `site` in `astro.config.mjs` in sync if the account or public URL changes.
