import { ExternalLink } from "lucide-react";

export default function MethodologyPage() {
  return (
    <div className="page-container editorial-page method-page">
      <header className="page-lead">
        <h1>Method and data</h1>
        <p>
          Exposure means buildings and people inside mapped shaking. It is not
          insured loss, structural damage or a forecast of claims.
        </p>
      </header>

      <section className="method-register" aria-labelledby="sources-heading">
        <div className="method-index">
          <span className="mono">01</span>
          <h2 id="sources-heading">Source register</h2>
        </div>
        <div className="method-copy">
          <dl className="source-register">
            <div>
              <dt>Earthquakes</dt>
              <dd>
                GeoNet FDSN event feed, polled hourly with{" "}
                <code>updatedafter</code> catch-up after an outage.
              </dd>
            </div>
            <div>
              <dt>Shaking</dt>
              <dd>
                Earth Sciences New Zealand Shaking Layers. Each event records
                its reviewed or automatic source timestamp.
              </dd>
            </div>
            <div>
              <dt>Buildings</dt>
              <dd>
                Toitū Te Whenua LINZ Building Outlines, layer version 438679;
                full GeoPackage export downloaded 24 Oct 2026. The export
                contains 6,634,223 current and historical rows.
              </dd>
            </div>
            <div>
              <dt>Population</dt>
              <dd>
                Stats NZ 2023 Census usually resident population, SA1 variable
                VAR_1_3.
              </dd>
            </div>
          </dl>
        </div>
      </section>

      <section className="method-register" aria-labelledby="grid-heading">
        <div className="method-index">
          <span className="mono">02</span>
          <h2 id="grid-heading">H3 exposure grid</h2>
        </div>
        <div className="method-copy">
          <p>
            Building polygons are reduced to a point on surface in NZTM2000,
            transformed to WGS84, then assigned to H3 resolution 8. Population
            is allocated within each SA1 in proportion to current building
            footprint. Presentation aggregates to H3 resolution 6 for compact
            maps.
          </p>
          <p>
            A building or person is counted as exposed when its populated H3
            cell reaches the reporting threshold. The product uses MMI 6 as the
            damaging shaking threshold and retains each lower and higher MMI
            band separately.
          </p>
        </div>
      </section>

      <section className="method-register" aria-labelledby="shaking-heading">
        <div className="method-index">
          <span className="mono">03</span>
          <h2 id="shaking-heading">Official and preliminary shaking</h2>
        </div>
        <div className="method-copy">
          <p>
            A reviewed official Shaking Layer is preferred, followed by an
            automatic official layer. If neither exists, the event may use a
            preliminary Dowrick–Rhoades point-source estimate within the
            published model range. Events of M6.5 or above using that
            approximation are explicitly marked.
          </p>
          <p>
            The deep-source model is selected at 70 km depth. The TVZ and
            subduction interface branches are not used because the project has
            no suitable licensed boundary or slab classification. Magnitudes
            outside the paper’s calibration range are not extrapolated.
          </p>
        </div>
      </section>

      <section className="method-register" aria-labelledby="basis-heading">
        <div className="method-index">
          <span className="mono">04</span>
          <h2 id="basis-heading">As-if-today replays</h2>
        </div>
        <div className="method-copy">
          <p>
            The ten fixed replays answer a current portfolio question: what
            would be exposed if the recorded shaking happened against today’s
            mapped building stock and 2023 population? They do not reconstruct
            the assets or population present on the historical event date.
          </p>
          <p>
            This common baseline makes events comparable. Every replay is
            labelled “as-if-today” on the overview, event record and approved
            briefing.
          </p>
        </div>
      </section>

      <section
        className="limitations-ledger"
        aria-labelledby="limitations-heading"
      >
        <div className="section-heading">
          <h2 id="limitations-heading">Known limitations</h2>
          <span className="updated">Current assessment record</span>
        </div>
        <ul>
          <li>
            Station validation MAE is 1.049 MMI. Coefficients were not tuned to
            hide that result.
          </li>
          <li>
            21,483 building outlines assigned to water meshblocks remain
            excluded.
          </li>
          <li>
            Population coverage excludes the Chatham Islands because no
            compatible source record is available in this build.
          </li>
          <li>
            SA1 population allocation is spatially coarse, and Stats NZ applies
            confidentiality treatment to small-area counts.
          </li>
          <li>
            Exposure is a screening measure. It does not include policy terms,
            vulnerability, damage, loss or business interruption.
          </li>
        </ul>
      </section>

      <p className="reference-link">
        <a
          href="https://github.com/liyang6620/nz-hazard-exposure-monitor/blob/main/docs/methodology.md"
          rel="noreferrer"
        >
          Read the equations, test vectors and source citations on GitHub
          <ExternalLink size={16} aria-hidden="true" />
        </a>
      </p>
    </div>
  );
}
