'use client';

import { useState, useRef, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Send,
  Loader2,
  Sparkles,
  Search,
  FileText,
  Network,
  Hash,
  Copy,
  Check,
  Download,
  DownloadOff,
} from 'lucide-react';
import { toast } from 'sonner';
import { api, ChatMessage, ChatResponse, PaperListItem } from '@/lib/api';
import { useAuthStore } from '@/lib/store';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';

interface ChatPanelProps {
  projectId: string;
  selectedPaper?: PaperListItem | null;
  onPaperMention?: (index: number) => void;
}

function ActionBadge({ action }: { action: string }) {
  const actionConfig: Record<string, { icon: React.ReactNode; label: string; color: string }> = {
    search: { icon: <Search className="h-3 w-3" />, label: 'Searched', color: 'bg-blue-500/10 text-blue-600' },
    deepen: { icon: <Network className="h-3 w-3" />, label: 'Deepened', color: 'bg-purple-500/10 text-purple-600' },
    generate_outline: { icon: <FileText className="h-3 w-3" />, label: 'Outline', color: 'bg-green-500/10 text-green-600' },
    find_gaps: { icon: <Search className="h-3 w-3" />, label: 'Gaps', color: 'bg-yellow-500/10 text-yellow-600' },
    help: { icon: <Sparkles className="h-3 w-3" />, label: 'Help', color: 'bg-gray-500/10 text-gray-600' },
  };

  const config = actionConfig[action] || { icon: null, label: action, color: 'bg-gray-500/10 text-gray-600' };

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium ${config.color}`}>
      {config.icon}
      {config.label}
    </span>
  );
}

interface DisplayMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  action?: string | null;
  papersAdded?: number[];
  timestamp: Date;
}

function MessageBubble({
  message,
  onPaperMention,
}: {
  message: DisplayMessage;
  onPaperMention?: (index: number) => void;
}) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Parse paper references in content (e.g., #5, paper 3)
  const renderContent = (text: string) => {
    const parts = text.split(/(#\d+|paper\s*\d+)/gi);
    return parts.map((part, i) => {
      const match = part.match(/#?(\d+)/);
      if (match && /^(#\d+|paper\s*\d+)$/i.test(part)) {
        const index = parseInt(match[1], 10);
        return (
          <button
            key={i}
            onClick={() => onPaperMention?.(index)}
            className="inline-flex items-center gap-0.5 px-1 py-0.5 mx-0.5 rounded bg-primary/10 text-primary hover:bg-primary/20 transition-colors font-medium"
          >
            <Hash className="h-3 w-3" />
            {index}
          </button>
        );
      }
      return part;
    });
  };

  if (message.role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-2xl rounded-br-md bg-primary px-4 py-2.5 text-primary-foreground">
          <p className="text-sm whitespace-pre-wrap">{message.content}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="flex items-start gap-2">
        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary/10">
          <Sparkles className="h-3.5 w-3.5 text-primary" />
        </div>
        <div className="flex-1 space-y-2">
          {/* Action badge */}
          {message.action && message.action !== 'help' && (
            <ActionBadge action={message.action} />
          )}

          {/* Message content */}
          <div className="rounded-2xl rounded-tl-md bg-muted/50 px-4 py-2.5">
            <div className="text-sm whitespace-pre-wrap">
              {renderContent(message.content)}
            </div>
          </div>

          {/* Papers added indicator */}
          {message.papersAdded && message.papersAdded.length > 0 && (
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <span>Added papers:</span>
              {message.papersAdded.map((idx) => (
                <button
                  key={idx}
                  onClick={() => onPaperMention?.(idx)}
                  className="px-1.5 py-0.5 rounded bg-green-500/10 text-green-600 hover:bg-green-500/20"
                >
                  #{idx}
                </button>
              ))}
            </div>
          )}

          {/* Copy button */}
          <Button
            variant="ghost"
            size="sm"
            className="h-6 gap-1 text-[10px] text-muted-foreground"
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

export function ChatPanel({ projectId, selectedPaper, onPaperMention }: ChatPanelProps) {
  const token = useAuthStore((s) => s.token) || 'demo-token';
  const queryClient = useQueryClient();

  const [input, setInput] = useState('');
  const [localMessages, setLocalMessages] = useState<DisplayMessage[]>([]);
  const [autoIngest, setAutoIngest] = useState(true);
  const scrollRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Fetch chat history
  const { data: history } = useQuery({
    queryKey: ['chat-history', projectId],
    queryFn: () => api.getChatHistory(token, projectId),
  });

  // Convert history to display messages
  useEffect(() => {
    if (history) {
      const messages: DisplayMessage[] = history.map((msg) => ({
        id: msg.id,
        role: msg.role as 'user' | 'assistant',
        content: msg.content,
        action: (msg.metadata as { action_taken?: string })?.action_taken,
        papersAdded: (msg.metadata as { papers_added?: number[] })?.papers_added,
        timestamp: new Date(msg.created_at),
      }));
      setLocalMessages(messages);
    }
  }, [history]);

  // Send message mutation
  const sendMutation = useMutation({
    mutationFn: (message: string) => api.sendChatMessage(token, projectId, message, autoIngest),
    onSuccess: (response: ChatResponse) => {
      // Add assistant response to local messages
      setLocalMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: response.message,
          action: response.action_taken,
          papersAdded: response.papers_added,
          timestamp: new Date(),
        },
      ]);

      // Invalidate related queries to refresh data
      queryClient.invalidateQueries({ queryKey: ['research-papers', projectId] });
      queryClient.invalidateQueries({ queryKey: ['research-outline', projectId] });
      queryClient.invalidateQueries({ queryKey: ['knowledge-tree', projectId] });
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to send message');
    },
  });

  const handleSubmit = () => {
    const message = input.trim();
    if (!message) return;

    // Add user message to local state immediately
    setLocalMessages((prev) => [
      ...prev,
      {
        id: crypto.randomUUID(),
        role: 'user',
        content: message,
        timestamp: new Date(),
      },
    ]);

    setInput('');
    sendMutation.mutate(message);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  // Insert paper reference when a paper is selected
  const insertPaperRef = () => {
    if (selectedPaper) {
      setInput((prev) => `${prev}paper #${selectedPaper.index} `.trim() + ' ');
      textareaRef.current?.focus();
    }
  };

  // Scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [localMessages]);

  const suggestions = [
    'Search for quantum cryptography',
    'Generate an outline',
    'Which claims need sources?',
  ];

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="shrink-0 px-4 py-3 border-b">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-serif font-semibold">Research Assistant</h3>
            <p className="text-xs text-muted-foreground">
              Chat to search, explore, and build your outline
            </p>
          </div>
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground">
                    {autoIngest ? (
                      <Download className="h-4 w-4 text-green-500" />
                    ) : (
                      <DownloadOff className="h-4 w-4 text-muted-foreground" />
                    )}
                  </span>
                  <Switch
                    checked={autoIngest}
                    onCheckedChange={setAutoIngest}
                    className="data-[state=checked]:bg-green-500"
                  />
                </div>
              </TooltipTrigger>
              <TooltipContent side="left">
                <p className="text-xs font-medium">
                  {autoIngest ? 'Auto-ingest ON' : 'Auto-ingest OFF'}
                </p>
                <p className="text-xs text-muted-foreground">
                  {autoIngest
                    ? 'Papers with PDFs will be automatically uploaded to RAG'
                    : 'Papers will not be auto-ingested (you can ingest manually)'}
                </p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
      </div>

      {/* Messages */}
      <ScrollArea ref={scrollRef} className="flex-1 p-4">
        {localMessages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center py-8">
            <Sparkles className="h-10 w-10 text-primary/30 mb-4" />
            <h4 className="font-medium mb-2">Start your research</h4>
            <p className="text-sm text-muted-foreground mb-4">
              Tell me what topic you&apos;d like to explore
            </p>
            <div className="flex flex-wrap justify-center gap-2">
              {suggestions.map((s) => (
                <Button
                  key={s}
                  variant="outline"
                  size="sm"
                  className="text-xs"
                  onClick={() => setInput(s)}
                >
                  {s}
                </Button>
              ))}
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {localMessages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} onPaperMention={onPaperMention} />
            ))}
            {sendMutation.isPending && (
              <div className="flex items-center gap-2">
                <div className="flex h-7 w-7 items-center justify-center rounded-full bg-primary/10">
                  <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
                </div>
                <span className="text-sm text-muted-foreground">Thinking...</span>
              </div>
            )}
          </div>
        )}
      </ScrollArea>

      {/* Selected paper quick-insert */}
      {selectedPaper && (
        <div className="shrink-0 px-4 py-2 border-t bg-muted/30">
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground truncate">
              Selected: #{selectedPaper.index} {selectedPaper.title}
            </span>
            <Button variant="ghost" size="sm" className="h-6 text-xs" onClick={insertPaperRef}>
              Insert ref
            </Button>
          </div>
        </div>
      )}

      {/* Input */}
      <div className="shrink-0 p-4 border-t">
        <div className="flex items-end gap-2">
          <Textarea
            ref={textareaRef}
            placeholder="Ask about your research..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={sendMutation.isPending}
            rows={1}
            className="min-h-[44px] resize-none"
          />
          <Button
            onClick={handleSubmit}
            disabled={sendMutation.isPending || !input.trim()}
            size="icon"
          >
            {sendMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}

