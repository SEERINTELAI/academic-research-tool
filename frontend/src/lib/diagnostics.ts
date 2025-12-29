/**
 * Diagnostic utilities for debugging and logging.
 * 
 * Logs are:
 * 1. Stored in-memory for the DiagnosticsPanel
 * 2. Printed to browser console
 * 3. Sent to backend /api/logs endpoint for server-side visibility
 */

// Log levels
export type LogLevel = 'debug' | 'info' | 'warn' | 'error';

interface LogEntry {
  timestamp: string;
  level: LogLevel;
  source: string;
  message: string;
  data?: unknown;
  stack?: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8003';

class DiagnosticLogger {
  private logs: LogEntry[] = [];
  private pendingLogs: LogEntry[] = [];
  private maxLogs = 1000;
  private enabled: boolean;
  private consoleOutput: boolean;
  private flushInterval: ReturnType<typeof setInterval> | null = null;
  private sendToBackend: boolean = true;

  constructor() {
    // Enable in development
    this.enabled = process.env.NODE_ENV === 'development';
    this.consoleOutput = true;
    
    // Start periodic flush to backend
    if (typeof window !== 'undefined' && this.enabled) {
      this.flushInterval = setInterval(() => this.flush(), 5000);
    }
  }

  private formatEntry(entry: LogEntry): string {
    const prefix = `[${entry.timestamp}] [${entry.level.toUpperCase()}] [${entry.source}]`;
    return `${prefix} ${entry.message}`;
  }

  private addEntry(level: LogLevel, source: string, message: string, data?: unknown, error?: Error) {
    if (!this.enabled) return;

    const entry: LogEntry = {
      timestamp: new Date().toISOString(),
      level,
      source,
      message,
      data: data as Record<string, unknown> | undefined,
      stack: error?.stack,
    };

    this.logs.push(entry);
    if (this.logs.length > this.maxLogs) {
      this.logs.shift();
    }

    // Queue for backend
    if (this.sendToBackend) {
      this.pendingLogs.push(entry);
    }

    // Console output with colors
    if (this.consoleOutput) {
      const formattedMessage = this.formatEntry(entry);
      const styles: Record<LogLevel, string> = {
        debug: 'color: gray',
        info: 'color: blue',
        warn: 'color: orange',
        error: 'color: red; font-weight: bold',
      };

      console.log(`%c${formattedMessage}`, styles[level]);
      if (data) {
        console.log('  Data:', data);
      }
      if (error?.stack) {
        console.log('  Stack:', error.stack);
      }
    }

    // Immediately flush errors to backend
    if (level === 'error' && this.sendToBackend) {
      this.flush();
    }
  }

  /**
   * Flush pending logs to the backend.
   */
  async flush(): Promise<void> {
    if (this.pendingLogs.length === 0) return;
    
    const logsToSend = [...this.pendingLogs];
    this.pendingLogs = [];

    try {
      const response = await fetch(`${API_BASE}/api/logs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          logs: logsToSend.map(log => ({
            level: log.level,
            source: log.source,
            message: log.message,
            data: log.data,
            error: log.stack,
            url: typeof window !== 'undefined' ? window.location.pathname : undefined,
            timestamp: log.timestamp,
          })),
        }),
      });

      if (!response.ok) {
        // Don't log this error to avoid infinite loop
        console.warn('Failed to send logs to backend:', response.status);
      }
    } catch {
      // Silently fail - don't want logging to break the app
      console.warn('Failed to send logs to backend (network error)');
    }
  }

  debug(source: string, message: string, data?: unknown) {
    this.addEntry('debug', source, message, data);
  }

  info(source: string, message: string, data?: unknown) {
    this.addEntry('info', source, message, data);
  }

  warn(source: string, message: string, data?: unknown) {
    this.addEntry('warn', source, message, data);
  }

  error(source: string, message: string, error?: Error, data?: unknown) {
    this.addEntry('error', source, message, data, error);
  }

  // Get all logs
  getLogs(level?: LogLevel): LogEntry[] {
    if (level) {
      return this.logs.filter((l) => l.level === level);
    }
    return [...this.logs];
  }

  // Get recent logs
  getRecent(count = 50): LogEntry[] {
    return this.logs.slice(-count);
  }

  // Export logs as JSON
  exportLogs(): string {
    return JSON.stringify(this.logs, null, 2);
  }

  // Clear logs
  clear() {
    this.logs = [];
    this.pendingLogs = [];
  }

  // Create a scoped logger for a specific component
  scope(source: string) {
    return {
      debug: (message: string, data?: unknown) => this.debug(source, message, data),
      info: (message: string, data?: unknown) => this.info(source, message, data),
      warn: (message: string, data?: unknown) => this.warn(source, message, data),
      error: (message: string, error?: Error, data?: unknown) => this.error(source, message, error, data),
    };
  }

  // Cleanup on unmount
  destroy() {
    if (this.flushInterval) {
      clearInterval(this.flushInterval);
    }
    this.flush(); // Send remaining logs
  }
}

// Singleton instance
export const logger = new DiagnosticLogger();

// Global error handlers
if (typeof window !== 'undefined') {
  // Catch uncaught errors
  window.addEventListener('error', (event) => {
    logger.error('GLOBAL', `Uncaught error: ${event.message}`, event.error, {
      filename: event.filename,
      lineno: event.lineno,
      colno: event.colno,
    });
  });

  // Catch unhandled promise rejections
  window.addEventListener('unhandledrejection', (event) => {
    logger.error(
      'GLOBAL',
      `Unhandled promise rejection: ${event.reason?.message || event.reason}`,
      event.reason instanceof Error ? event.reason : new Error(String(event.reason))
    );
  });

  // Flush logs before page unload
  window.addEventListener('beforeunload', () => {
    logger.flush();
  });

  // Expose to window for debugging in browser console
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  (window as any).__diagnostics = logger;
}
