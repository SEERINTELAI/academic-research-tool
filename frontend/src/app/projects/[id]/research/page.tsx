'use client';

import { useState, useRef, useEffect } from 'react';
import { useParams } from 'next/navigation';
import { useMutation } from '@tanstack/react-query';
import {
  Send,
  Loader2,
  MessageSquare,
  Sparkles,
  FileText,
  ChevronDown,
  ChevronUp,
  Copy,
  Check,
} from 'lucide-react';
import { toast } from 'sonner';
import { api, QueryResponse } from '@/lib/api';
import { useAuthStore, useProjectStore, useSourcesStore } from '@/lib/store';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: QueryResponse['sources'];
  timestamp: Date;
}

const queryModes = [
  { value: 'hybrid', label: 'Hybrid', description: 'Best of both local and global' },
  { value: 'local', label: 'Local', description: 'Focus on specific entities' },
  { value: 'global', label: 'Global', description: 'Broad thematic analysis' },
  { value: 'naive', label: 'Simple', description: 'Direct keyword matching' },
] as const;

function SourceReference({
  source,
  index,
}: {
  source: QueryResponse['sources'][number];
  index: number;
}) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="rounded-lg border border-border/50 bg-muted/30 p-3">
      <button
        className="flex w-full items-start justify-between text-left"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-start gap-2">
          <Badge variant="secondary" className="mt-0.5">
            {index + 1}
          </Badge>
          <div>
            <p className="text-sm font-medium">
              {source.document_name || `Source ${index + 1}`}
            </p>
            <p className="text-xs text-muted-foreground">
              Relevance: {Math.round(source.relevance_score * 100)}%
            </p>
          </div>
        </div>
        {isExpanded ? (
          <ChevronUp className="h-4 w-4 text-muted-foreground" />
        ) : (
          <ChevronDown className="h-4 w-4 text-muted-foreground" />
        )}
      </button>
      {isExpanded && (
        <div className="mt-3 border-t border-border/50 pt-3">
          <p className="text-sm text-muted-foreground">{source.content}</p>
        </div>
      )}
    </div>
  );
}

