'use client';

import Link from 'next/link';
import { ArrowRight, BookOpen, FileText, Library, Search, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

const features = [
  {
    icon: FileText,
    title: 'Structured Outlines',
    description: 'Build your research outline with AI-assisted section generation and research questions.',
  },
  {
    icon: Search,
    title: 'Paper Discovery',
    description: 'Search Semantic Scholar, explore citations, and build your knowledge graph.',
  },
  {
    icon: Library,
    title: 'Smart Ingestion',
    description: 'PDFs are automatically parsed and indexed for intelligent retrieval.',
  },
  {
    icon: BookOpen,
    title: 'AI Writing Assist',
    description: 'Write with context-aware suggestions and automatic citation insertion.',
  },
];

export default function HomePage() {
  return (
    <div className="page-transition">
      {/* Hero */}
      <section className="relative overflow-hidden border-b border-border">
        <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-accent/10" />
        <div className="relative mx-auto max-w-4xl px-6 py-20 text-center">
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/5 px-4 py-1.5 text-sm text-primary">
            <Sparkles className="h-4 w-4" />
            AI-Powered Research
          </div>
          <h1 className="mb-4 font-serif text-5xl font-bold tracking-tight md:text-6xl">
            Your Research,
            <br />
            <span className="text-primary">Accelerated</span>
          </h1>
          <p className="mx-auto mb-8 max-w-xl text-lg text-muted-foreground">
            From outline to publication. Search papers, synthesize findings, and write with
            AI assistance—all with perfect citations.
          </p>
          <div className="flex flex-wrap items-center justify-center gap-4">
            <Button asChild size="lg" className="gap-2">
              <Link href="/projects/new">
                Start a Project
                <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
            <Button asChild variant="outline" size="lg">
              <Link href="/projects">View Projects</Link>
            </Button>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="mx-auto max-w-5xl px-6 py-16">
        <h2 className="mb-12 text-center font-serif text-3xl font-semibold">
          Everything You Need
        </h2>
        <div className="grid gap-6 md:grid-cols-2">
          {features.map((feature) => (
            <Card key={feature.title} className="border-border/50 bg-card/50">
              <CardHeader>
                <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                  <feature.icon className="h-5 w-5 text-primary" />
                </div>
                <CardTitle className="font-serif">{feature.title}</CardTitle>
                <CardDescription>{feature.description}</CardDescription>
              </CardHeader>
            </Card>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="border-t border-border bg-muted/30">
        <div className="mx-auto max-w-4xl px-6 py-16 text-center">
          <h2 className="mb-4 font-serif text-2xl font-semibold">Ready to Begin?</h2>
          <p className="mb-6 text-muted-foreground">
            Create your first project and start researching smarter.
          </p>
          <Button asChild size="lg">
            <Link href="/projects/new">Create Project</Link>
          </Button>
        </div>
      </section>
    </div>
  );
}
