'use client';

import { useState } from 'react';
import { useParams } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Search,
  Plus,
  ExternalLink,
  FileText,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Clock,
  Download,
  Trash2,
  Network,
} from 'lucide-react';
import { toast } from 'sonner';
import { api, PaperSearchResult, Source } from '@/lib/api';
import { useAuthStore, useSourcesStore, useProjectStore } from '@/lib/store';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

function SearchResultCard({
  paper,
  onAdd,
  isAdding,
}: {
  paper: PaperSearchResult;
  onAdd: (paperId: string) => void;
  isAdding: boolean;
}) {
  return (
    <Card className="border-border/50">
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
              <p className="line-clamp-2 text-sm text-muted-foreground">
                {paper.abstract}
              </p>
            )}
          </div>
          <div className="flex flex-col gap-2">
            <Button
              size="sm"
              onClick={() => onAdd(paper.paper_id)}
              disabled={isAdding}
            >
              {isAdding ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Plus className="h-4 w-4" />
              )}
            </Button>
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

const statusConfig = {
  pending: { icon: Clock, color: 'text-muted-foreground', label: 'Pending' },
  downloading: { icon: Download, color: 'text-blue-500', label: 'Downloading' },
  ingesting: { icon: Loader2, color: 'text-yellow-500', label: 'Ingesting' },
  completed: { icon: CheckCircle2, color: 'text-green-500', label: 'Ready' },
  failed: { icon: AlertCircle, color: 'text-destructive', label: 'Failed' },
};

