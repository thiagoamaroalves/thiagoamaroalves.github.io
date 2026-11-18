# Built to Change

Ideas and trade-offs for building software that evolves.

An English language technical blog about software architecture, engineering practice, programming, and practical AI. Articles are written in Markdown and rendered by Astro as a static site.

## Develop locally

```sh
npm install
npm run dev
```

Create a production build with `npm run build` and preview it with `npm run preview`.

## Write an article

Add a Markdown file in `src/content/posts/` using a lowercase kebab case filename. Include `title`, `description`, `pubDate`, `category`, `tags`, `readingTime`, and `featured` fields in its frontmatter. Supported categories are Architecture, Engineering, Programming, and AI.

## Publish

The public site is `https://thiagoamaroalves.github.io`. Pushes to `main` build and deploy the site using the workflow in `.github/workflows/deploy.yml` and GitHub Pages. GitHub Pages requires this personal account's repository to be public on the free plan.
