"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { TraceReadyLogo } from "./TraceReadyLogo";

interface AppShellFrameProps {
  children: React.ReactNode;
  initialNavCollapsed?: boolean;
  links: Array<{ href: string; label: string; section?: string }>;
  profile?: {
    email: string;
    fullName?: string;
    companyName?: string;
    role: string;
  };
}

export function AppShellFrame({ children, initialNavCollapsed = false, links, profile }: AppShellFrameProps) {
  const [collapsed, setCollapsed] = useState(initialNavCollapsed);
  const [profileMenuOpen, setProfileMenuOpen] = useState(false);
  const profileMenuRef = useRef<HTMLDivElement>(null);
  const pathname = usePathname();
  const initials = profile?.email.slice(0, 1).toUpperCase() ?? "T";
  const profileTitle = profile?.fullName ?? profile?.email ?? profile?.role ?? "Workspace";
  const profileMeta = profile?.companyName ?? profile?.email ?? profile?.role;
  const workspaceBase = profile?.role === "Consultant Reviewer" || profile?.role === "Founder Admin" ? "/reviewer" : "/operator";
  const primaryLinks = links.filter((link) => !link.section);
  const sectionNames = [...new Set(links.filter((link) => link.section).map((link) => link.section as string))];
  const workspaceClass =
    profile?.role === "Consultant Reviewer"
      ? "reviewer-shell"
      : profile?.role === "Founder Admin"
        ? "admin-shell"
        : "operator-shell";
  const currentLink = [...links]
    .filter(({ href }) => !href.includes("#"))
    .sort((a, b) => b.href.length - a.href.length)
    .find(({ href }) => pathname === href || (href !== "/operator" && href !== "/reviewer" && pathname.startsWith(`${href}/`)));

  function toggleNavigation() {
    setCollapsed((value) => {
      const next = !value;
      document.cookie = `traceready_nav_collapsed=${next ? "true" : "false"}; path=/; max-age=31536000; SameSite=Lax`;
      return next;
    });
  }

  useEffect(() => {
    function handlePointerDown(event: PointerEvent) {
      if (!profileMenuRef.current?.contains(event.target as Node)) {
        setProfileMenuOpen(false);
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setProfileMenuOpen(false);
      }
    }

    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, []);

  return (
    <div className={`shell ${workspaceClass} ${collapsed ? "nav-collapsed" : ""}`}>
      <aside className="nav" aria-label="Workspace navigation">
        <div className="nav-top">
          <button
            aria-label={collapsed ? "Open navigation" : "Collapse navigation"}
            className="nav-collapse-row top"
            onClick={toggleNavigation}
            type="button"
          >
            <MenuIcon />
          </button>
        </div>

        <div className="nav-scroll">
          {primaryLinks.length ? (
            <nav className="nav-links" aria-label="Main navigation">
              {primaryLinks.map(({ href, label }) => {
                const isActive = currentLink?.href === href;

                return (
                  <Link aria-current={isActive ? "page" : undefined} className={isActive ? "active" : ""} href={href} key={`${href}-${label}`} title={label}>
                    <NavIcon label={label} />
                    <span className="nav-label">{label}</span>
                  </Link>
                );
              })}
            </nav>
          ) : null}

          {sectionNames.map((sectionName) => {
            const sectionLinks = links.filter((link) => link.section === sectionName);
            return (
              <nav className={`nav-admin-links nav-section-${sectionName}`} aria-label={`${sectionLabel(sectionName)} navigation`} key={sectionName}>
                <span className="nav-section-label">{sectionLabel(sectionName)}</span>
                {sectionLinks.map(({ href, label }) => {
                  const isActive = currentLink?.href === href;

                  return (
                    <Link aria-current={isActive ? "page" : undefined} className={isActive ? "active" : ""} href={href} key={`${href}-${label}`} title={label}>
                      <NavIcon label={label} />
                      <span className="nav-label">{label}</span>
                    </Link>
                  );
                })}
              </nav>
            );
          })}
        </div>

        <nav className="nav-utilities" aria-label="Workspace utilities">
          <Link href={`${workspaceBase}/notifications`}>
            <UtilityIcon name="notifications" />
            <span>Notifications</span>
          </Link>
          <Link href={`${workspaceBase}/help`}>
            <UtilityIcon name="help" />
            <span>Help</span>
          </Link>
        </nav>
      </aside>
      <main className="main">
        <header className="app-topbar">
          <div className="topbar-left">
            <Link className="topbar-brand" href={workspaceBase}>
              <TraceReadyLogo linked={false} showText={false} />
              <strong>TraceReady</strong>
            </Link>
          </div>
          <div className="topbar-profile-menu" ref={profileMenuRef}>
            <button
              aria-expanded={profileMenuOpen}
              aria-haspopup="menu"
              className="topbar-profile profile-menu-button"
              onClick={() => setProfileMenuOpen((value) => !value)}
              type="button"
            >
              <div className="profile-avatar" aria-hidden="true">
                {initials}
              </div>
              <div className="profile-copy">
                <strong>{profileTitle}</strong>
                {profileMeta ? <span>{profileMeta}</span> : null}
              </div>
              <ChevronIcon />
            </button>
            <div className={`profile-dropdown ${profileMenuOpen ? "open" : ""}`} role="menu">
              <div className="profile-dropdown-header">
                <div className="profile-avatar" aria-hidden="true">
                  {initials}
                </div>
                <div>
                  <strong>{profileTitle}</strong>
                  {profileMeta ? <span>{profileMeta}</span> : null}
                </div>
              </div>
              <Link className="profile-dropdown-link" href={`${workspaceBase}#settings`} onClick={() => setProfileMenuOpen(false)} role="menuitem">
                <UtilityIcon name="settings" />
                <span>Settings</span>
              </Link>
              <Link className="profile-dropdown-link danger" href="/logout" onClick={() => setProfileMenuOpen(false)} role="menuitem">
                <UtilityIcon name="signout" />
                <span>Sign out</span>
              </Link>
            </div>
          </div>
        </header>
        <div className="main-content">{children}</div>
      </main>
    </div>
  );
}

function ChevronIcon() {
  return (
    <svg className="profile-chevron-icon" viewBox="0 0 20 20" aria-hidden="true">
      <path d="m5 7.5 5 5 5-5" />
    </svg>
  );
}

function MenuIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M5 7h14" />
      <path d="M5 12h14" />
      <path d="M5 17h14" />
    </svg>
  );
}

