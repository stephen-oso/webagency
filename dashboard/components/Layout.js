import { useRouter } from 'next/router';
import Link from 'next/link';
import { useEffect, useState } from 'react';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function Layout({ title, children }) {
  const router = useRouter();
  const [reviewMode, setReviewMode] = useState(false);

  useEffect(() => {
    fetch(`${API}/settings`)
      .then(r => r.ok ? r.json() : null)
      .then(d => d && setReviewMode(d.review_mode))
      .catch(() => {});
  }, []);

  const links = [
    { href: '/', icon: '⬡', label: 'Pipeline' },
    { href: '/settings', icon: '⚙', label: 'Settings' },
  ];

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="sidebar-brand-name">Agency OS</div>
          <div className="sidebar-brand-sub">Lead Pipeline</div>
        </div>
        <nav className="sidebar-nav">
          {links.map(({ href, icon, label }) => (
            <Link
              key={href}
              href={href}
              className={`nav-link${router.pathname === href ? ' active' : ''}`}
            >
              <span className="nav-icon">{icon}</span>
              {label}
            </Link>
          ))}
        </nav>
        <div className="sidebar-footer">Agency Dashboard v1</div>
      </aside>

      <div className="main">
        <header className="topbar">
          <span className="topbar-title">{title}</span>
          <div className="topbar-right">
            {reviewMode && (
              <div className="review-badge">
                <span className="review-dot" />
                Review Mode On
              </div>
            )}
          </div>
        </header>
        <main className="content">{children}</main>
      </div>
    </div>
  );
}
