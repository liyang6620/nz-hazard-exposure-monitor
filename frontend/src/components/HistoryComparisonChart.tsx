import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { EventSummary } from "../data/types";
import { displayEventName, formatInteger } from "../lib/format";

export function HistoryComparisonChart({ events }: { events: EventSummary[] }) {
  const data = events.map((event) => ({
    name: displayEventName(event.name)
      .replace("Christchurch, ", "Chch, ")
      .replace(/\s20\d{2}$/, ""),
    Buildings: event.buildings_mmi_ge_6 ?? 0,
    People: Math.round(event.population_mmi_ge_6 ?? 0),
  }));

  return (
    <figure className="history-chart">
      <figcaption>Buildings and people exposed to MMI 6+ shaking</figcaption>
      <div className="history-legend" aria-label="Comparison chart legend">
        <span>
          <i className="buildings" />
          Buildings
        </span>
        <span>
          <i className="people" />
          People
        </span>
      </div>
      <div className="history-chart-canvas">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            margin={{ top: 12, right: 8, left: 2, bottom: 42 }}
          >
            <CartesianGrid strokeDasharray="2 4" vertical={false} />
            <XAxis
              dataKey="name"
              angle={-32}
              interval={0}
              textAnchor="end"
              height={72}
            />
            <YAxis
              tickFormatter={(value: number) => `${Math.round(value / 1000)}k`}
            />
            <Tooltip formatter={(value) => formatInteger(Number(value))} />
            <Legend content={() => null} />
            <Bar dataKey="Buildings" fill="#171815" />
            <Bar
              dataKey="People"
              fill="#f2eddf"
              stroke="#171815"
              strokeWidth={1}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p>
        Counts use current building stock and 2023 population. Zero means the
        replay did not reach damaging shaking, not that no assets exist.
      </p>
    </figure>
  );
}
