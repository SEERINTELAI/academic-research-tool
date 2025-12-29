'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  ChevronDown,
  ChevronRight,
  FileText,
  Library,
  Calendar,
  Building,
  Hash,
} from 'lucide-react';
import { api, LibraryResponse, TopicGroup, LibraryPaper } from '@/lib/api';
import { useAuthStore } from '@/lib/store';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';

interface LibraryPanelProps {
  projectId: string;
  onSelectPaper: (paper: LibraryPaper) => void;
  selectedPaperId?: string;
}

function TopicSection({
  group,
  onSelectPaper,
  selectedPaperId,
}: {
  group: TopicGroup;
  onSelectPaper: (paper: LibraryPaper) => void;
  selectedPaperId?: string;
}) {
  const [isOpen, setIsOpen] = useState(true);

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen}>
      <CollapsibleTrigger asChild>
        <Button
          variant="ghost"
          className="w-full justify-start gap-2 h-10 px-3 hover:bg-muted/50"
        >
          {isOpen ? (
            <ChevronDown className="h-4 w-4 shrink-0" />
          ) : (
            <ChevronRight className="h-4 w-4 shrink-0" />
          )}
          <span className="font-medium truncate flex-1 text-left">
            {group.topic}
          </span>
          <Badge variant="secondary" className="shrink-0">
            {group.paper_count}
          </Badge>
        </Button>
      </CollapsibleTrigger>
      <CollapsibleContent>
        <div className="pl-6 space-y-1">
          {group.papers.map((paper) => (
            <PaperRow
              key={paper.id}
              paper={paper}
              isSelected={paper.id === selectedPaperId}
              onClick={() => onSelectPaper(paper)}
            />
          ))}
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}

function PaperRow({
  paper,
  isSelected,
  onClick,
}: {
  paper: LibraryPaper;
  isSelected: boolean;
  onClick: () => void;
}) {
  const authorText =
    paper.authors.length > 0
      ? paper.authors
          .slice(0, 2)
          .map((a) => a.name.split(' ').pop()) // Last name only
          .join(', ')
      : 'Unknown';

  return (
    <button
      onClick={onClick}
      className={`w-full text-left px-3 py-2 rounded-md hover:bg-muted/50 transition-colors flex items-start gap-2 ${
        isSelected ? 'bg-primary/10 ring-1 ring-primary/30' : ''
      }`}
    >
      <FileText className="h-4 w-4 shrink-0 mt-0.5 text-muted-foreground" />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium line-clamp-1">{paper.title}</p>
        <div className="flex items-center gap-2 text-xs text-muted-foreground mt-0.5">
          <span className="truncate">{authorText}</span>
          {paper.year && (
            <>
              <span>•</span>
              <span>{paper.year}</span>
            </>
          )}
        </div>
      </div>
    </button>
  );
}

function LoadingSkeleton() {
  return (
    <div className="space-y-4 p-4">
      {[1, 2, 3].map((i) => (
        <div key={i} className="space-y-2">
          <div className="flex items-center gap-2">
            <Skeleton className="h-4 w-4" />
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-5 w-8" />
          </div>
          <div className="pl-6 space-y-2">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </div>
        </div>
      ))}
    </div>
  );
}

export function LibraryPanel({
  projectId,
  onSelectPaper,
  selectedPaperId,
}: LibraryPanelProps) {
  const token = useAuthStore((s) => s.token) || 'demo-token';

  const { data: library, isLoading, error } = useQuery({
    queryKey: ['library', projectId],
    queryFn: () => api.getLibrary(token, projectId),
  });

  if (isLoading) {
    return <LoadingSkeleton />;
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center p-6">
        <Library className="h-12 w-12 text-muted-foreground/50 mb-4" />
        <h3 className="font-medium mb-2">Error loading library</h3>
        <p className="text-sm text-muted-foreground">
          {error instanceof Error ? error.message : 'Something went wrong'}
        </p>
      </div>
    );
  }

  if (!library || library.total_papers === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center p-6">
        <Library className="h-12 w-12 text-muted-foreground/50 mb-4" />
        <h3 className="font-medium mb-2">No papers in library</h3>
        <p className="text-sm text-muted-foreground">
          Ingest papers from the Explore tab to add them here.
          <br />
          Ingested papers will be grouped by topic.
        </p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header stats */}
      <div className="shrink-0 px-4 py-3 border-b bg-muted/30">
        <div className="flex items-center gap-4 text-sm">
          <div className="flex items-center gap-1.5">
            <FileText className="h-4 w-4 text-muted-foreground" />
            <span className="font-medium">{library.total_papers}</span>
            <span className="text-muted-foreground">papers</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Hash className="h-4 w-4 text-muted-foreground" />
            <span className="font-medium">{library.total_topics}</span>
            <span className="text-muted-foreground">topics</span>
          </div>
        </div>
      </div>

      {/* Topic groups */}
      <ScrollArea className="flex-1">
        <div className="p-2 space-y-1">
          {library.topics.map((group) => (
            <TopicSection
              key={group.topic}
              group={group}
              onSelectPaper={onSelectPaper}
              selectedPaperId={selectedPaperId}
            />
          ))}
        </div>
      </ScrollArea>
    </div>
  );
}

