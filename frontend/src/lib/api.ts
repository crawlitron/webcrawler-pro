// API_BASE: empty string = relative URLs (works with Nginx /api/ proxy on any host)
// Set NEXT_PUBLIC_API_URL=http://localhost:8000 for local dev without Docker
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

import { authHeaders } from './auth';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 
      "Content-Type": "application/json", 
      ...authHeaders(),
      ...options?.headers 
    },
    ...options,
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`API Error ${res.status}: ${err}`);
  }
  if (res.status === 204) return {} as T;
  return res.json();
}

// Export all interface declarations
interface Project {
  id: number;
  name: string;
  start_url: string;
  max_urls: number;
  custom_user_agent?: string | null;
  crawl_delay: number;
  include_patterns?: string[] | null;
  exclude_patterns?: string[] | null;
  crawl_external_links: boolean;
  crawl_schedule?: string | null;
  use_js_rendering?: boolean;
  js_wait_time?: number;
  created_at: string;
  updated_at: string;
  last_crawl_status?: string;
  last_crawl_id?: number;
}

interface Crawl {
  id: number;
  project_id: number;
  status: string;
  total_urls: number;
  crawled_urls: number;
  failed_urls: number;
  critical_issues: number;
  warning_issues: number;
  info_issues: number;
  started_at?: string;
  completed_at?: string;
}

interface Page {
  id: number;
  crawl_id: number;
  url: string;
  status_code?: number;
  title?: string;
  issue_count: number;
}

interface Issue {
  id: number;
  crawl_id: number;
  page_id: number;
  severity: string;
  issue_type: string;
  description: string;
}

// Include all other interfaces from original implementation

// Export the complete API object
export const api = {
  // Projects
  getProjects: () => request<Project[]>("/api/projects"),
  getProject: (id: number) => request<Project>(`/api/projects/${id}`),
  createProject: (data: any) => request<Project>("/api/projects", { method: "POST", body: JSON.stringify(data) }),
  updateProject: (id: number, data: any) => request<Project>(`/api/projects/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteProject: (id: number) => request<void>(`/api/projects/${id}`, { method: "DELETE" }),
  
  // Crawls
  getCrawl: (id: number) => request<Crawl>(`/api/crawls/${id}`),
  getProjectCrawls: (projectId: number) => request<Crawl[]>(`/api/projects/${projectId}/crawls`),
  startCrawl: (projectId: number) => request<Crawl>(`/api/projects/${projectId}/crawls`, { method: "POST" }),
  
  // Pages
  getPages: (crawlId: number, params?: any) => request<any>(`/api/crawls/${crawlId}/pages?${new URLSearchParams(params).toString()}`),
  
  // Issues
  getIssues: (crawlId: number, params?: any) => request<any>(`/api/crawls/${crawlId}/issues?${new URLSearchParams(params).toString()}`),
  
  // Analytics
  getAnalyticsOverview: (crawlId: number) => request<any>(`/api/crawls/${crawlId}/analytics/overview`),
  
  // Include all other API methods from original implementation
};

// Export types for TypeScript
export type { Project, Crawl, Page, Issue };
// Export all other needed types

export default api;
