import { getCollection } from 'astro:content';

export const prerender = true;

export async function GET() {
  const siteUrl = new URL('https://thiagoamaroalves.github.io');
  const base = siteUrl.toString().replace(/\/$/, '');
  const posts = await getCollection('posts');
  const pages = [
    { path: '/', date: undefined },
    { path: '/about/', date: undefined },
    { path: '/writing/', date: undefined },
    ...posts.map((post) => ({ path: `/writing/${post.id}/`, date: post.data.pubDate.toISOString() })),
  ];
  const urls = pages.map(({ path, date }) => `
  <url><loc>${base}${path}</loc>${date ? `<lastmod>${date}</lastmod>` : ''}</url>`).join('');
  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">${urls}
</urlset>`;

  return new Response(xml, { headers: { 'Content-Type': 'application/xml; charset=utf-8' } });
}
