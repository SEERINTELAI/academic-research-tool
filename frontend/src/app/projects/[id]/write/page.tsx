'use client';

import { useState, useCallback, useRef } from 'react';
import { useParams } from 'next/navigation';
import dynamic from 'next/dynamic';
import { useMutation } from '@tanstack/react-query';
import {
  Save,
  Sparkles,
  Library,
  MessageSquare,
  BookmarkPlus,
  Loader2,
  ChevronRight,
  FileText,
  X,
  Wand2,
} from 'lucide-react';
import { toast } from 'sonner';
import { api, QueryResponse, Source } from '@/lib/api';
import { useAuthStore, useProjectStore, useSourcesStore, useEditorStore, useUIStore } from '@/lib/store';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet';

// Dynamically import Monaco to avoid SSR issues
const Editor = dynamic(() => import('@monaco-editor/react'), {
  ssr: false,
  loading: () => (
    <div className="flex h-full items-center justify-center">
      <Loader2 className="h-8 w-8 animate-spin text-primary" />
    </div>
  ),
});

function AIAssistPanel({
  isOpen,
  onClose,
  onInsert,
  projectId,
}: {
  isOpen: boolean;
  onClose: () => void;
  onInsert: (text: string) => void;
  projectId: string;
}) {
  const token = useAuthStore((s) => s.token);
  const [prompt, setPrompt] = useState('');
  const [response, setResponse] = useState<QueryResponse | null>(null);

  const authToken = token || 'demo-token';

  const queryMutation = useMutation({
    mutationFn: (query: string) =>
      api.query(authToken, projectId, { query, mode: 'hybrid' }),
    onSuccess: (data) => {
      setResponse(data);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Query failed');
    },
  });

  const handleSubmit = () => {
    if (!prompt.trim()) return;
    queryMutation.mutate(prompt);
  };

  const handleInsert = () => {
    if (response?.answer) {
      onInsert(response.answer);
      setResponse(null);
      setPrompt('');
      onClose();
      toast.success('Text inserted');
    }
  };

  return (
    <Sheet open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <SheetContent className="flex w-[400px] flex-col sm:w-[540px]">
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2 font-serif">
            <Sparkles className="h-5 w-5 text-primary" />
            AI Writing Assist
          </SheetTitle>
        </SheetHeader>
        
        <div className="flex flex-1 flex-col gap-4 overflow-hidden pt-4">
          <div className="space-y-2">
            <Textarea
              placeholder="Describe what you want to write about..."
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              rows={3}
            />
            <Button
              onClick={handleSubmit}
              disabled={queryMutation.isPending || !prompt.trim()}
              className="w-full"
            >
              {queryMutation.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Wand2 className="mr-2 h-4 w-4" />
              )}
              Generate
            </Button>
          </div>

          {response && (
            <div className="flex-1 space-y-4 overflow-hidden">
              <Separator />
              <ScrollArea className="h-[calc(100%-80px)]">
                <div className="space-y-4 pr-4">
                  <div className="rounded-lg bg-muted/50 p-4">
                    <p className="whitespace-pre-wrap text-sm">{response.answer}</p>
                  </div>
                  
                  {response.sources && response.sources.length > 0 && (
                    <div className="space-y-2">
                      <p className="text-xs font-medium text-muted-foreground">
                        Sources ({response.sources.length})
                      </p>
                      {response.sources.map((source, i) => (
                        <div
                          key={source.chunk_id}
                          className="rounded border border-border/50 bg-background p-2 text-xs"
                        >
                          <div className="flex items-center gap-2">
                            <Badge variant="secondary" className="h-5 w-5 justify-center p-0">
                              {i + 1}
                            </Badge>
                            <span className="font-medium">
                              {source.document_name || `Source ${i + 1}`}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </ScrollArea>
              
              <div className="flex gap-2">
                <Button variant="outline" onClick={() => setResponse(null)} className="flex-1">
                  Regenerate
                </Button>
                <Button onClick={handleInsert} className="flex-1">
                  <BookmarkPlus className="mr-2 h-4 w-4" />
                  Insert
                </Button>
              </div>
            </div>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}

function SourcesPanel({
  sources,
  onInsertCitation,
}: {
  sources: Source[];
  onInsertCitation: (source: Source) => void;
}) {
  const ingestedSources = sources.filter((s) => s.ingestion_status === 'ready');

  return (
    <Card className="h-full">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 font-serif text-base">
          <Library className="h-4 w-4" />
          Sources
        </CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <ScrollArea className="h-[calc(100vh-14rem)]">
          <div className="space-y-2 px-4 pb-4">
            {ingestedSources.length === 0 ? (
              <p className="py-8 text-center text-sm text-muted-foreground">
                No ingested sources yet.
              </p>
            ) : (
              ingestedSources.map((source) => (
                <div
                  key={source.id}
                  className="group cursor-pointer rounded-lg border border-border/50 bg-muted/30 p-3 transition-colors hover:border-primary/30"
                  onClick={() => onInsertCitation(source)}
                >
                  <p className="line-clamp-2 text-sm font-medium">{source.title}</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {source.authors?.slice(0, 2).map((a) => a.name).join(', ')}
                    {source.year && ` (${source.year})`}
                  </p>
                  <div className="mt-2 flex items-center gap-1 text-xs text-primary opacity-0 transition-opacity group-hover:opacity-100">
                    <BookmarkPlus className="h-3 w-3" />
                    Click to cite
                  </div>
                </div>
              ))
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}

export default function WritePage() {
  const params = useParams();
  const projectId = params.id as string;

  const project = useProjectStore((s) => s.currentProject);
  const sources = useSourcesStore((s) => s.sources);
  const { content, setContent, isDirty, markSaved } = useEditorStore();
  const { rightPanelOpen, rightPanelContent, setRightPanel } = useUIStore();

  const [isAIOpen, setIsAIOpen] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const editorRef = useRef<any>(null);

  const handleEditorMount = (editor: any) => {
    editorRef.current = editor;
  };

  const handleEditorChange = (value: string | undefined) => {
    setContent(value || '');
  };

  const handleSave = useCallback(async () => {
    setIsSaving(true);
    // TODO: Implement actual save to backend
    await new Promise((resolve) => setTimeout(resolve, 500));
    markSaved();
    setIsSaving(false);
    toast.success('Document saved');
  }, [markSaved]);

  const insertText = useCallback((text: string) => {
    if (editorRef.current) {
      const selection = editorRef.current.getSelection();
      const model = editorRef.current.getModel();
      if (model && selection) {
        const op = { range: selection, text, forceMoveMarkers: true };
        model.pushEditOperations([], [op], () => null);
      }
    }
  }, []);

  const handleInsertCitation = useCallback((source: Source) => {
    const authorName = source.authors?.[0]?.name?.split(' ').pop() || 'Author';
    const year = source.year || 'n.d.';
    const citation = `(${authorName}, ${year})`;
    insertText(citation);
    toast.success('Citation inserted');
  }, [insertText]);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 's') {
        e.preventDefault();
        handleSave();
      }
    },
    [handleSave]
  );

  return (
    <div className="page-transition flex h-[calc(100vh-2rem)] flex-col">
      {/* Toolbar */}
      <div className="flex items-center justify-between border-b border-border px-4 py-2">
        <div className="flex items-center gap-2">
          <FileText className="h-5 w-5 text-primary" />
          <h1 className="font-serif text-lg font-semibold">{project?.title}</h1>
          {isDirty && (
            <Badge variant="secondary" className="text-xs">
              Unsaved
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            className="gap-2"
            onClick={() => setRightPanel(rightPanelContent === 'sources' ? null : 'sources')}
          >
            <Library className="h-4 w-4" />
            Sources
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="gap-2"
            onClick={() => setIsAIOpen(true)}
          >
            <Sparkles className="h-4 w-4" />
            AI Assist
          </Button>
          <Separator orientation="vertical" className="h-6" />
          <Button
            size="sm"
            onClick={handleSave}
            disabled={isSaving || !isDirty}
            className="gap-2"
          >
            {isSaving ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Save className="h-4 w-4" />
            )}
            Save
          </Button>
        </div>
      </div>

      {/* Editor Area */}
      <div className="flex flex-1 overflow-hidden">
        {/* Main Editor */}
        <div className="flex-1">
          <Editor
            height="100%"
            defaultLanguage="markdown"
            value={content}
            onChange={handleEditorChange}
            onMount={handleEditorMount}
            theme="vs-light"
            options={{
              minimap: { enabled: false },
              fontSize: 15,
              lineHeight: 1.8,
              wordWrap: 'on',
              padding: { top: 24, bottom: 24 },
              lineNumbers: 'off',
              folding: false,
              renderLineHighlight: 'none',
              scrollBeyondLastLine: false,
              overviewRulerBorder: false,
              hideCursorInOverviewRuler: true,
              fontFamily: "'Crimson Pro', Georgia, serif",
              fontLigatures: true,
              cursorBlinking: 'smooth',
              cursorSmoothCaretAnimation: 'on',
              smoothScrolling: true,
            }}
          />
        </div>

        {/* Right Panel */}
        {rightPanelOpen && rightPanelContent === 'sources' && (
          <div className="w-80 shrink-0 border-l border-border">
            <SourcesPanel sources={sources} onInsertCitation={handleInsertCitation} />
          </div>
        )}
      </div>

      {/* AI Assist Sheet */}
      <AIAssistPanel
        isOpen={isAIOpen}
        onClose={() => setIsAIOpen(false)}
        onInsert={insertText}
        projectId={projectId}
      />
    </div>
  );
}

