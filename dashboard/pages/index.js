import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/router';
import Layout from '../components/Layout';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const COLUMNS = [
  {
    id: 'discovered',
    label: 'Discovered',
    match: s => s === 'discovered',
    badgeClass: 'badge-discovered',
  },
  {
    id: 'processing',
    label: 'Processing',
    match: s => ['gathering', 'gathered', 'building', 'built', 'publishing'].includes(s),
    badgeClass: 'badge-processing',
  },
  {
    id: 'published',
    label: 'Published',
    match: s => s === 'published',
    badgeClass: 'badge-published',
  },
  {
    id: 'outreach',
    label: 'Outreach',
    match: s => s === 'outreaching' || s === 'outreached',
    badgeClass: 'badge-outreach',
  },
  {
    id: 'failed',
    label: 'Failed',
    match: s => s?.endsWith('_failed') || s === 'error',
    badgeClass: 'badge-failed',
  },
];

function scorePillClass(score) {
  if (score == null) return '';
  if (score >= 70) return 'score-pill';
  if (score >= 40) return 'score-pill mid';
  return 'score-pill low';
}

function BizCard({ biz, onClick }) {
  return (
    <div className="biz-card" onClick={onClick} role="button" tabIndex={0}
      onKeyDown={e => e.key === 'Enter' && onClick()}>
      <div className="biz-card-name">{biz.name}</div>
      <div className="biz-card-meta">{biz.city}, {biz.state} · {biz.category}</div>
      <div className="biz-card-footer">
        <span className="biz-card-status">{biz.status}</span>
        {biz.website_score != null && (
          <span className={scorePillClass(biz.website_score)}>{biz.website_score}</span>
        )}
      </div>
    </div>
  );
}

export default function PipelinePage() {
  const router = useRouter();
  const [businesses, setBusinesses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastRefresh, setLastRefresh] = useState(null);

  const load = useCallback(async () => {
    try {
      const r = await fetch(`${API}/businesses?limit=200`);
      if (!r.ok) throw new Error(`API ${r.status}`);
      const data = await r.json();
      setBusinesses(data);
      setLastRefresh(new Date());
      setError(null);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(load, 10_000);
    return () => clearInterval(t);
  }, [load]);

  const grouped = COLUMNS.map(col => ({
    ...col,
    items: businesses.filter(b => col.match(b.status)),
  }));

  const total = businesses.length;
  const outreached = businesses.filter(b => b.status === 'outreached').length;

  return (
    <Layout title="Pipeline">
      <div className="toolbar">
        <div className="toolbar-left">
          <span className="toolbar-stat">
            <strong>{total}</strong> total · <strong>{outreached}</strong> outreached
          </span>
          {lastRefresh && (
            <span className="toolbar-stat">
              Updated {lastRefresh.toLocaleTimeString()}
            </span>
          )}
        </div>
        <button className="btn btn-ghost btn-sm" onClick={load} disabled={loading}>
          ↻ Refresh
        </button>
      </div>

      {error && <div className="error-msg" style={{ marginBottom: '1rem' }}>Cannot reach API: {error}</div>}

      {loading && businesses.length === 0 ? (
        <div className="loading-wrap"><div className="spinner" /></div>
      ) : (
        <div className="kanban">
          {grouped.map(col => (
            <div key={col.id} className="column">
              <div className="column-head">
                <span className="column-label">{col.label}</span>
                <span className="column-count">{col.items.length}</span>
              </div>
              <div className="column-body">
                {col.items.length === 0 ? (
                  <div className="column-empty">—</div>
                ) : (
                  col.items.map(biz => (
                    <BizCard
                      key={biz.id}
                      biz={biz}
                      onClick={() => router.push(`/business/${biz.id}`)}
                    />
                  ))
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </Layout>
  );
}
