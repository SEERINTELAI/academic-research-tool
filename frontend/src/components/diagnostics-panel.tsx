'use client';

import { useState, useEffect } from 'react';
import { Bug, X, ChevronDown, ChevronUp, Trash2, Download, Copy, Check } from 'lucide-react';
import { logger, type LogLevel } from '@/lib/diagnostics';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';

const levelColors: Record<LogLevel, string> = {
  debug: 'bg-gray-500/20 text-gray-600 dark:text-gray-400',
  info: 'bg-blue-500/20 text-blue-600 dark:text-blue-400',
  warn: 'bg-yellow-500/20 text-yellow-600 dark:text-yellow-400',
  error: 'bg-red-500/20 text-red-600 dark:text-red-400',
};

export function DiagnosticsPanel() {
  const [isOpen, setIsOpen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [logs, setLogs] = useState<ReturnType<typeof logger.getLogs>>([]);
  const [filter, setFilter] = useState<LogLevel | 'all'>('all');
  const [copied, setCopied] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);

  useEffect(() => {
    if (!isOpen || !autoRefresh) return;

    const interval = setInterval(() => {
      setLogs(logger.getLogs());
    }, 500);

    return () => clearInterval(interval);
  }, [isOpen, autoRefresh]);

  useEffect(() => {
    if (isOpen) {
      setLogs(logger.getLogs());
    }
  }, [isOpen]);

  const filteredLogs = filter === 'all' ? logs : logs.filter((l) => l.level === filter);
  const errorCount = logs.filter((l) => l.level === 'error').length;
  const warnCount = logs.filter((l) => l.level === 'warn').length;

  const handleCopy = async () => {
    await navigator.clipboard.writeText(logger.exportLogs());
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const blob = new Blob([logger.exportLogs()], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `diagnostics-${new Date().toISOString()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Only show in development
  if (process.env.NODE_ENV !== 'development') {
    return null;
  }

  return (
    <>
      {/* Floating button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="fixed bottom-4 right-4 z-50 flex h-12 w-12 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-lg transition-transform hover:scale-110"
        title="Open Diagnostics"
      >
        <Bug className="h-5 w-5" />
        {(errorCount > 0 || warnCount > 0) && (
          <span className="absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full bg-destructive text-xs text-white">
            {errorCount || warnCount}
          </span>
        )}
      </button>

      {/* Panel */}
      {isOpen && (
        <div
          className={`fixed bottom-20 right-4 z-50 w-[600px] overflow-hidden rounded-lg border border-border bg-card shadow-2xl transition-all ${
            isMinimized ? 'h-12' : 'h-[500px]'
          }`}
        >
          {/* Header */}
          <div className="flex h-12 items-center justify-between border-b border-border bg-muted/50 px-4">
            <div className="flex items-center gap-3">
              <Bug className="h-4 w-4 text-primary" />
              <span className="font-medium">Diagnostics</span>
              <Badge variant="secondary" className="text-xs">
                {logs.length} logs
              </Badge>
              {errorCount > 0 && (
                <Badge variant="destructive" className="text-xs">
                  {errorCount} errors
                </Badge>
              )}
            </div>
            <div className="flex items-center gap-1">
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={() => setIsMinimized(!isMinimized)}
              >
                {isMinimized ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              </Button>
              <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => setIsOpen(false)}>
                <X className="h-4 w-4" />
              </Button>
            </div>
          </div>

          {!isMinimized && (
            <>
              {/* Toolbar */}
              <div className="flex items-center gap-2 border-b border-border px-4 py-2">
                <select
                  value={filter}
                  onChange={(e) => setFilter(e.target.value as LogLevel | 'all')}
                  className="rounded border border-border bg-background px-2 py-1 text-sm"
                >
                  <option value="all">All levels</option>
                  <option value="debug">Debug</option>
                  <option value="info">Info</option>
                  <option value="warn">Warn</option>
                  <option value="error">Error</option>
                </select>
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={autoRefresh}
                    onChange={(e) => setAutoRefresh(e.target.checked)}
                  />
                  Auto-refresh
                </label>
                <div className="flex-1" />
                <Button variant="ghost" size="sm" onClick={handleCopy}>
                  {copied ? <Check className="mr-1 h-3 w-3" /> : <Copy className="mr-1 h-3 w-3" />}
                  Copy
                </Button>
                <Button variant="ghost" size="sm" onClick={handleDownload}>
                  <Download className="mr-1 h-3 w-3" />
                  Export
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    logger.clear();
                    setLogs([]);
                  }}
                >
                  <Trash2 className="mr-1 h-3 w-3" />
                  Clear
                </Button>
              </div>

              {/* Logs */}
              <ScrollArea className="h-[calc(100%-96px)]">
                <div className="space-y-1 p-2 font-mono text-xs">
                  {filteredLogs.length === 0 ? (
                    <div className="py-8 text-center text-muted-foreground">
                      No logs yet. Interact with the app to see API calls.
                    </div>
                  ) : (
                    filteredLogs.map((log, i) => (
                      <div
                        key={i}
                        className="group rounded border border-transparent px-2 py-1 hover:border-border hover:bg-muted/30"
                      >
                        <div className="flex items-start gap-2">
                          <Badge className={`${levelColors[log.level]} shrink-0 text-[10px]`}>
                            {log.level.toUpperCase()}
                          </Badge>
                          <span className="shrink-0 text-muted-foreground">
                            [{log.source}]
                          </span>
                          <span className="flex-1 break-all">{log.message}</span>
                          <span className="shrink-0 text-muted-foreground">
                            {new Date(log.timestamp).toLocaleTimeString()}
                          </span>
                        </div>
                        {log.data !== undefined && (
                          <pre className="mt-1 overflow-x-auto rounded bg-muted/50 p-2 text-[10px]">
                            {JSON.stringify(log.data, null, 2)}
                          </pre>
                        )}
                        {log.stack && (
                          <pre className="mt-1 overflow-x-auto rounded bg-destructive/10 p-2 text-[10px] text-destructive">
                            {log.stack}
                          </pre>
                        )}
                      </div>
                    ))
                  )}
                </div>
              </ScrollArea>
            </>
          )}
        </div>
      )}
    </>
  );
}

