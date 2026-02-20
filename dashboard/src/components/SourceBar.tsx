import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

interface Props {
  data: { source: string; count: number }[];
}

export function SourceBar({ data }: Props) {
  if (!data.length) {
    return (
      <div className="flex h-64 items-center justify-center text-muted">
        No source data yet
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data} layout="vertical" margin={{ left: 20 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--color-chart-grid)" />
        <XAxis
          type="number"
          tick={{ fontSize: 12, fill: "var(--color-chart-tick)" }}
          allowDecimals={false}
        />
        <YAxis
          type="category"
          dataKey="source"
          tick={{ fontSize: 12, fill: "var(--color-chart-tick)" }}
          width={140}
        />
        <Tooltip />
        <Bar
          dataKey="count"
          fill="#10b981"
          radius={[0, 4, 4, 0]}
          name="Records"
        />
      </BarChart>
    </ResponsiveContainer>
  );
}
