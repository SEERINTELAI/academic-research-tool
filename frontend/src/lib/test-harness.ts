/**
 * Test harness for frontend state inspection and debugging.
 * 
 * Exposes React Query cache state, Zustand stores, and network history
 * via window.__TEST_HARNESS__ in development mode.
 * 
 * Usage in browser console:
 *   window.__TEST_HARNESS__.getState()
 *   window.__TEST_HARNESS__.getQueryCache()
 *   window.__TEST_HARNESS__.getNetworkHistory()
 *   window.__TEST_HARNESS__.clearNetworkHistory()
 */

import { QueryClient } from '@tanstack/react-query';
import { 
  useAuthStore, 
  useProjectStore, 
  useOutlineStore, 
  useSourcesStore,
  useEditorStore,
  useUIStore,
} from './store';

// Network request history
interface NetworkRequest {
  id: string;
  url: string;
  method: string;
  status?: number;
  duration?: number;
  error?: string;
  timestamp: string;
  requestBody?: unknown;
  responseBody?: unknown;
}

const networkHistory: NetworkRequest[] = [];
const MAX_NETWORK_HISTORY = 100;

/**
 * Record a network request for debugging.
 */
export function recordNetworkRequest(request: NetworkRequest): void {
  networkHistory.push(request);
  if (networkHistory.length > MAX_NETWORK_HISTORY) {
    networkHistory.shift();
  }
}

/**
 * Test harness interface exposed to window.
 */
interface TestHarness {
  // State inspection
  getState: () => {
    auth: ReturnType<typeof useAuthStore.getState>;
    projects: ReturnType<typeof useProjectStore.getState>;
    outline: ReturnType<typeof useOutlineStore.getState>;
    sources: ReturnType<typeof useSourcesStore.getState>;
    editor: ReturnType<typeof useEditorStore.getState>;
    ui: ReturnType<typeof useUIStore.getState>;
  };
  
  // Query cache inspection
  getQueryCache: () => {
    queries: Array<{
      queryKey: unknown;
      state: string;
      dataUpdatedAt: number;
      errorUpdatedAt: number;
    }>;
    mutations: Array<{
      mutationId: number;
      state: string;
    }>;
  } | null;
  
  // Network history
  getNetworkHistory: () => NetworkRequest[];
  clearNetworkHistory: () => void;
  
  // Actions for testing
  actions: {
    setAuth: (token: string, userId: string) => void;
    clearAuth: () => void;
    setTheme: (theme: 'light' | 'dark' | 'system') => void;
  };
  
  // Version info
  version: string;
  initialized: boolean;
}

// Reference to query client (set by initTestHarness)
let queryClientRef: QueryClient | null = null;

/**
 * Initialize the test harness with the QueryClient.
 * Call this from your Providers component.
 */
export function initTestHarness(queryClient: QueryClient): void {
  if (typeof window === 'undefined') return;
  if (process.env.NODE_ENV !== 'development') return;
  
  queryClientRef = queryClient;
  
  const testHarness: TestHarness = {
    version: '1.0.0',
    initialized: true,
    
    getState: () => ({
      auth: useAuthStore.getState(),
      projects: useProjectStore.getState(),
      outline: useOutlineStore.getState(),
      sources: useSourcesStore.getState(),
      editor: useEditorStore.getState(),
      ui: useUIStore.getState(),
    }),
    
    getQueryCache: () => {
      if (!queryClientRef) return null;
      
      const queryCache = queryClientRef.getQueryCache();
      const mutationCache = queryClientRef.getMutationCache();
      
      return {
        queries: queryCache.getAll().map(query => ({
          queryKey: query.queryKey,
          state: query.state.status,
          dataUpdatedAt: query.state.dataUpdatedAt,
          errorUpdatedAt: query.state.errorUpdatedAt,
        })),
        mutations: mutationCache.getAll().map(mutation => ({
          mutationId: mutation.mutationId,
          state: mutation.state.status,
        })),
      };
    },
    
    getNetworkHistory: () => [...networkHistory],
    
    clearNetworkHistory: () => {
      networkHistory.length = 0;
    },
    
    actions: {
      setAuth: (token: string, userId: string) => {
        useAuthStore.getState().setAuth(token, userId);
      },
      clearAuth: () => {
        useAuthStore.getState().clearAuth();
      },
      setTheme: (theme: 'light' | 'dark' | 'system') => {
        useUIStore.getState().setTheme(theme);
      },
    },
  };
  
  // Expose to window
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  (window as any).__TEST_HARNESS__ = testHarness;
  
  console.log(
    '%c🧪 Test Harness Initialized',
    'color: #10b981; font-weight: bold; font-size: 14px;'
  );
  console.log(
    '%cAccess via window.__TEST_HARNESS__',
    'color: #6b7280; font-size: 12px;'
  );
  console.log(
    '%cMethods: getState(), getQueryCache(), getNetworkHistory(), actions.*',
    'color: #6b7280; font-size: 12px;'
  );
}

/**
 * Wrap fetch to record network requests.
 * Call this once during app initialization.
 */
export function instrumentFetch(): void {
  if (typeof window === 'undefined') return;
  if (process.env.NODE_ENV !== 'development') return;
  
  const originalFetch = window.fetch;
  
  window.fetch = async function(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
    const requestId = Math.random().toString(36).substring(2, 9);
    const url = typeof input === 'string' ? input : input instanceof URL ? input.toString() : input.url;
    const method = init?.method || 'GET';
    const startTime = Date.now();
    
    const record: NetworkRequest = {
      id: requestId,
      url,
      method,
      timestamp: new Date().toISOString(),
    };
    
    // Try to capture request body
    if (init?.body) {
      try {
        record.requestBody = JSON.parse(init.body as string);
      } catch {
        record.requestBody = '<non-JSON body>';
      }
    }
    
    try {
      const response = await originalFetch(input, init);
      record.status = response.status;
      record.duration = Date.now() - startTime;
      
      // Clone response to read body without consuming it
      const cloned = response.clone();
      try {
        record.responseBody = await cloned.json();
      } catch {
        // Not JSON response
      }
      
      recordNetworkRequest(record);
      return response;
    } catch (error) {
      record.error = error instanceof Error ? error.message : String(error);
      record.duration = Date.now() - startTime;
      recordNetworkRequest(record);
      throw error;
    }
  };
  
  console.log(
    '%c🔍 Fetch instrumented for network history',
    'color: #8b5cf6; font-size: 12px;'
  );
}

// Type declaration for window
declare global {
  interface Window {
    __TEST_HARNESS__?: TestHarness;
  }
}

