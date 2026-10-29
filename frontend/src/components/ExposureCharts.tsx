import {
  Bar,
  BarChart,
  Cell,
  CartesianGrid,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { MmiBand } from "../data/types";
import { formatInteger } from "../lib/format";
import { chartBands } from "../lib/mmi";

export function ExposureCharts({ bands }: { bands: MmiBand[] }) {
  const data = chartBands(bands);
  const lower = bands.filter((band) => ["<4", "4"].includes(band.mmi_band));
  const lowerBuildings = lower.reduce((sum, band) => sum + band.buildings, 0);
  const lowerPopulation = lower.reduce((sum, band) => sum + band.population, 0);
  if (!data.length)
    return (
      <div className="state-panel">
        No populated exposure cells are available for this event.
      </div>
    );
  return (
    <>
      <p className="lower-intensity-summary">
        Lower intensity (MMI below 5): {formatInteger(lowerBuildings)} buildings
        and {formatInteger(lowerPopulation)} people.
      </p>
      <div className="chart-grid">
        <Chart title="Buildings by MMI" data={data} dataKey="buildings" />
        <Chart title="Population by MMI" data={data} dataKey="population" />
      </div>
    </>
  );
}

function Chart({
  title,
  data,
  dataKey,
}: {
  title: string;
  data: MmiBand[];
  dataKey: "buildings" | "population";
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
            stroke="#c9c0ad"
          />
          <XAxis
            dataKey="mmi_band"
            tickLine={false}
            axisLine={{ stroke: "#aaa28f" }}
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
          <Bar dataKey={dataKey} maxBarSize={52} minPointSize={4}>
            {data.map((band) => (
              <Cell key={band.mmi_band} fill={mmiColour(band.mmi_band)} />
            ))}
            <LabelList
              dataKey={dataKey}
              position="top"
              formatter={(value) => compactNumber(Number(value ?? 0))}
            />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <span className="chart-legend">Modified Mercalli Intensity band</span>
    </figure>
  );
}

function mmiColour(band: string): string {
  return (
    { "5": "#fff200", "6": "#ffb300", "7": "#ff6800", "8+": "#d7191c" }[band] ??
    "#4b4a44"
  );
}

function compactNumber(value: number): string {
  return new Intl.NumberFormat("en-NZ", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value);
}
