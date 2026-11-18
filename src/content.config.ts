import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';
import { z } from 'astro/zod';

const posts = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/posts' }),
  schema: z.object({
    title: z.string(),
    description: z.string(),
    pubDate: z.coerce.date(),
    category: z.enum(['Architecture', 'Engineering', 'Programming', 'AI']),
    tags: z.array(z.string()),
    readingTime: z.string(),
    featured: z.boolean().default(false),
  }),
});

export const collections = { posts };
