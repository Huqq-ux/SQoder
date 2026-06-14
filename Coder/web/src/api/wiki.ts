import { api } from './client';

export interface WikiPageSummary {
  path: string;
  title: string;
  category: string;
  link_count: number;
  backlink_count: number;
  modified: string;
}

export interface WikiPageDetail {
  path: string;
  frontmatter: Record<string, any>;
  body: string;
  backlinks: string[];
}

export interface WikiSearchResult {
  path: string;
  title: string;
  snippet: string;
  score: number;
}

export interface WikiLintResult {
  broken_links: Array<{ source: string; target: string }>;
  orphans: string[];
  frontmatter_issues: string[];
  total_pages: number;
  health: 'good' | 'warning' | 'error';
}

export interface WikiIngestResponse {
  status: string;
  pages_created: number;
  pages_updated: number;
  errors: string[];
}

export async function listWikiPages(courseId: string): Promise<WikiPageSummary[]> {
  const data = await api.get<{ pages: WikiPageSummary[] }>(`/wiki/${courseId}/pages`);
  return data.pages;
}

export async function getWikiPage(courseId: string, path: string): Promise<WikiPageDetail> {
  return api.get<WikiPageDetail>(`/wiki/${courseId}/pages/${encodeURIComponent(path)}`);
}

export async function getWikiIndex(courseId: string): Promise<string> {
  const data = await api.get<{ content: string }>(`/wiki/${courseId}/index`);
  return data.content;
}

export async function getWikiSchema(courseId: string): Promise<string> {
  const data = await api.get<{ content: string }>(`/wiki/${courseId}/schema`);
  return data.content;
}

export async function getWikiLog(courseId: string): Promise<string[]> {
  const data = await api.get<{ entries: string[] }>(`/wiki/${courseId}/log`);
  return data.entries;
}

export async function searchWiki(courseId: string, query: string): Promise<WikiSearchResult[]> {
  const data = await api.post<{ results: WikiSearchResult[] }>(`/wiki/${courseId}/search`, { query });
  return data.results;
}

export async function ingestWiki(courseId: string): Promise<WikiIngestResponse> {
  return api.post<WikiIngestResponse>(`/wiki/${courseId}/ingest`);
}

export async function lintWiki(courseId: string): Promise<WikiLintResult> {
  return api.post<WikiLintResult>(`/wiki/${courseId}/lint`);
}
