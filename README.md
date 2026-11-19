# Thiago Alves — Engineering Notes

An independent technical publication about software architecture, databases, distributed systems, and performance. The site is built with Astro and published as a static site on GitHub Pages. Portuguese is the default presentation language; English pages live under `/en/`.

## Develop locally

```sh
npm ci
npm run dev
```

Create a production build with `npm run build` and preview it with `npm run preview`.

## Publish a post

Add a Markdown file under `src/content/posts/` with a lowercase kebab case filename. Include `title`, `description`, `pubDate`, `language`, `category`, `tags`, and `readingTime`. `featured` is optional and defaults to `false`.

Supported post languages are `pt` and `en`. The collection keeps `en` as the schema default for older Markdown entries, so new content should always set `language` explicitly. Supported categories are Architecture, Databases, Distributed Systems, Performance, Engineering, Programming, and AI.

Example frontmatter:

```yaml
---
title: A reviewed post title
description: A concise summary of the post.
pubDate: 2026-11-18
language: pt
category: Architecture
tags:
  - architecture
readingTime: 7 min
featured: false
---
```

Only files in `src/content/posts/` are published as posts. Keep private or unfinished writing elsewhere, such as `drafts/`.

## Publish a note

Add a Markdown file under `src/content/notes/`. Notes use the same metadata and language rules as posts. Their categories are Databases, Architecture, Benchmark, Distributed Systems, and Performance. The notes collection can remain empty; the site shows a real empty state until a note is published.

## Post images and diagrams

Follow the [visual style guide](docs/visual-style-guide.md) for post diagrams and illustrations. Keep English and Portuguese assets paired in `public/images/`, using the same layout, dimensions, and palette in both versions.

## Language and URL decisions

- Portuguese is served at `/`, `/artigos/`, `/notas/`, and `/sobre/`.
- English is served at `/en/`, `/en/writing/`, `/en/notes/`, and `/en/about/`.
- Existing English `/writing/`, `/about/`, and `/writing/:slug/` URLs remain available as canonical aliases to their `/en/` pages. Existing post URLs are preserved when English posts are present.
- English posts without a reviewed Portuguese counterpart remain English. The language switch sends readers to the Portuguese home page and does not label a translation as available.
- To associate reviewed translations, set the same `translationKey` on both language entries. Only associated pairs receive post-level `hreflang` links.
- UI copy is localized in Astro components. Published Markdown is never translated automatically.
- Topic pages and search results are generated from published collections. Search filters the current language's already-rendered entries in the browser.
- `/rss.xml` is the Portuguese feed and `/en/rss.xml` is the English feed. `sitemap.xml` lists canonical routes.

These decisions keep Markdown publishing static, preserve the prior English routes, and avoid treating a missing translation as existing content.

## Deployment

The public site is `https://thiagoamaroalves.github.io`. The `site` value in `astro.config.mjs` stays at the domain root, so links and assets work on this GitHub Pages user site. Pushes to `main` build and deploy through `.github/workflows/deploy.yml`.
