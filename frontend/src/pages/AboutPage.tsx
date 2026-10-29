import { ExternalLink, FileText, GitBranch, Layers3 } from "lucide-react";

export default function AboutPage() {
  return (
    <div className="page-container editorial-page about-page">
      <header className="page-lead">
        <h1>One exposure engine, two deployment targets</h1>
        <p>
          NZ Hazard Exposure Monitor turns public earthquake, building and
          population data into an analyst-ready exposure record. The local
          Docker product is operational; Azure remains the primary production
          target and has not yet been deployed.
        </p>
      </header>

      <section
        className="architecture-section"
        aria-labelledby="architecture-heading"
      >
        <div className="section-heading">
          <h2 id="architecture-heading">System architecture</h2>
        </div>
        <div
          className="architecture-flow"
          role="img"
          aria-label="System architecture from public sources through one shared core to local and Azure deployments"
        >
          <div className="architecture-sources">
            <span>GeoNet events + shaking</span>
            <span>LINZ buildings</span>
            <span>Stats NZ population</span>
          </div>
          <div className="flow-line" aria-hidden="true" />
          <div className="architecture-core">
            <strong>Shared Python core</strong>
            <span>H3 exposure · DuckDB/dbt · briefing approval</span>
          </div>
          <div className="flow-split" aria-hidden="true" />
          <div className="deployment-lanes">
            <div>
              <strong>Local · operational</strong>
              <span>FastAPI + APScheduler</span>
              <span>SQLite + volume storage</span>
              <span>Caddy + Mailpit</span>
            </div>
            <div>
              <strong>Azure · planned</strong>
              <span>Functions Flex Consumption</span>
              <span>Storage + Key Vault</span>
              <span>Application Insights</span>
            </div>
          </div>
          <div className="flow-line" aria-hidden="true" />
          <div className="architecture-output">
            Static website · exposure maps · approved analyst briefings
          </div>
        </div>
      </section>

      <section
        className="technology-register"
        aria-labelledby="technology-heading"
      >
        <div className="section-heading">
          <h2 id="technology-heading">Technology register</h2>
        </div>
        <dl>
          <div>
            <dt>Spatial and data</dt>
            <dd>Python, DuckDB, dbt, H3, GeoParquet</dd>
          </div>
          <div>
            <dt>Product website</dt>
            <dd>React, TypeScript, Vite, Recharts, ArcGIS Maps SDK</dd>
          </div>
          <div>
            <dt>Local operations</dt>
            <dd>
              Docker Compose, FastAPI, APScheduler, SQLite, Caddy, Mailpit
            </dd>
          </div>
          <div>
            <dt>Quality controls</dt>
            <dd>
              Pytest, Vitest, Playwright, Ruff, ESLint, Terraform validation
            </dd>
          </div>
        </dl>
      </section>

      <section className="project-links" aria-labelledby="links-heading">
        <div className="section-heading">
          <h2 id="links-heading">Project records</h2>
        </div>
        <a
          href="https://github.com/liyang6620/nz-hazard-exposure-monitor"
          rel="noreferrer"
        >
          <GitBranch aria-hidden="true" />
          <span>
            <strong>Source and evidence</strong>
            GitHub repository, tests and milestone records
          </span>
          <ExternalLink aria-hidden="true" />
        </a>
        <a
          href="https://github.com/liyang6620/nz-hazard-exposure-monitor/raw/main/evidence/m5/nzhem-powerbi-report.pdf"
          rel="noreferrer"
        >
          <FileText aria-hidden="true" />
          <span>
            <strong>Power BI report</strong>
            Five-page analyst report exported from Power BI Desktop
          </span>
          <ExternalLink aria-hidden="true" />
        </a>
        <a
          href="https://www.arcgis.com/home/item.html?id=ce9c69b085584965a236d0c6fdfb7ebc"
          rel="noreferrer"
        >
          <Layers3 aria-hidden="true" />
          <span>
            <strong>ArcGIS hosted layer</strong>
            Private event_exposure_r6 layer · 4,011 features · sign-in required
          </span>
          <ExternalLink aria-hidden="true" />
        </a>
      </section>
    </div>
  );
}