function SourceCard({
  source,
  onIngest,
  onDelete,
  onDiscover,
  isIngesting,
}: {
  source: Source;
  onIngest: (id: string) => void;
  onDelete: (id: string) => void;
  onDiscover: (id: string) => void;
  isIngesting: boolean;
}) {
  const status = statusConfig[source.ingestion_status] || statusConfig.pending;
  const StatusIcon = status.icon;
  const isAnimated = source.ingestion_status === 'ingesting' || source.ingestion_status === 'downloading';

  return (
    <Card className="group border-border/50">
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 space-y-2">
            <div className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-primary" />
              <h4 className="font-serif font-semibold leading-snug">{source.title}</h4>
            </div>
            <p className="text-sm text-muted-foreground">
              {source.authors?.slice(0, 3).map((a) => a.name).join(', ')}
              {source.authors?.length > 3 && ` +${source.authors.length - 3} more`}
            </p>
            <div className="flex flex-wrap items-center gap-2 text-xs">
              {source.year && <Badge variant="secondary">{source.year}</Badge>}
              {source.venue && (
                <span className="max-w-[200px] truncate text-muted-foreground">
                  {source.venue}
                </span>
              )}
              <div className={`flex items-center gap-1 ${status.color}`}>
                <StatusIcon className={`h-3.5 w-3.5 ${isAnimated ? 'animate-spin' : ''}`} />
                <span>{status.label}</span>
              </div>
            </div>
          </div>
          <div className="flex flex-col gap-2">
            {source.ingestion_status === 'pending' && (
              <Button
                size="sm"
                onClick={() => onIngest(source.id)}
                disabled={isIngesting}
              >
                {isIngesting ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  'Ingest'
                )}
              </Button>
            )}
            {source.ingestion_status === 'completed' && (
              <Button
                size="sm"
                variant="outline"
                onClick={() => onDiscover(source.id)}
              >
                <Network className="h-4 w-4" />
              </Button>
            )}
            <Button
              size="sm"
              variant="ghost"
              className="text-destructive opacity-0 transition-opacity group-hover:opacity-100"
              onClick={() => onDelete(source.id)}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default function SourcesPage() {
  const params = useParams();
  const projectId = params.id as string;
  const queryClient = useQueryClient();

  const token = useAuthStore((s) => s.token);
  const project = useProjectStore((s) => s.currentProject);
  const sources = useSourcesStore((s) => s.sources);

  const [searchQuery, setSearchQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<PaperSearchResult[]>([]);
  const [addingPaperId, setAddingPaperId] = useState<string | null>(null);
  const [ingestingSourceId, setIngestingSourceId] = useState<string | null>(null);
  const [discoverySourceId, setDiscoverySourceId] = useState<string | null>(null);

  const authToken = token || 'demo-token';

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    
    setIsSearching(true);
    try {
      const result = await api.searchPapers(authToken, searchQuery);
      setSearchResults(result.results);
    } catch (error) {
      toast.error('Search failed. Please try again.');
    } finally {
      setIsSearching(false);
    }
  };

  const addMutation = useMutation({
    mutationFn: (paperId: string) => {
      setAddingPaperId(paperId);
      return api.addSource(authToken, projectId, paperId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sources', projectId] });
      toast.success('Paper added to sources');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to add paper');
    },
    onSettled: () => {
      setAddingPaperId(null);
    },
  });

  const ingestMutation = useMutation({
    mutationFn: (sourceId: string) => {
      setIngestingSourceId(sourceId);
      return api.ingestSource(authToken, projectId, sourceId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sources', projectId] });
      toast.success('Ingestion started');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to start ingestion');
    },
    onSettled: () => {
      setIngestingSourceId(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (sourceId: string) =>
      api.deleteSource(authToken, projectId, sourceId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sources', projectId] });
      toast.success('Source deleted');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to delete source');
    },
  });

  const { data: discoveryData, isLoading: isDiscovering } = useQuery({
    queryKey: ['discovery', projectId, discoverySourceId],
    queryFn: () =>
      discoverySourceId
        ? api.discoverRelated(authToken, projectId, discoverySourceId)
        : null,
    enabled: !!discoverySourceId,
  });

  const ingestedCount = sources.filter((s) => s.ingestion_status === 'completed').length;

  return (
    <div className="page-transition p-6">
      <div className="mb-6">
        <h1 className="font-serif text-3xl font-bold">{project?.title}</h1>
        <p className="mt-1 text-muted-foreground">
          Manage your research sources • {sources.length} papers ({ingestedCount} ingested)
        </p>
      </div>

      <Tabs defaultValue="library" className="space-y-6">
        <TabsList>
          <TabsTrigger value="library">Library ({sources.length})</TabsTrigger>
          <TabsTrigger value="search">Search Papers</TabsTrigger>
        </TabsList>

        <TabsContent value="library" className="space-y-4">
          {sources.length > 0 ? (
            <div className="grid gap-4 md:grid-cols-2">
              {sources.map((source) => (
                <SourceCard
                  key={source.id}
                  source={source}
                  onIngest={(id) => ingestMutation.mutate(id)}
                  onDelete={(id) => deleteMutation.mutate(id)}
                  onDiscover={(id) => setDiscoverySourceId(id)}
                  isIngesting={ingestingSourceId === source.id}
                />
              ))}
            </div>
          ) : (
            <Card className="border-dashed">
              <CardContent className="py-12 text-center">
                <FileText className="mx-auto mb-4 h-12 w-12 text-muted-foreground/50" />
                <h3 className="mb-2 font-serif text-lg font-semibold">No sources yet</h3>
                <p className="text-sm text-muted-foreground">
                  Search for papers and add them to your library.
                </p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="search" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="font-serif">Search Academic Papers</CardTitle>
              <CardDescription>
                Search Semantic Scholar for relevant research papers.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex gap-2">
                <Input
                  placeholder="e.g., machine learning healthcare diagnosis"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                />
                <Button onClick={handleSearch} disabled={isSearching}>
                  {isSearching ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Search className="h-4 w-4" />
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>

          {searchResults.length > 0 && (
            <div className="space-y-4">
              <h3 className="font-serif text-lg font-semibold">
                Results ({searchResults.length})
              </h3>
              <ScrollArea className="h-[500px]">
                <div className="space-y-3 pr-4">
                  {searchResults.map((paper) => (
                    <SearchResultCard
                      key={paper.paper_id}
                      paper={paper}
                      onAdd={(id) => addMutation.mutate(id)}
                      isAdding={addingPaperId === paper.paper_id}
                    />
                  ))}
                </div>
              </ScrollArea>
            </div>
          )}
        </TabsContent>
      </Tabs>

      {/* Discovery Dialog */}
      <Dialog
        open={!!discoverySourceId}
        onOpenChange={(open) => !open && setDiscoverySourceId(null)}
      >
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="font-serif">Related Papers</DialogTitle>
            <DialogDescription>
              Explore references, citations, and similar papers.
            </DialogDescription>
          </DialogHeader>
          {isDiscovering ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
          ) : discoveryData ? (
            <Tabs defaultValue="references">
              <TabsList className="w-full">
                <TabsTrigger value="references" className="flex-1">
                  References ({discoveryData.references?.length || 0})
                </TabsTrigger>
                <TabsTrigger value="citations" className="flex-1">
                  Cited By ({discoveryData.citations?.length || 0})
                </TabsTrigger>
                <TabsTrigger value="related" className="flex-1">
                  Similar ({discoveryData.related?.length || 0})
                </TabsTrigger>
              </TabsList>
              <ScrollArea className="mt-4 h-[400px]">
                <TabsContent value="references" className="mt-0 space-y-2">
                  {discoveryData.references?.map((paper) => (
                    <SearchResultCard
                      key={paper.paper_id}
                      paper={paper}
                      onAdd={(id) => addMutation.mutate(id)}
                      isAdding={addingPaperId === paper.paper_id}
                    />
                  ))}
                </TabsContent>
                <TabsContent value="citations" className="mt-0 space-y-2">
                  {discoveryData.citations?.map((paper) => (
                    <SearchResultCard
                      key={paper.paper_id}
                      paper={paper}
                      onAdd={(id) => addMutation.mutate(id)}
                      isAdding={addingPaperId === paper.paper_id}
                    />
                  ))}
                </TabsContent>
                <TabsContent value="related" className="mt-0 space-y-2">
                  {discoveryData.related?.map((paper) => (
                    <SearchResultCard
                      key={paper.paper_id}
                      paper={paper}
                      onAdd={(id) => addMutation.mutate(id)}
                      isAdding={addingPaperId === paper.paper_id}
                    />
                  ))}
                </TabsContent>
              </ScrollArea>
            </Tabs>
          ) : null}
        </DialogContent>
      </Dialog>
    </div>
  );
}

