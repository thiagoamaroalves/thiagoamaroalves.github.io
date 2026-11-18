import { getCollection } from 'astro:content';
import { notePath, postPath } from '../utils/routes';
import { topics, topicHref } from '../data/topics';

export const prerender = true;

export async function GET() {
  const siteUrl = new URL('https://thiagoamaroalves.github.io');
  const base = siteUrl.toString().replace(/\/$/, '');
  const posts = await getCollection('posts');
  const notes = await getCollection('notes');
  const fixedPaths = [
    '/', '/en/', '/artigos/', '/en/writing/', '/notas/', '/en/notes/',
    '/sobre/', '/en/about/', '/buscar/', '/en/search/',
    ...topics.flatMap((topic) => [topicHref(topic, 'pt'), topicHref(topic, 'en')]),
  ];
  const datedPaths = [
    ...posts.map((post) => ({ path: postPath(post), date: post.data.pubDate.toISOString() })),
    ...notes.map((note) => ({ path: notePath(note), date: note.data.pubDate.toISOString() })),
  ];
  const urls = [
    ...fixedPaths.map((path) => ({ path, date: undefined as string | undefined })),
    ...datedPaths,
  ].map(({ path, date }) => `
  <url><loc>${base}${path}</loc>${date ? `<lastmod>${date}</lastmod>` : ''}</url>`).join('');
  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">${urls}
</urlset>`;

  return new Response(xml, { headers: { 'Content-Type': 'application/xml; charset=utf-8' } });
}
