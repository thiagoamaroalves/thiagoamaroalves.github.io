import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';
import { z } from 'astro/zod';

const posts = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/posts' }),
  schema: z.object({
    title: z.string(),
    description: z.string(),
    pubDate: z.coerce.date(),
    language: z.enum(['pt', 'en']).default('en'),
    category: z.enum([
      'Architecture',
      'Databases',
      'Distributed Systems',
      'Performance',
      'Engineering',
      'Programming',
      'AI',
    ]),
    tags: z.array(z.string()),
    readingTime: z.string(),
    featured: z.boolean().default(false),
    translationKey: z.string().optional(),
  }),
});

const notes = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/notes' }),
  schema: z.object({
    title: z.string(),
    description: z.string(),
    pubDate: z.coerce.date(),
    language: z.enum(['pt', 'en']).default('en'),
    category: z.enum(['Databases', 'Architecture', 'Benchmark', 'Distributed Systems', 'Performance']),
    tags: z.array(z.string()).default([]),
    readingTime: z.string(),
    translationKey: z.string().optional(),
  }),
});

export const collections = { posts, notes };
