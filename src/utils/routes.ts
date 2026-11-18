import type { CollectionEntry } from 'astro:content';

export type Language = 'pt' | 'en';
export type Post = CollectionEntry<'posts'>;
export type Note = CollectionEntry<'notes'>;

export function postPath(post: Post, legacy = false) {
  if (post.data.language === 'pt') return `/artigos/${post.id}/`;
  return legacy ? `/writing/${post.id}/` : `/en/writing/${post.id}/`;
}

export function notePath(note: Note) {
  return note.data.language === 'pt' ? `/notas/${note.id}/` : `/en/notes/${note.id}/`;
}

export function localeHome(language: Language) {
  return language === 'pt' ? '/' : '/en/';
}

export function formatDate(date: Date, language: Language) {
  return new Intl.DateTimeFormat(language === 'pt' ? 'pt-BR' : 'en', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    timeZone: 'UTC',
  }).format(date);
}

export function categoryLabel(category: string, language: Language) {
  if (language === 'en') return category;
  const labels: Record<string, string> = {
    Architecture: 'Arquitetura',
    Databases: 'Bancos de dados',
    'Distributed Systems': 'Sistemas distribuídos',
    Performance: 'Performance',
    Engineering: 'Engenharia',
    Programming: 'Programação',
    AI: 'IA',
    Benchmark: 'Benchmark',
  };
  return labels[category] ?? category;
}

export function matchingTranslation<T extends Post | Note>(entry: T, entries: T[]) {
  if (!entry.data.translationKey) return undefined;
  return entries.find(
    (candidate) =>
      candidate.data.translationKey === entry.data.translationKey &&
      candidate.data.language !== entry.data.language,
  );
}
