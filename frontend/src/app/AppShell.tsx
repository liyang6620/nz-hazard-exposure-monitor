import { GitBranch, Menu, X } from "lucide-react";
import { useState, type ReactNode } from "react";
import { Link, NavLink } from "react-router-dom";

import { EarthquakeTicker } from "../components/EarthquakeTicker";
import { useSiteData } from "./SiteDataContext";

export function AppShell({ children }: { children: ReactNode }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const { data } = useSiteData();
  const recentEvents =
    data?.events.filter((event) => event.is_recent_monitoring).slice(0, 8) ??
    [];
  return (
    <div className="app-shell">
      <EarthquakeTicker events={recentEvents} />
      <header className="site-header">
        <div className="header-inner">
          <Link
            className="brand"
            to="/"
            aria-label="NZ Hazard Exposure Monitor home"
          >
            <span>
              <strong>NZ Hazard Exposure Monitor</strong>
              <small>Earthquake exposure record</small>
            </span>
          </Link>
          <button
            className="icon-button menu-button"
            type="button"
            aria-label={menuOpen ? "Close navigation" : "Open navigation"}
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((open) => !open)}
          >
            {menuOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
          <nav
            className={menuOpen ? "site-nav open" : "site-nav"}
            aria-label="Primary navigation"
          >
            <NavLink to="/" onClick={() => setMenuOpen(false)}>
              Latest
            </NavLink>
          </nav>
        </div>
      </header>
      <main id="main-content">{children}</main>
      <footer className="site-footer">
        <div className="footer-inner">
          <div>
            <strong>NZ Hazard Exposure Monitor</strong>
            <p>
              Buildings and population exposed to New Zealand earthquake
              shaking.
            </p>
          </div>
          <a
            href="https://github.com/liyang6620/nz-hazard-exposure-monitor"
            rel="noreferrer"
          >
            <GitBranch size={17} aria-hidden="true" /> GitHub
          </a>
        </div>
      </footer>
    </div>
  );
}
