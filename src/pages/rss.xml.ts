import { getCollection } from 'astro:content';

export const prerender = true;

const escapeXml = (value: string) =>
  value.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&apos;');

export async function GET() {
  const siteUrl = new URL('https://thiagoamaroalves.github.io');
  const posts = (await getCollection('posts')).sort(
    (a, b) => b.data.pubDate.valueOf() - a.data.pubDate.valueOf(),
  );
  const items = posts.map((post) => `
    <item>
      <title>${escapeXml(post.data.title)}</title>
      <link>${new URL(`/writing/${post.id}/`, siteUrl)}</link>
      <guid>${new URL(`/writing/${post.id}/`, siteUrl)}</guid>
      <description>${escapeXml(post.data.description)}</description>
      <pubDate>${post.data.pubDate.toUTCString()}</pubDate>
      <category>${escapeXml(post.data.category)}</category>
    </item>`).join('');
  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
  <title>Built to Change</title>
  <link>${siteUrl}</link>
  <description>Ideas and trade-offs for building software that evolves.</description>
  <language>en</language>${items}
</channel></rss>`;

  return new Response(xml, { headers: { 'Content-Type': 'application/rss+xml; charset=utf-8' } });
}
