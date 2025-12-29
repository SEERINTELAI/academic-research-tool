'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { FileText, ExternalLink, Star, StarOff, Check, Clock } from 'lucide-react';
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
  isSelected,
  onClick,
}: {
  paper: PaperListItem;
  isSelected: boolean;
  onClick: () => void;
}) {
  const authorText = paper.authors.length > 0
    ? paper.authors.slice(0, 2).map((a) => a.name).join(', ')
    : 'Unknown';

  return (
    <button
      onClick={onClick}
      className={`w-full text-left px-4 py-3 border-b border-border/50 hover:bg-muted/50 transition-colors ${
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

          {/* Status indicators */}
          <div className="flex items-center gap-2 mt-2">
            {paper.is_ingested ? (
              <Badge variant="outline" className="text-[10px] gap-1">
                <Check className="h-3 w-3 text-green-500" />
                Ingested
              </Badge>
            ) : (
              <Badge variant="outline" className="text-[10px] gap-1">
                <Clock className="h-3 w-3 text-muted-foreground" />
                Pending
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
    </button>
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

  const { data: papers, isLoading, error } = useQuery({
    queryKey: ['research-papers', projectId],
    queryFn: () => api.getPapersList(token, projectId),
  });

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

  if (!papers || papers.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center p-6">
        <FileText className="h-12 w-12 text-muted-foreground/50 mb-4" />
        <h3 className="font-medium mb-2">No papers yet</h3>
        <p className="text-sm text-muted-foreground">
          Start by searching for papers in the chat.
          <br />
          Try: &quot;search for quantum cryptography&quot;
        </p>
      </div>
    );
  }

  return (
    <ScrollArea className="h-full">
      <div className="divide-y divide-border/50">
        {papers.map((paper) => (
          <PaperRow
            key={paper.node_id}
            paper={paper}
            isSelected={paper.node_id === selectedPaperId}
            onClick={() => onSelectPaper(paper)}
          />
        ))}
      </div>
    </ScrollArea>
  );
}

