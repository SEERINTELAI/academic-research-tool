'use client';

import { useState } from 'react';
import { Search, Loader2, ExternalLink, Plus, FileText } from 'lucide-react';
import { toast } from 'sonner';
import { api, PaperSearchResult } from '@/lib/api';
import { useAuthStore } from '@/lib/store';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';

function SearchResultCard({ paper }: { paper: PaperSearchResult }) {
  return (
    <Card className="border-border/50 transition-colors hover:border-primary/30">
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 space-y-2">
            <h4 className="font-serif font-semibold leading-snug">{paper.title}</h4>
            <p className="text-sm text-muted-foreground">
              {paper.authors?.slice(0, 3).map((a) => a.name).join(', ')}
              {paper.authors?.length > 3 && ` +${paper.authors.length - 3} more`}
            </p>
            <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
              {paper.year && <Badge variant="secondary">{paper.year}</Badge>}
              {paper.venue && (
                <span className="max-w-[200px] truncate">{paper.venue}</span>
              )}
              {paper.citation_count !== null && (
                <span>{paper.citation_count} citations</span>
              )}
            </div>
            {paper.abstract && (
              <p className="line-clamp-3 text-sm text-muted-foreground">
                {paper.abstract}
              </p>
            )}
          </div>
          <div className="flex flex-col gap-2">
            {paper.pdf_url && (
              <Button size="sm" variant="outline" asChild>
                <a href={paper.pdf_url} target="_blank" rel="noopener noreferrer">
                  <ExternalLink className="h-4 w-4" />
                </a>
              </Button>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default function SearchPage() {
  const token = useAuthStore((s) => s.token);
  const [query, setQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [results, setResults] = useState<PaperSearchResult[]>([]);
  const [hasSearched, setHasSearched] = useState(false);

  const authToken = token || 'demo-token';

  const handleSearch = async () => {
    if (!query.trim()) return;

    setIsSearching(true);
    setHasSearched(true);
    try {
      const response = await api.searchPapers(authToken, query);
      setResults(response.results);
    } catch (error) {
      toast.error('Search failed. Please try again.');
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <div className="page-transition p-6">
      <div className="mb-8">
        <h1 className="font-serif text-3xl font-bold">Search Papers</h1>
        <p className="mt-1 text-muted-foreground">
          Find academic papers from Semantic Scholar
        </p>
      </div>

      <Card className="mb-8">
        <CardHeader>
          <CardTitle className="font-serif">Search Academic Literature</CardTitle>
          <CardDescription>
            Enter keywords, paper titles, or author names to find relevant research.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2">
            <Input
              placeholder="e.g., deep learning for natural language processing"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              className="flex-1"
            />
            <Button onClick={handleSearch} disabled={isSearching || !query.trim()}>
              {isSearching ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Search className="mr-2 h-4 w-4" />
              )}
              Search
            </Button>
          </div>
        </CardContent>
      </Card>

      {isSearching ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      ) : results.length > 0 ? (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-serif text-xl font-semibold">
              Results ({results.length})
            </h2>
          </div>
          <ScrollArea className="h-[calc(100vh-24rem)]">
            <div className="space-y-4 pr-4">
              {results.map((paper) => (
                <SearchResultCard key={paper.paper_id} paper={paper} />
              ))}
            </div>
          </ScrollArea>
        </div>
      ) : hasSearched ? (
        <Card className="border-dashed">
          <CardContent className="py-16 text-center">
            <FileText className="mx-auto mb-4 h-12 w-12 text-muted-foreground/50" />
            <h3 className="mb-2 font-serif text-xl font-semibold">No results found</h3>
            <p className="text-muted-foreground">
              Try different keywords or check your spelling.
            </p>
          </CardContent>
        </Card>
      ) : (
        <Card className="border-dashed">
          <CardContent className="py-16 text-center">
            <Search className="mx-auto mb-4 h-12 w-12 text-muted-foreground/50" />
            <h3 className="mb-2 font-serif text-xl font-semibold">
              Start your search
            </h3>
            <p className="text-muted-foreground">
              Enter a query above to search millions of academic papers.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

