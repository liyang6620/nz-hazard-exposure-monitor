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

import type { MmiBand } from "../data/types";

export function ExposureCharts({ bands }: { bands: MmiBand[] }) {
  const data = bands.filter(
    (band) => band.buildings > 0 || band.population > 0,
  );
  if (!data.length)
    return (
      <div className="state-panel">
        No populated exposure cells are available for this event.
      </div>
    );
  return (
    <div className="chart-grid">
      <Chart
        title="Buildings by MMI"
        data={data}
        dataKey="buildings"
        colour="#176b62"
      />
      <Chart
        title="Population by MMI"
        data={data}
        dataKey="population"
        colour="#c44d2d"
      />
    </div>
  );
}

function Chart({
  title,
  data,
  dataKey,
  colour,
}: {
  title: string;
  data: MmiBand[];
  dataKey: "buildings" | "population";
  colour: string;
}) {
  return (
    <figure className="chart-panel">
      <figcaption>{title}</figcaption>
      <ResponsiveContainer width="100%" height={260}>
        <BarChart
          data={data}
          margin={{ top: 12, right: 8, left: 2, bottom: 0 }}
        >
          <CartesianGrid
            strokeDasharray="3 3"
            vertical={false}
            stroke="#dce3e0"
          />
          <XAxis
            dataKey="mmi_band"
            tickLine={false}
            axisLine={{ stroke: "#aab7b2" }}
          />
          <YAxis
            tickLine={false}
            axisLine={false}
            width={56}
            tickFormatter={compactNumber}
          />
          <Tooltip
            formatter={(value) =>
              Number(value).toLocaleString("en-NZ", {
                maximumFractionDigits: 0,
              })
            }
          />
          <Legend
            content={() => (
              <span className="chart-legend">
                Modified Mercalli Intensity band
              </span>
            )}
          />
          <Bar
            dataKey={dataKey}
            fill={colour}
            radius={[3, 3, 0, 0]}
            maxBarSize={52}
          />
        </BarChart>
      </ResponsiveContainer>
    </figure>
  );
}

function compactNumber(value: number): string {
  return new Intl.NumberFormat("en-NZ", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value);
}
