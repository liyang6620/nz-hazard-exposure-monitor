import type { RegionExposure } from "../data/types";
import { formatInteger } from "../lib/format";

export function RegionExposureTable({
  regions,
}: {
  regions: RegionExposure[];
}) {
  if (!regions.length)
    return (
      <div className="state-panel">
        No regions experienced populated shaking at MMI 6 or above.
      </div>
    );
  return (
    <div className="table-wrap compact-table">
      <table>
        <caption className="sr-only">
          Exposure at MMI 6 or above by region
        </caption>
        <thead>
          <tr>
            <th>Region</th>
            <th>Buildings</th>
            <th>Population</th>
            <th>Share of buildings</th>
          </tr>
        </thead>
        <tbody>
          {regions.map((region) => {
            const total = regions.reduce((sum, row) => sum + row.buildings, 0);
            const share = total ? (region.buildings / total) * 100 : 0;
            return (
              <tr key={region.region_code}>
                <th scope="row">{region.region_name}</th>
                <td>{formatInteger(region.buildings)}</td>
                <td>{formatInteger(region.population)}</td>
                <td>
                  <span className="share-bar">
                    <span style={{ width: `${share}%` }} />
                  </span>
                  <span className="share-label">{share.toFixed(1)}%</span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