function NavIcon({ label }: { label: string }) {
  const normalized = label.toLowerCase();
  if (normalized.includes("upload")) return <UtilityIcon name="upload" />;
  if (normalized.includes("audit") || normalized.includes("review") || normalized.includes("finding") || normalized.includes("gate")) return <UtilityIcon name="shield" />;
  if (normalized.includes("report") || normalized.includes("source") || normalized.includes("citation") || normalized.includes("rule") || normalized.includes("kde")) return <UtilityIcon name="document" />;
  if (normalized.includes("setting") || normalized.includes("version") || normalized.includes("coverage")) return <UtilityIcon name="settings" />;
  return <UtilityIcon name="home" />;
}

function sectionLabel(sectionName: string) {
  if (sectionName === "review") return "Review";
  if (sectionName === "library") return "Library";
  if (sectionName === "tools") return "Tools";
  if (sectionName === "admin") return "Admin";
  return sectionName;
}

function UtilityIcon({ name }: { name: string }) {
  return (
    <span className="nav-icon" aria-hidden="true">
      <svg viewBox="0 0 24 24">
        {name === "home" ? (
          <>
            <path d="M3 11.5 12 4l9 7.5" />
            <path d="M5.5 10.5V20h13v-9.5" />
            <path d="M9.5 20v-6h5v6" />
          </>
        ) : null}
        {name === "upload" ? (
          <>
            <path d="M12 16V4" />
            <path d="m7 9 5-5 5 5" />
            <path d="M4 16v3h16v-3" />
          </>
        ) : null}
        {name === "shield" ? (
          <>
            <path d="M12 3 20 7v5c0 5-3.5 8-8 9-4.5-1-8-4-8-9V7l8-4Z" />
            <path d="m8.5 12 2.4 2.4 4.8-5" />
          </>
        ) : null}
        {name === "document" ? (
          <>
            <path d="M7 3h7l4 4v14H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Z" />
            <path d="M14 3v5h5" />
            <path d="M8.5 13h7" />
            <path d="M8.5 17h5" />
          </>
        ) : null}
        {name === "settings" ? (
          <>
            <path d="M12 8.5a3.5 3.5 0 1 1 0 7 3.5 3.5 0 0 1 0-7Z" />
            <path d="M19 12a7.7 7.7 0 0 0-.1-1l2-1.5-2-3.5-2.4 1a7.7 7.7 0 0 0-1.8-1L14.4 3h-4.8L9.2 6a7.7 7.7 0 0 0-1.8 1L5 6l-2 3.5L5 11a7.7 7.7 0 0 0 0 2l-2 1.5L5 18l2.4-1a7.7 7.7 0 0 0 1.8 1l.4 3h4.8l.4-3a7.7 7.7 0 0 0 1.8-1l2.4 1 2-3.5-2-1.5c.1-.3.1-.7.1-1Z" />
          </>
        ) : null}
        {name === "notifications" ? (
          <>
            <path d="M18 9a6 6 0 0 0-12 0c0 7-3 7-3 7h18s-3 0-3-7" />
            <path d="M10 20a2 2 0 0 0 4 0" />
          </>
        ) : null}
        {name === "help" ? (
          <>
            <circle cx="12" cy="12" r="9" />
            <path d="M9.7 9a2.4 2.4 0 0 1 4.6 1.1c0 1.7-2.3 2.1-2.3 3.7" />
            <path d="M12 17h.01" />
          </>
        ) : null}
        {name === "signout" ? (
          <>
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
            <path d="M16 17l5-5-5-5" />
            <path d="M21 12H9" />
          </>
        ) : null}
      </svg>
    </span>
  );
}
