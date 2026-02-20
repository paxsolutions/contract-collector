import { ExternalLink } from "lucide-react";
import type { CanonicalRecord } from "../api";

interface Props {
  records: CanonicalRecord[];
  loading: boolean;
}

function statusColor(status: string): string {
  switch (status) {
    case "active":
      return "bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300";
    case "closed":
      return "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300";
    case "awarded":
      return "bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300";
    case "cancelled":
      return "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300";
    default:
      return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300";
  }
}

function fmtDate(d: string | null): string {
  if (!d) return "—";
  return new Date(d).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function RecordsTable({ records, loading }: Props) {
  if (loading) {
    return (
      <div className="flex h-40 items-center justify-center text-muted">
        Loading records…
      </div>
    );
  }

  if (!records.length) {
    return (
      <div className="flex h-40 items-center justify-center text-muted">
        No records found
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-border text-xs uppercase tracking-wide text-muted">
            <th className="px-4 py-3">Title</th>
            <th className="px-4 py-3">Agency</th>
            <th className="px-4 py-3">Source</th>
            <th className="px-4 py-3">Category</th>
            <th className="px-4 py-3">Status</th>
            <th className="px-4 py-3">Posted</th>
            <th className="px-4 py-3">Due</th>
            <th className="px-4 py-3 text-right">Value</th>
            <th className="px-4 py-3" />
          </tr>
        </thead>
        <tbody>
          {records.map((r) => (
            <tr
              key={r.record_id}
              className="border-b border-border last:border-0 hover:bg-surface-alt"
            >
              <td className="max-w-xs truncate px-4 py-3 font-medium text-heading">
                {r.title || "—"}
              </td>
              <td className="px-4 py-3 text-muted">{r.agency || "—"}</td>
              <td className="px-4 py-3 text-muted">{r.source_name}</td>
              <td className="px-4 py-3">
                {r.category ? (
                  <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
                    {r.category}
                  </span>
                ) : (
                  "—"
                )}
              </td>
              <td className="px-4 py-3">
                <span
                  className={`rounded-full px-2 py-0.5 text-xs font-medium ${statusColor(r.status)}`}
                >
                  {r.status}
                </span>
              </td>
              <td className="px-4 py-3 text-muted whitespace-nowrap">
                {fmtDate(r.posted_date)}
              </td>
              <td className="px-4 py-3 text-muted whitespace-nowrap">
                {fmtDate(r.due_date)}
              </td>
              <td className="px-4 py-3 text-right tabular-nums">
                {r.estimated_value
                  ? `$${r.estimated_value.toLocaleString()}`
                  : "—"}
              </td>
              <td className="px-4 py-3">
                {r.source_url && (
                  <a
                    href={r.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary hover:text-primary-dark"
                  >
                    <ExternalLink size={14} />
                  </a>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
