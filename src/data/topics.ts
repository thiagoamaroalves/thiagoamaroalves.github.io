import type { Language } from '../utils/routes';

export interface Topic {
  slug: string;
  englishSlug: string;
  category: string;
  icon: 'architecture' | 'database' | 'distributed' | 'performance';
  copy: Record<Language, { title: string; description: string; eyebrow: string }>;
  tags: string[];
}

export const topics: Topic[] = [
  {
    slug: 'arquitetura',
    englishSlug: 'architecture',
    category: 'Architecture',
    icon: 'architecture',
    tags: ['architecture', 'arquitetura', 'design', 'boundaries', 'trade-offs'],
    copy: {
      pt: { title: 'Arquitetura', description: 'Limites, decisões e sistemas que evoluem.', eyebrow: 'Estrutura e mudança' },
      en: { title: 'Architecture', description: 'Boundaries, decisions, and systems that evolve.', eyebrow: 'Structure and change' },
    },
  },
  {
    slug: 'bancos-de-dados',
    englishSlug: 'databases',
    category: 'Databases',
    icon: 'database',
    tags: ['database', 'databases', 'postgresql', 'sql', 'banco de dados'],
    copy: {
      pt: { title: 'Bancos de dados', description: 'Persistência, consistência e recuperação.', eyebrow: 'Dados e persistência' },
      en: { title: 'Databases', description: 'Persistence, consistency, and recovery.', eyebrow: 'Data and persistence' },
    },
  },
  {
    slug: 'sistemas-distribuidos',
    englishSlug: 'distributed-systems',
    category: 'Distributed Systems',
    icon: 'distributed',
    tags: ['distributed systems', 'sistemas distribuídos', 'consistency', 'availability'],
    copy: {
      pt: { title: 'Sistemas distribuídos', description: 'Coordenação, falhas e consistência em escala.', eyebrow: 'Coordenação e falhas' },
      en: { title: 'Distributed systems', description: 'Coordination, failure, and consistency at scale.', eyebrow: 'Coordination and failure' },
    },
  },
  {
    slug: 'performance',
    englishSlug: 'performance',
    category: 'Performance',
    icon: 'performance',
    tags: ['performance', 'latency', 'throughput', 'benchmark'],
    copy: {
      pt: { title: 'Performance', description: 'Medições, latência e escolhas de capacidade.', eyebrow: 'Medir e compreender' },
      en: { title: 'Performance', description: 'Measurement, latency, and capacity choices.', eyebrow: 'Measure and understand' },
    },
  },
];

export const topicHref = (topic: Topic, language: Language) =>
  language === 'pt' ? `/topicos/${topic.slug}/` : `/en/topics/${topic.englishSlug}/`;
