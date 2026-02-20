const BASE = "/api";

export interface Stats {
  raw_count: number;
  canonical_count: number;
  categories: { category: string; count: number }[];
  sources: { source: string; count: number }[];
  statuses: { status: string; count: number }[];
  timeline: { date: string; count: number }[];
}

export interface RawRecord {
  source_id: string;
  source_name: string;
  source_url: string;
  fetched_at: string;
  extracted: Record<string, string>;
  content_hash: string;
}

export interface CanonicalRecord {
  record_id: string;
  source_name: string;
  source_id: string;
  source_url: string;
  title: string;
  description: string;
  agency: string;
  posted_date: string | null;
  due_date: string | null;
  estimated_value: number | null;
  currency: string;
  category: string;
  category_confidence: number;
  status: string;
}

export interface PaginatedResponse<T> {
  total: number;
  records: T[];
}

export interface Source {
  name: string;
  count: number;
}

async function fetchJSON<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export const api = {
  health: () => fetchJSON<{ status: string }>(`${BASE}/health`),
  stats: () => fetchJSON<Stats>(`${BASE}/stats`),
  sources: () => fetchJSON<Source[]>(`${BASE}/sources`),

  rawRecords: (params?: { source?: string; limit?: number; skip?: number }) => {
    const q = new URLSearchParams();
    if (params?.source) q.set("source", params.source);
    if (params?.limit) q.set("limit", String(params.limit));
    if (params?.skip) q.set("skip", String(params.skip));
    return fetchJSON<PaginatedResponse<RawRecord>>(
      `${BASE}/records/raw?${q.toString()}`
    );
  },

  canonicalRecords: (params?: {
    source?: string;
    category?: string;
    status?: string;
    search?: string;
    limit?: number;
    skip?: number;
  }) => {
    const q = new URLSearchParams();
    if (params?.source) q.set("source", params.source);
    if (params?.category) q.set("category", params.category);
    if (params?.status) q.set("status", params.status);
    if (params?.search) q.set("search", params.search);
    if (params?.limit) q.set("limit", String(params.limit));
    if (params?.skip) q.set("skip", String(params.skip));
    return fetchJSON<PaginatedResponse<CanonicalRecord>>(
      `${BASE}/records/canonical?${q.toString()}`
    );
  },
};
