/**
 * API client for the Academic Research Tool backend
 */

import { logger } from './diagnostics';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const apiLogger = logger.scope('API');

export class APIError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    message: string
  ) {
    super(message);
    this.name = 'APIError';
  }
}

function getHeaders(token?: string): HeadersInit {
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

async function apiRequest<T>(
  method: string,
  path: string,
  options: { token?: string; body?: unknown } = {}
): Promise<T> {
  const url = `${API_BASE}${path}`;
  const startTime = Date.now();
  
  apiLogger.debug(`${method} ${path}`, options.body ? { body: options.body } : undefined);
  
  const fetchOptions: RequestInit = {
    method,
    headers: getHeaders(options.token),
  };
  
  if (options.body) {
    fetchOptions.body = JSON.stringify(options.body);
  }
  
  try {
    const response = await fetch(url, fetchOptions);
    const duration = Date.now() - startTime;
    
    if (!response.ok) {
      const errorBody = await response.json().catch(() => ({ detail: response.statusText }));
      const message = errorBody.detail || 'An error occurred';
      apiLogger.error(`${response.status} ${path} (${duration}ms)`, new Error(message), { error: errorBody });
      throw new APIError(response.status, response.statusText, message);
    }
    
    const data = await response.json();
    apiLogger.info(`${response.status} ${path} (${duration}ms)`, { responseSize: JSON.stringify(data).length });
    return data as T;
  } catch (error) {
    if (error instanceof APIError) throw error;
    const duration = Date.now() - startTime;
    apiLogger.error(`NETWORK ERROR ${path} (${duration}ms)`, error instanceof Error ? error : new Error(String(error)));
    throw error;
  }
}

async function apiRequestVoid(
  method: string,
  path: string,
  options: { token?: string; body?: unknown } = {}
): Promise<void> {
  const url = `${API_BASE}${path}`;
  const startTime = Date.now();
  
  apiLogger.debug(`${method} ${path}`, options.body ? { body: options.body } : undefined);
  
  const fetchOptions: RequestInit = {
    method,
    headers: getHeaders(options.token),
  };
  
  if (options.body) {
    fetchOptions.body = JSON.stringify(options.body);
  }
  
  try {
    const response = await fetch(url, fetchOptions);
    const duration = Date.now() - startTime;
    
    if (!response.ok) {
      const errorBody = await response.json().catch(() => ({ detail: response.statusText }));
      const message = errorBody.detail || 'An error occurred';
      apiLogger.error(`${response.status} ${path} (${duration}ms)`, new Error(message), { error: errorBody });
      throw new APIError(response.status, response.statusText, message);
    }
    
    apiLogger.info(`${response.status} ${path} (${duration}ms)`);
  } catch (error) {
    if (error instanceof APIError) throw error;
    const duration = Date.now() - startTime;
    apiLogger.error(`NETWORK ERROR ${path} (${duration}ms)`, error instanceof Error ? error : new Error(String(error)));
    throw error;
  }
}

// ============================================================================
// Types
// ============================================================================

export interface Project {
  id: string;
  user_id?: string;
  title: string;
  description: string | null;
  status: 'draft' | 'active' | 'archived' | 'completed';
  created_at: string;
  updated_at: string;
}

export interface ProjectCreate {
  title: string;
  description?: string;
}

export interface OutlineSection {
  id: string;
  project_id: string;
  parent_id: string | null;
  title: string;
  section_type: 'heading' | 'subheading' | 'paragraph' | 'abstract' | 'introduction' | 'methods' | 'results' | 'discussion' | 'conclusion' | 'references' | 'custom' | 'literature_review';
  content: string | null;
  order_index: number;
  research_questions: string[];
  created_at: string;
  updated_at: string;
  children?: OutlineSection[];
}

export interface OutlineSectionCreate {
  parent_id?: string | null;
  title: string;
  section_type?: string;
  content?: string;
  order_index?: number;
  research_questions?: string[];
}

export interface Author {
  name: string;
  author_id?: string;
}

export interface Source {
  id: string;
  project_id: string;
  paper_id: string | null;
  title: string;
  authors: Author[];
  abstract: string | null;
  year: number | null;
  venue: string | null;
  doi: string | null;
  pdf_url: string | null;
  ingestion_status: 'pending' | 'downloading' | 'parsing' | 'chunking' | 'ingesting' | 'ready' | 'failed';
  hyperion_doc_id: string | null;
  created_at: string;
}

export interface PaperSearchResult {
  paper_id: string;
  title: string;
  authors: Author[];
  abstract: string | null;
  year: number | null;
  venue: string | null;
  citation_count: number | null;
  doi: string | null;
  pdf_url: string | null;
  external_ids: Record<string, string>;
}

export interface PaperSearchResponse {
  results: PaperSearchResult[];
  total: number;
  offset: number;
  limit: number;
}

export interface QueryRequest {
  query: string;
  mode?: 'hybrid' | 'local' | 'global' | 'naive';
}

export interface SourceReference {
  chunk_id: string;
  source_id?: string;
  content: string;
  relevance_score: number;
  document_name?: string;
}

export interface QueryResponse {
  query: string;
  answer: string;
  sources: SourceReference[];
  synthesis_id?: string;
}

export interface DiscoveryResult {
  references: PaperSearchResult[];
  citations: PaperSearchResult[];
  related: PaperSearchResult[];
}

// ============================================================================
// Research UI Types
// ============================================================================

export interface ChatMessage {
  id: string;
  session_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface ChatRequest {
  message: string;
}

export interface ChatResponse {
  message: string;
  action_taken: string | null;
  papers_added: number[];
  papers_referenced: number[];
  sections_created: number;
  claims_created: number;
  metadata: Record<string, unknown>;
}

export interface PaperAuthor {
  name: string;
  affiliation?: string | null;
}

export interface PaperListItem {
  index: number;
  paper_id: string;
  node_id: string;
  source_id: string | null;
  title: string;
  authors: PaperAuthor[];
  year: number | null;
  summary: string;
  citation_count: number | null;
  relevance_score: number;
  user_rating: string | null;
  is_ingested: boolean;
  pdf_url: string | null;
}

export interface PaperDetails extends PaperListItem {
  abstract: string;
  venue: string | null;
  doi: string | null;
  ingestion_status: string | null;
  user_note: string | null;
}

export interface SourceBadge {
  index: number;
  paper_id: string;
  title: string;
  confidence: number;
}

export interface ClaimWithSources {
  id: string;
  claim_text: string;
  order_index: number;
  sources: SourceBadge[];
  evidence_strength: string;
  needs_sources: boolean;
  user_critique: string | null;
  status: string;
}

export interface SectionWithClaims {
  id: string;
  title: string;
  section_type: string;
  order_index: number;
  claims: ClaimWithSources[];
  total_claims: number;
  claims_with_sources: number;
  claims_needing_sources: number;
}

export interface OutlineWithSources {
  project_id: string;
  session_id: string;
  sections: SectionWithClaims[];
  total_sections: number;
  total_claims: number;
  claims_with_sources: number;
  claims_needing_sources: number;
}

export interface TreeNode {
  id: string;
  label: string;
  title: string;
  node_type: string;
  year: number | null;
  size: number;
  color: string | null;
  paper_index: number | null;
  user_rating: string | null;
}

export interface TreeEdge {
  source: string;
  target: string;
  relationship: string;
}

export interface KnowledgeTreeGraph {
  session_id: string;
  topic: string;
  nodes: TreeNode[];
  edges: TreeEdge[];
  total_papers: number;
  total_topics: number;
}

export interface ResearchSessionInfo {
  id: string;
  project_id: string;
  topic: string;
  status: string;
  papers_found: number;
  papers_ingested: number;
  outline_sections: number;
  created_at: string;
  updated_at: string;
}

// ============================================================================
// API Functions
// ============================================================================

export const api = {
  // Health
  health: () => apiRequest<{ status: string; version: string }>('GET', '/api/health'),

  // Projects
  listProjects: (token: string) => 
    apiRequest<Project[]>('GET', '/api/projects', { token }),

  getProject: (token: string, id: string) =>
    apiRequest<Project>('GET', `/api/projects/${id}`, { token }),

  createProject: (token: string, data: ProjectCreate) =>
    apiRequest<Project>('POST', '/api/projects', { token, body: data }),

  updateProject: (token: string, id: string, data: Partial<ProjectCreate>) =>
    apiRequest<Project>('PATCH', `/api/projects/${id}`, { token, body: data }),

  deleteProject: (token: string, id: string) =>
    apiRequestVoid('DELETE', `/api/projects/${id}`, { token }),

  // Outline
  getOutline: (token: string, projectId: string) =>
    apiRequest<{ project_id: string; sections: OutlineSection[]; total_count: number }>(
      'GET', `/api/projects/${projectId}/outline`, { token }
    ),

  createOutlineSection: (token: string, projectId: string, data: OutlineSectionCreate) =>
    apiRequest<OutlineSection>('POST', `/api/projects/${projectId}/outline`, { token, body: data }),

  updateOutlineSection: (token: string, projectId: string, sectionId: string, data: Partial<OutlineSectionCreate>) =>
    apiRequest<OutlineSection>('PATCH', `/api/projects/${projectId}/outline/${sectionId}`, { token, body: data }),

  deleteOutlineSection: (token: string, projectId: string, sectionId: string) =>
    apiRequestVoid('DELETE', `/api/projects/${projectId}/outline/${sectionId}`, { token }),

  // Sources
  searchPapers: (token: string, query: string, limit = 10, offset = 0) => {
    const params = new URLSearchParams({ query, limit: String(limit), offset: String(offset) });
    return apiRequest<PaperSearchResponse>('GET', `/api/projects/sources/search?${params}`, { token });
  },

  listSources: (token: string, projectId: string) =>
    apiRequest<Source[]>('GET', `/api/projects/${projectId}/sources`, { token }),

  addSource: (token: string, projectId: string, paperId: string) =>
    apiRequest<Source>('POST', `/api/projects/${projectId}/sources`, { token, body: { paper_id: paperId } }),

  ingestSource: (token: string, projectId: string, sourceId: string) =>
    apiRequest<Source>('POST', `/api/projects/${projectId}/sources/${sourceId}/ingest`, { token }),

  deleteSource: (token: string, projectId: string, sourceId: string) =>
    apiRequestVoid('DELETE', `/api/projects/${projectId}/sources/${sourceId}`, { token }),

  // Research / RAG
  query: (token: string, projectId: string, data: QueryRequest) =>
    apiRequest<QueryResponse>('POST', `/api/projects/${projectId}/research/query`, { token, body: data }),

  // Discovery
  discoverRelated: (token: string, projectId: string, sourceId: string) =>
    apiRequest<DiscoveryResult>('GET', `/api/projects/${projectId}/sources/${sourceId}/discover`, { token }),

  // ============================================================================
  // Research UI (Chat-Driven Interface)
  // ============================================================================

  // Chat
  sendChatMessage: (token: string, projectId: string, message: string) =>
    apiRequest<ChatResponse>('POST', `/api/projects/${projectId}/research-ui/chat`, { token, body: { message } }),

  getChatHistory: (token: string, projectId: string, limit = 50) =>
    apiRequest<ChatMessage[]>('GET', `/api/projects/${projectId}/research-ui/chat/history?limit=${limit}`, { token }),

  // Papers (Explore Tab)
  getPapersList: (token: string, projectId: string) =>
    apiRequest<PaperListItem[]>('GET', `/api/projects/${projectId}/research-ui/papers`, { token }),

  getPaperDetails: (token: string, projectId: string, index: number) =>
    apiRequest<PaperDetails>('GET', `/api/projects/${projectId}/research-ui/papers/${index}`, { token }),

  // Outline with Sources (Outline Tab)
  getOutlineWithSources: (token: string, projectId: string) =>
    apiRequest<OutlineWithSources>('GET', `/api/projects/${projectId}/research-ui/outline`, { token }),

  // Knowledge Tree (Knowledge Tree Tab)
  getKnowledgeTree: (token: string, projectId: string) =>
    apiRequest<KnowledgeTreeGraph>('GET', `/api/projects/${projectId}/research-ui/tree`, { token }),

  // Session
  getResearchSession: (token: string, projectId: string) =>
    apiRequest<ResearchSessionInfo | null>('GET', `/api/projects/${projectId}/research-ui/session`, { token }),
};
