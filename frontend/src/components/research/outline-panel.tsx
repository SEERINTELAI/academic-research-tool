'use client';

import { useQuery } from '@tanstack/react-query';
import { FileText, AlertCircle, CheckCircle2, ChevronRight } from 'lucide-react';
import { api, SectionWithClaims, ClaimWithSources } from '@/lib/api';
import { useAuthStore } from '@/lib/store';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Skeleton } from '@/components/ui/skeleton';

interface OutlinePanelProps {
  projectId: string;
  onSelectClaim?: (claim: ClaimWithSources, section: SectionWithClaims) => void;
  onPaperClick?: (index: number) => void;
}

function SourceBadgeButton({
  index,
  title,
  onClick,
}: {
  index: number;
  title: string;
  onClick: () => void;
}) {
  return (
    <button
      onClick={(e) => {
        e.stopPropagation();
        onClick();
      }}
      className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs bg-primary/10 text-primary hover:bg-primary/20 transition-colors"
      title={title}
    >
      #{index}
    </button>
  );
}

function ClaimRow({
  claim,
  onPaperClick,
  onClick,
}: {
  claim: ClaimWithSources;
  onPaperClick?: (index: number) => void;
  onClick?: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="w-full text-left px-3 py-2 hover:bg-muted/50 rounded-lg transition-colors"
    >
      <div className="flex items-start gap-2">
        <ChevronRight className="h-4 w-4 mt-0.5 text-muted-foreground shrink-0" />
        <div className="flex-1 min-w-0">
          <p className="text-sm">{claim.claim_text}</p>
          <div className="flex items-center gap-2 mt-1.5 flex-wrap">
            {claim.sources.length > 0 ? (
              claim.sources.map((source) => (
                <SourceBadgeButton
                  key={source.index}
                  index={source.index}
                  title={source.title}
                  onClick={() => onPaperClick?.(source.index)}
                />
              ))
            ) : (
              <Badge variant="destructive" className="text-[10px] gap-1">
                <AlertCircle className="h-3 w-3" />
                needs sources
              </Badge>
            )}
            {claim.evidence_strength === 'strong' && (
              <Badge variant="outline" className="text-[10px] text-green-600">
                <CheckCircle2 className="h-3 w-3 mr-1" />
                strong
              </Badge>
            )}
          </div>
        </div>
      </div>
    </button>
  );
}

function SectionCard({
  section,
  onSelectClaim,
  onPaperClick,
}: {
  section: SectionWithClaims;
  onSelectClaim?: (claim: ClaimWithSources, section: SectionWithClaims) => void;
  onPaperClick?: (index: number) => void;
}) {
  return (
    <Card className="border-border/50">
      <CardHeader className="py-3 px-4">
        <CardTitle className="flex items-center justify-between text-base">
          <span>
            {section.order_index + 1}. {section.title}
          </span>
          <div className="flex items-center gap-2">
            {section.claims_needing_sources > 0 && (
              <Badge variant="destructive" className="text-[10px]">
                {section.claims_needing_sources} need sources
              </Badge>
            )}
            <Badge variant="secondary" className="text-[10px]">
              {section.total_claims} claims
            </Badge>
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent className="pt-0 pb-2 px-2">
        <div className="space-y-1">
          {section.claims.map((claim) => (
            <ClaimRow
              key={claim.id}
              claim={claim}
              onPaperClick={onPaperClick}
              onClick={() => onSelectClaim?.(claim, section)}
            />
          ))}
          {section.claims.length === 0 && (
            <p className="text-sm text-muted-foreground px-3 py-2">
              No claims yet. Ask the AI to add claims to this section.
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function LoadingSkeleton() {
  return (
    <div className="space-y-4 p-4">
      {[1, 2, 3].map((i) => (
        <div key={i} className="space-y-2">
          <Skeleton className="h-6 w-1/3" />
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </div>
      ))}
    </div>
  );
}

export function OutlinePanel({ projectId, onSelectClaim, onPaperClick }: OutlinePanelProps) {
  const token = useAuthStore((s) => s.token) || 'demo-token';

  const { data: outline, isLoading, error } = useQuery({
    queryKey: ['research-outline', projectId],
    queryFn: () => api.getOutlineWithSources(token, projectId),
  });

  if (isLoading) {
    return <LoadingSkeleton />;
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center p-6">
        <FileText className="h-12 w-12 text-muted-foreground/50 mb-4" />
        <h3 className="font-medium mb-2">Error loading outline</h3>
        <p className="text-sm text-muted-foreground">
          {error instanceof Error ? error.message : 'Something went wrong'}
        </p>
      </div>
    );
  }

  if (!outline || outline.sections.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center p-6">
        <FileText className="h-12 w-12 text-muted-foreground/50 mb-4" />
        <h3 className="font-medium mb-2">No outline yet</h3>
        <p className="text-sm text-muted-foreground">
          Ask the AI to generate an outline from your research.
          <br />
          Try: &quot;generate an outline from what we&apos;ve found&quot;
        </p>
      </div>
    );
  }

  return (
    <ScrollArea className="h-full">
      <div className="p-4 space-y-4">
        {/* Summary stats */}
        <div className="flex items-center gap-4 text-xs text-muted-foreground pb-2 border-b">
          <span>{outline.total_sections} sections</span>
          <span>•</span>
          <span>{outline.total_claims} claims</span>
          {outline.claims_needing_sources > 0 && (
            <>
              <span>•</span>
              <span className="text-destructive">
                {outline.claims_needing_sources} need sources
              </span>
            </>
          )}
        </div>

        {/* Sections */}
        {outline.sections.map((section) => (
          <SectionCard
            key={section.id}
            section={section}
            onSelectClaim={onSelectClaim}
            onPaperClick={onPaperClick}
          />
        ))}
      </div>
    </ScrollArea>
  );
}

