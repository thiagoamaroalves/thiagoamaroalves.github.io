import { getCollection } from 'astro:content';
import { notePath, postPath } from '../utils/routes';

export const prerender = true;

const siteUrl = new URL('https://thiagoamaroalves.github.io');
const escapeXml = (value: string) =>
  value.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&apos;');

export async function GET() {
  const posts = (await getCollection('posts')).filter((entry) => entry.data.language === 'pt');
  const notes = (await getCollection('notes')).filter((entry) => entry.data.language === 'pt');
  const items = [...posts, ...notes]
    .sort((a, b) => b.data.pubDate.valueOf() - a.data.pubDate.valueOf())
    .map((entry) => {
      const path = entry.collection === 'posts' ? postPath(entry) : notePath(entry);
      const url = new URL(path, siteUrl);
      return `
    <item>
      <title>${escapeXml(entry.data.title)}</title>
      <link>${url}</link>
      <guid>${url}</guid>
      <description>${escapeXml(entry.data.description)}</description>
      <pubDate>${entry.data.pubDate.toUTCString()}</pubDate>
      <category>${escapeXml(entry.data.category)}</category>
    </item>`;
    })
    .join('');
  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
  <title>Thiago Alves — Engineering Notes</title>
  <link>${siteUrl}</link>
  <description>Artigos e notas sobre arquitetura de software, bancos de dados e sistemas distribuídos.</description>
  <language>pt-BR</language>${items}
</channel></rss>`;

  return new Response(xml, { headers: { 'Content-Type': 'application/rss+xml; charset=utf-8' } });
}
