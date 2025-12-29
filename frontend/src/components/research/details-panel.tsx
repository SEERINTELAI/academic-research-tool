'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  X,
  ExternalLink,
  FileText,
  Star,
  StarOff,
  Download,
  Hash,
  Calendar,
  Building,
  Quote,
  AlertCircle,
  CheckCircle2,
  Loader2,
} from 'lucide-react';
import { toast } from 'sonner';
import { api, PaperListItem, PaperDetails, ClaimWithSources, SectionWithClaims } from '@/lib/api';
import { useAuthStore } from '@/lib/store';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Skeleton } from '@/components/ui/skeleton';
import { Separator } from '@/components/ui/separator';

type SelectedItem =
  | { type: 'paper'; paper: PaperListItem }
  | { type: 'claim'; claim: ClaimWithSources; section: SectionWithClaims };

interface DetailsPanelProps {
  projectId: string;
  selectedItem: SelectedItem | null;
  onClose: () => void;
  onChatInsert?: (text: string) => void;
}

function PaperDetailsView({
  paper,
  projectId,
  onChatInsert,
}: {
  paper: PaperListItem;
  projectId: string;
  onChatInsert?: (text: string) => void;
}) {
  const token = useAuthStore((s) => s.token) || 'demo-token';
  const queryClient = useQueryClient();

  const { data: details, isLoading } = useQuery({
    queryKey: ['paper-details', projectId, paper.index],
    queryFn: () => api.getPaperDetails(token, projectId, paper.index),
    enabled: !!paper,
  });

  const ingestMutation = useMutation({
    mutationFn: () => {
      if (!paper.source_id) {
        throw new Error('No source ID for this paper');
      }
      return api.ingestSource(token, projectId, paper.source_id);
    },
    onSuccess: () => {
      toast.success('Ingestion started! The paper will be processed shortly.');
      // Refresh the papers list and details
      queryClient.invalidateQueries({ queryKey: ['research-papers', projectId] });
      queryClient.invalidateQueries({ queryKey: ['paper-details', projectId, paper.index] });
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to start ingestion');
    },
  });

  if (isLoading) {
    return (
      <div className="space-y-4 p-4">
        <Skeleton className="h-6 w-3/4" />
        <Skeleton className="h-4 w-1/2" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }

  const displayData = details || paper;

  return (
    <div className="space-y-4">
      {/* Header with index */}
      <div className="flex items-start gap-3">
        <Badge variant="default" className="shrink-0 font-mono text-lg px-3 py-1">
          #{paper.index}
        </Badge>
        <div className="flex-1 min-w-0">
          <h3 className="font-serif font-semibold text-lg leading-tight">
            {displayData.title}
          </h3>
        </div>
      </div>

      {/* Quick actions */}
      <div className="flex flex-wrap gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => onChatInsert?.(`paper #${paper.index}`)}
        >
          <Hash className="h-3 w-3 mr-1" />
          Reference in chat
        </Button>
        {displayData.pdf_url && (
          <Button variant="outline" size="sm" asChild>
            <a href={displayData.pdf_url} target="_blank" rel="noopener noreferrer">
              <ExternalLink className="h-3 w-3 mr-1" />
              View PDF
            </a>
          </Button>
        )}
        {/* Ingest button for papers that aren't ingested yet */}
        {!displayData.is_ingested && paper.source_id && (
          <Button
            variant="default"
            size="sm"
            onClick={() => ingestMutation.mutate()}
            disabled={ingestMutation.isPending}
          >
            {ingestMutation.isPending ? (
              <Loader2 className="h-3 w-3 mr-1 animate-spin" />
            ) : (
              <Download className="h-3 w-3 mr-1" />
            )}
            Ingest Paper
          </Button>
        )}
      </div>

      <Separator />

      {/* Metadata */}
      <div className="grid grid-cols-2 gap-3 text-sm">
        {displayData.year && (
          <div className="flex items-center gap-2">
            <Calendar className="h-4 w-4 text-muted-foreground" />
            <span>{displayData.year}</span>
          </div>
        )}
        {details?.venue && (
          <div className="flex items-center gap-2">
            <Building className="h-4 w-4 text-muted-foreground" />
            <span className="truncate">{details.venue}</span>
          </div>
        )}
        {displayData.citation_count != null && (
          <div className="flex items-center gap-2">
            <Quote className="h-4 w-4 text-muted-foreground" />
            <span>{displayData.citation_count} citations</span>
          </div>
        )}
        <div className="flex items-center gap-2">
          {displayData.is_ingested ? (
            <>
              <CheckCircle2 className="h-4 w-4 text-green-500" />
              <span className="text-green-600">Ingested</span>
            </>
          ) : (
            <>
              <AlertCircle className="h-4 w-4 text-muted-foreground" />
              <span className="text-muted-foreground">Not ingested</span>
            </>
          )}
        </div>
      </div>

      {/* Authors */}
      <div>
        <h4 className="text-xs font-medium text-muted-foreground mb-2">Authors</h4>
        <div className="flex flex-wrap gap-1">
          {displayData.authors.map((author, i) => (
            <Badge key={i} variant="secondary" className="text-xs">
              {author.name}
            </Badge>
          ))}
        </div>
      </div>

      {/* Abstract */}
      {details?.abstract && (
        <div>
          <h4 className="text-xs font-medium text-muted-foreground mb-2">Abstract</h4>
          <p className="text-sm text-muted-foreground leading-relaxed">
            {details.abstract}
          </p>
        </div>
      )}

      {/* Summary (from knowledge node) */}
      {paper.summary && !details?.abstract && (
        <div>
          <h4 className="text-xs font-medium text-muted-foreground mb-2">Summary</h4>
          <p className="text-sm text-muted-foreground leading-relaxed">
            {paper.summary}
          </p>
        </div>
      )}

      {/* DOI */}
      {details?.doi && (
        <div>
          <h4 className="text-xs font-medium text-muted-foreground mb-2">DOI</h4>
          <a
            href={`https://doi.org/${details.doi}`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-primary hover:underline"
          >
            {details.doi}
          </a>
        </div>
      )}
    </div>
  );
}

function ClaimDetailsView({
  claim,
  section,
  onChatInsert,
}: {
  claim: ClaimWithSources;
  section: SectionWithClaims;
  onChatInsert?: (text: string) => void;
}) {
  return (
    <div className="space-y-4">
      {/* Header */}
      <div>
        <Badge variant="outline" className="mb-2">
          Section: {section.title}
        </Badge>
        <h3 className="font-serif font-semibold">
          {claim.claim_text}
        </h3>
      </div>

      {/* Status */}
      <div className="flex items-center gap-2">
        <Badge
          variant={claim.needs_sources ? 'destructive' : 'secondary'}
          className="text-xs"
        >
          {claim.needs_sources ? 'Needs sources' : `${claim.sources.length} sources`}
        </Badge>
        <Badge variant="outline" className="text-xs">
          {claim.evidence_strength} evidence
        </Badge>
        <Badge variant="outline" className="text-xs">
          {claim.status}
        </Badge>
      </div>

      {/* Quick actions */}
      <div className="flex flex-wrap gap-2">
        {claim.needs_sources && (
          <Button
            variant="outline"
            size="sm"
            onClick={() =>
              onChatInsert?.(`find papers that support the claim "${claim.claim_text.slice(0, 50)}..."`)
            }
          >
            Find sources
          </Button>
        )}
        <Button
          variant="outline"
          size="sm"
          onClick={() =>
            onChatInsert?.(`expand on the claim "${claim.claim_text.slice(0, 50)}..."`)
          }
        >
          Expand
        </Button>
      </div>

      <Separator />

      {/* Supporting sources */}
      <div>
        <h4 className="text-xs font-medium text-muted-foreground mb-2">
          Supporting Sources
        </h4>
        {claim.sources.length > 0 ? (
          <div className="space-y-2">
            {claim.sources.map((source) => (
              <div
                key={source.index}
                className="flex items-start gap-2 p-2 rounded-lg bg-muted/50"
              >
                <Badge variant="default" className="shrink-0 font-mono">
                  #{source.index}
                </Badge>
                <p className="text-sm line-clamp-2">{source.title}</p>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground italic">
            No sources linked yet. Ask the AI to find supporting papers.
          </p>
        )}
      </div>

      {/* User critique */}
      {claim.user_critique && (
        <div>
          <h4 className="text-xs font-medium text-muted-foreground mb-2">
            Your Feedback
          </h4>
          <p className="text-sm text-muted-foreground">
            {claim.user_critique}
          </p>
        </div>
      )}
    </div>
  );
}

export function DetailsPanel({
  projectId,
  selectedItem,
  onClose,
  onChatInsert,
}: DetailsPanelProps) {
  if (!selectedItem) {
    return null;
  }

  return (
    <div className="border-t bg-background">
      <div className="flex items-center justify-between px-4 py-2 border-b">
        <h4 className="text-sm font-medium">
          {selectedItem.type === 'paper' ? 'Paper Details' : 'Claim Details'}
        </h4>
        <Button variant="ghost" size="icon" className="h-7 w-7" onClick={onClose}>
          <X className="h-4 w-4" />
        </Button>
      </div>
      <ScrollArea className="h-[250px]">
        <div className="p-4">
          {selectedItem.type === 'paper' ? (
            <PaperDetailsView
              paper={selectedItem.paper}
              projectId={projectId}
              onChatInsert={onChatInsert}
            />
          ) : (
            <ClaimDetailsView
              claim={selectedItem.claim}
              section={selectedItem.section}
              onChatInsert={onChatInsert}
            />
          )}
        </div>
      </ScrollArea>
    </div>
  );
}

