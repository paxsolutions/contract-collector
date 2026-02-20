import { Database, FileText, Layers, RefreshCw, Search } from "lucide-react";
import { useEffect, useState } from "react";
import type { CanonicalRecord, Stats } from "./api";
import { api } from "./api";
import { CategoryChart } from "./components/CategoryChart";
import { RecordsTable } from "./components/RecordsTable";
import { SourceBar } from "./components/SourceBar";
import { StatCard } from "./components/StatCard";
import { ThemeToggle } from "./components/ThemeToggle";
import { TimelineChart } from "./components/TimelineChart";
import { useTheme } from "./hooks/useTheme";

export default function App() {
  const { theme, toggle: toggleTheme } = useTheme();
  const [stats, setStats] = useState<Stats | null>(null);
  const [records, setRecords] = useState<CanonicalRecord[]>([]);
  const [totalRecords, setTotalRecords] = useState(0);
  const [loading, setLoading] = useState(true);
  const [recordsLoading, setRecordsLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [source, setSource] = useState("");
  const [category, setCategory] = useState("");
  const [page, setPage] = useState(0);
  const pageSize = 25;

  const fetchStats = async () => {
    try {
      const data = await api.stats();
      setStats(data);
    } catch (err) {
      console.error("Failed to fetch stats:", err);
    } finally {
      setLoading(false);
    }
  };

  const fetchRecords = async () => {
    setRecordsLoading(true);
    try {
      const data = await api.canonicalRecords({
        search: search || undefined,
        source: source || undefined,
        category: category || undefined,
        limit: pageSize,
        skip: page * pageSize,
      });
      setRecords(data.records);
      setTotalRecords(data.total);
    } catch (err) {
      console.error("Failed to fetch records:", err);
    } finally {
      setRecordsLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  useEffect(() => {
    fetchRecords();
  }, [search, source, category, page]);

  const totalPages = Math.ceil(totalRecords / pageSize);
  const categories = stats?.categories.map((c) => c.category) ?? [];

  return (
    <div className="min-h-screen bg-surface-alt">
      {/* Header */}
      <header className="border-b border-border bg-surface px-6 py-4">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-white">
              <FileText size={20} />
            </div>
            <div>
              <h1 className="text-lg font-semibold text-heading">
                Contract Collector
              </h1>
              <p className="text-xs text-muted">
                Procurement Intelligence Dashboard
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <ThemeToggle theme={theme} onToggle={toggleTheme} />
            <button
              onClick={() => {
                setLoading(true);
                fetchStats();
                fetchRecords();
              }}
              className="flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-sm text-muted hover:bg-surface-alt transition-colors cursor-pointer"
            >
              <RefreshCw size={14} />
              Refresh
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-6 px-6 py-6">
        {/* Stats cards */}
        {loading ? (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {[...Array(4)].map((_, i) => (
              <div
                key={i}
                className="h-28 animate-pulse rounded-xl bg-surface border border-border"
              />
            ))}
          </div>
        ) : stats ? (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              title="Raw Records"
              value={stats.raw_count}
              icon={<Database size={20} />}
              subtitle="Collected from all sources"
            />
            <StatCard
              title="Canonical Records"
              value={stats.canonical_count}
              icon={<Layers size={20} />}
              subtitle="Normalized & deduplicated"
            />
            <StatCard
              title="Sources"
              value={stats.sources.length}
              icon={<FileText size={20} />}
              subtitle={stats.sources.map((s) => s.source).join(", ") || "—"}
            />
            <StatCard
              title="Categories"
              value={stats.categories.length}
              icon={<Search size={20} />}
              subtitle="Classified by ML pipeline"
            />
          </div>
        ) : null}

        {/* Charts row */}
        {stats && (
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <div className="rounded-xl border border-border bg-surface p-6 shadow-sm">
              <h2 className="mb-4 text-sm font-semibold text-heading">
                Records Over Time
              </h2>
              <TimelineChart data={stats.timeline} />
            </div>
            <div className="rounded-xl border border-border bg-surface p-6 shadow-sm">
              <h2 className="mb-4 text-sm font-semibold text-heading">
                By Category
              </h2>
              <CategoryChart data={stats.categories} />
            </div>
          </div>
        )}

        {stats && stats.sources.length > 0 && (
          <div className="rounded-xl border border-border bg-surface p-6 shadow-sm">
            <h2 className="mb-4 text-sm font-semibold text-heading">
              Records by Source
            </h2>
            <SourceBar data={stats.sources} />
          </div>
        )}

        {/* Records table */}
        <div className="rounded-xl border border-border bg-surface shadow-sm">
          <div className="flex flex-wrap items-center gap-3 border-b border-border px-6 py-4">
            <h2 className="text-sm font-semibold text-heading">
              Canonical Records
            </h2>
            <span className="text-xs text-muted">
              {totalRecords.toLocaleString()} total
            </span>
            <div className="ml-auto flex flex-wrap items-center gap-2">
              <div className="relative">
                <Search
                  size={14}
                  className="absolute left-3 top-1/2 -translate-y-1/2 text-muted"
                />
                <input
                  type="text"
                  placeholder="Search title, agency…"
                  value={search}
                  onChange={(e) => {
                    setSearch(e.target.value);
                    setPage(0);
                  }}
                  className="rounded-lg border border-border bg-surface-alt py-1.5 pl-9 pr-3 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary"
                />
              </div>
              <select
                value={source}
                onChange={(e) => {
                  setSource(e.target.value);
                  setPage(0);
                }}
                className="rounded-lg border border-border bg-surface-alt px-3 py-1.5 text-sm outline-none focus:border-primary"
              >
                <option value="">All sources</option>
                {stats?.sources.map((s) => (
                  <option key={s.source} value={s.source}>
                    {s.source}
                  </option>
                ))}
              </select>
              <select
                value={category}
                onChange={(e) => {
                  setCategory(e.target.value);
                  setPage(0);
                }}
                className="rounded-lg border border-border bg-surface-alt px-3 py-1.5 text-sm outline-none focus:border-primary"
              >
                <option value="">All categories</option>
                {categories.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <RecordsTable records={records} loading={recordsLoading} />

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between border-t border-border px-6 py-3">
              <button
                disabled={page === 0}
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                className="rounded-lg border border-border px-3 py-1.5 text-sm text-muted hover:bg-surface-alt disabled:opacity-40 cursor-pointer disabled:cursor-not-allowed"
              >
                Previous
              </button>
              <span className="text-xs text-muted">
                Page {page + 1} of {totalPages}
              </span>
              <button
                disabled={page + 1 >= totalPages}
                onClick={() => setPage((p) => p + 1)}
                className="rounded-lg border border-border px-3 py-1.5 text-sm text-muted hover:bg-surface-alt disabled:opacity-40 cursor-pointer disabled:cursor-not-allowed"
              >
                Next
              </button>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