function MessageBubble({ message }: { message: Message }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (message.role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] rounded-2xl rounded-br-md bg-primary px-4 py-3 text-primary-foreground">
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-start gap-3">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10">
          <Sparkles className="h-4 w-4 text-primary" />
        </div>
        <div className="flex-1 space-y-3">
          <div className="rounded-2xl rounded-tl-md bg-muted/50 px-4 py-3">
            <div className="prose prose-sm dark:prose-invert max-w-none">
              <p className="whitespace-pre-wrap">{message.content}</p>
            </div>
          </div>
          
          {message.sources && message.sources.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs font-medium text-muted-foreground">
                Sources ({message.sources.length})
              </p>
              <div className="space-y-2">
                {message.sources.map((source, i) => (
                  <SourceReference key={source.chunk_id} source={source} index={i} />
                ))}
              </div>
            </div>
          )}
          
          <Button
            variant="ghost"
            size="sm"
            className="h-7 gap-1.5 text-xs text-muted-foreground"
            onClick={handleCopy}
          >
            {copied ? (
              <>
                <Check className="h-3 w-3" />
                Copied
              </>
            ) : (
              <>
                <Copy className="h-3 w-3" />
                Copy
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}

export default function ResearchPage() {
  const params = useParams();
  const projectId = params.id as string;

  const token = useAuthStore((s) => s.token);
  const project = useProjectStore((s) => s.currentProject);
  const sources = useSourcesStore((s) => s.sources);

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [queryMode, setQueryMode] = useState<'hybrid' | 'local' | 'global' | 'naive'>('hybrid');
  
  const scrollRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const authToken = token || 'demo-token';

  const ingestedSources = sources.filter((s) => s.ingestion_status === 'ready');

  const queryMutation = useMutation({
    mutationFn: (query: string) =>
      api.query(authToken, projectId, { query, mode: queryMode }),
    onSuccess: (response) => {
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: response.answer,
          sources: response.sources,
          timestamp: new Date(),
        },
      ]);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Query failed. Please try again.');
    },
  });

  const handleSubmit = () => {
    const query = input.trim();
    if (!query) return;

    setMessages((prev) => [
      ...prev,
      {
        id: crypto.randomUUID(),
        role: 'user',
        content: query,
        timestamp: new Date(),
      },
    ]);
    setInput('');
    queryMutation.mutate(query);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  return (
    <div className="page-transition flex h-[calc(100vh-2rem)] flex-col p-6">
      <div className="mb-4">
        <h1 className="font-serif text-3xl font-bold">{project?.title}</h1>
        <p className="mt-1 text-muted-foreground">
          Ask questions about your research sources
        </p>
      </div>

      <div className="flex flex-1 gap-6 overflow-hidden">
        {/* Chat Area */}
        <Card className="flex flex-1 flex-col overflow-hidden">
          <CardContent className="flex flex-1 flex-col overflow-hidden p-0">
            {ingestedSources.length === 0 ? (
              <div className="flex flex-1 items-center justify-center p-6">
                <div className="text-center">
                  <FileText className="mx-auto mb-4 h-12 w-12 text-muted-foreground/50" />
                  <h3 className="mb-2 font-serif text-lg font-semibold">
                    No ingested sources
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    Ingest some papers first to start asking questions.
                  </p>
                </div>
              </div>
            ) : messages.length === 0 ? (
              <div className="flex flex-1 items-center justify-center p-6">
                <div className="text-center">
                  <MessageSquare className="mx-auto mb-4 h-12 w-12 text-muted-foreground/50" />
                  <h3 className="mb-2 font-serif text-lg font-semibold">
                    Start a conversation
                  </h3>
                  <p className="mb-4 text-sm text-muted-foreground">
                    Ask questions about your {ingestedSources.length} ingested papers.
                  </p>
                  <div className="flex flex-wrap justify-center gap-2">
                    {[
                      'Summarize the main findings',
                      'What methods were used?',
                      'Compare the approaches',
                    ].map((suggestion) => (
                      <Button
                        key={suggestion}
                        variant="outline"
                        size="sm"
                        onClick={() => setInput(suggestion)}
                      >
                        {suggestion}
                      </Button>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <ScrollArea ref={scrollRef} className="flex-1 p-4">
                <div className="space-y-6">
                  {messages.map((message) => (
                    <MessageBubble key={message.id} message={message} />
                  ))}
                  {queryMutation.isPending && (
                    <div className="flex items-center gap-3">
                      <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10">
                        <Loader2 className="h-4 w-4 animate-spin text-primary" />
                      </div>
                      <span className="text-sm text-muted-foreground">
                        Thinking...
                      </span>
                    </div>
                  )}
                </div>
              </ScrollArea>
            )}

            {/* Input */}
            <div className="border-t border-border p-4">
              <div className="flex items-end gap-2">
                <div className="relative flex-1">
                  <Textarea
                    ref={textareaRef}
                    placeholder="Ask about your research..."
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    disabled={queryMutation.isPending || ingestedSources.length === 0}
                    rows={1}
                    className="min-h-[44px] resize-none pr-24"
                  />
                  <div className="absolute bottom-2 right-2">
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="sm" className="h-7 text-xs">
                          {queryModes.find((m) => m.value === queryMode)?.label}
                          <ChevronDown className="ml-1 h-3 w-3" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        {queryModes.map((mode) => (
                          <DropdownMenuItem
                            key={mode.value}
                            onClick={() => setQueryMode(mode.value)}
                          >
                            <div>
                              <p className="font-medium">{mode.label}</p>
                              <p className="text-xs text-muted-foreground">
                                {mode.description}
                              </p>
                            </div>
                          </DropdownMenuItem>
                        ))}
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                </div>
                <Button
                  onClick={handleSubmit}
                  disabled={
                    queryMutation.isPending ||
                    !input.trim() ||
                    ingestedSources.length === 0
                  }
                >
                  {queryMutation.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Send className="h-4 w-4" />
                  )}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Sources Sidebar */}
        <Card className="hidden w-72 shrink-0 lg:block">
          <CardHeader className="pb-3">
            <CardTitle className="font-serif text-base">Available Sources</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <ScrollArea className="h-[calc(100vh-16rem)]">
              <div className="space-y-2 px-4 pb-4">
                {ingestedSources.map((source) => (
                  <div
                    key={source.id}
                    className="rounded-lg border border-border/50 bg-muted/30 p-3"
                  >
                    <p className="line-clamp-2 text-sm font-medium">{source.title}</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {source.authors?.slice(0, 2).map((a) => a.name).join(', ')}
                    </p>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

