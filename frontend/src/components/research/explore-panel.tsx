'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { FileText, Download, Search, Loader2, Star } from 'lucide-react';
import { toast } from 'sonner';
import { api, PaperListItem } from '@/lib/api';
import { useAuthStore } from '@/lib/store';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Skeleton } from '@/components/ui/skeleton';

interface ExplorePanelProps {
  projectId: string;
  onSelectPaper: (paper: PaperListItem) => void;
  selectedPaperId?: string;
}

function PaperRow({
  paper,
  projectId,
  isSelected,
  onClick,
  onIngested,
}: {
  paper: PaperListItem;
  projectId: string;
  isSelected: boolean;
  onClick: () => void;
  onIngested: () => void;
}) {
  const token = useAuthStore((s) => s.token) || 'demo-token';
  const queryClient = useQueryClient();

  const ingestMutation = useMutation({
    mutationFn: () => {
      if (!paper.source_id) {
        throw new Error('No source ID for this paper');
      }
      return api.ingestSource(token, projectId, paper.source_id);
    },
    onSuccess: () => {
      toast.success('Paper ingested! It will appear in your Library.');
      // Refresh both explore and library
      queryClient.invalidateQueries({ queryKey: ['research-papers', projectId] });
      queryClient.invalidateQueries({ queryKey: ['library', projectId] });
      onIngested();
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to ingest paper');
    },
  });

  const authorText = paper.authors.length > 0
    ? paper.authors.slice(0, 2).map((a) => a.name).join(', ')
    : 'Unknown';

  const handleIngest = (e: React.MouseEvent) => {
    e.stopPropagation();
    ingestMutation.mutate();
  };

  return (
    <div
      onClick={onClick}
      className={`w-full text-left px-4 py-3 border-b border-border/50 hover:bg-muted/50 transition-colors cursor-pointer ${
        isSelected ? 'bg-primary/5 border-l-2 border-l-primary' : ''
      }`}
    >
      <div className="flex items-start gap-3">
        {/* Index badge - prominent for referencing */}
        <Badge
          variant={isSelected ? 'default' : 'secondary'}
          className="shrink-0 font-mono text-sm min-w-[2.5rem] justify-center"
        >
          #{paper.index}
        </Badge>

        <div className="flex-1 min-w-0">
          {/* Title */}
          <h4 className="font-medium text-sm line-clamp-2 mb-1">
            {paper.title}
          </h4>

          {/* Authors and Year */}
          <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
            <span className="truncate">{authorText}</span>
            {paper.year && (
              <>
                <span>•</span>
                <span>{paper.year}</span>
              </>
            )}
          </div>

          {/* Summary */}
          {paper.summary && (
            <p className="text-xs text-muted-foreground/80 line-clamp-2">
              {paper.summary}
            </p>
          )}

          {/* Actions */}
          <div className="flex items-center gap-2 mt-2">
            {paper.pdf_url && paper.source_id && (
              <Button
                variant="default"
                size="sm"
                className="h-7 text-xs"
                onClick={handleIngest}
                disabled={ingestMutation.isPending}
              >
                {ingestMutation.isPending ? (
                  <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                ) : (
                  <Download className="h-3 w-3 mr-1" />
                )}
                Ingest
              </Button>
            )}
            {!paper.pdf_url && (
              <Badge variant="outline" className="text-[10px] text-muted-foreground">
                No PDF available
              </Badge>
            )}
            {paper.citation_count && paper.citation_count > 0 && (
              <Badge variant="outline" className="text-[10px]">
                {paper.citation_count} citations
              </Badge>
            )}
            {paper.user_rating === 'useful' && (
              <Star className="h-3 w-3 text-yellow-500 fill-yellow-500" />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="space-y-4 p-4">
      {[1, 2, 3, 4, 5].map((i) => (
        <div key={i} className="flex items-start gap-3">
          <Skeleton className="h-6 w-10 rounded" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-3 w-2/3" />
            <Skeleton className="h-3 w-1/2" />
          </div>
        </div>
      ))}
    </div>
  );
}

export function ExplorePanel({ projectId, onSelectPaper, selectedPaperId }: ExplorePanelProps) {
  const token = useAuthStore((s) => s.token) || 'demo-token';

  const { data: allPapers, isLoading, error } = useQuery({
    queryKey: ['research-papers', projectId],
    queryFn: () => api.getPapersList(token, projectId),
  });

  // Filter to only show non-ingested papers (candidates)
  const papers = allPapers?.filter((p) => !p.is_ingested) || [];

  if (isLoading) {
    return <LoadingSkeleton />;
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center p-6">
        <FileText className="h-12 w-12 text-muted-foreground/50 mb-4" />
        <h3 className="font-medium mb-2">Error loading papers</h3>
        <p className="text-sm text-muted-foreground">
          {error instanceof Error ? error.message : 'Something went wrong'}
        </p>
      </div>
    );
  }

  if (papers.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center p-6">
        <Search className="h-12 w-12 text-muted-foreground/50 mb-4" />
        <h3 className="font-medium mb-2">No papers to explore</h3>
        <p className="text-sm text-muted-foreground">
          Search for papers in the chat to find candidates.
          <br />
          Try: &quot;search for quantum cryptography&quot;
          <br />
          <span className="text-xs mt-2 block text-muted-foreground/70">
            Ingested papers appear in the Library tab.
          </span>
        </p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="shrink-0 px-4 py-2 border-b bg-muted/30">
        <p className="text-xs text-muted-foreground">
          <span className="font-medium">{papers.length}</span> papers to review •{' '}
          <span className="text-muted-foreground/70">Click Ingest to add to your Library</span>
        </p>
      </div>

      <ScrollArea className="flex-1">
        <div className="divide-y divide-border/50">
          {papers.map((paper) => (
            <PaperRow
              key={paper.node_id}
              paper={paper}
              projectId={projectId}
              isSelected={paper.node_id === selectedPaperId}
              onClick={() => onSelectPaper(paper)}
              onIngested={() => {}}
            />
          ))}
        </div>
      </ScrollArea>
    </div>
  );
}
