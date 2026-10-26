import { Activity, GitBranch, Menu, X } from "lucide-react";
import { useState, type ReactNode } from "react";
import { Link, NavLink } from "react-router-dom";

export function AppShell({ children }: { children: ReactNode }) {
  const [menuOpen, setMenuOpen] = useState(false);
  return (
    <div className="app-shell">
      <header className="site-header">
        <div className="header-inner">
          <Link
            className="brand"
            to="/"
            aria-label="NZ Hazard Exposure Monitor home"
          >
            <span className="brand-mark" aria-hidden="true">
              <Activity size={20} />
            </span>
            <span>
              <strong>NZ Hazard</strong>
              <small>Exposure Monitor</small>
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
              Overview
            </NavLink>
          </nav>
        </div>
      </header>
      <main id="main-content">{children}</main>
      <footer className="site-footer">
        <div className="footer-inner">
          <div>
            <strong>NZ Hazard Exposure Monitor</strong>
            <p>Decision support for earthquake exposure analysis.</p>
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
