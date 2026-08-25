import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/router';
import Layout from '../components/Layout';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const ALL_CATEGORIES = [
  'restaurant', 'plumber', 'salon', 'dentist', 'landscaping',
  'retail', 'trades', 'professional', 'auto', 'cleaning',
  'gym', 'photography', 'realestate', 'childcare', 'petservices',
];

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

  // Rescan modal
  const [scanOpen, setScanOpen] = useState(false);
  const [scanRegion, setScanRegion] = useState('');
  const [scanCategories, setScanCategories] = useState([]);
  const [scanning, setScanning] = useState(false);
  const [scanMsg, setScanMsg] = useState(null);

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

  // Re-fetch immediately when tab becomes visible (mobile browsers throttle intervals in background)
  useEffect(() => {
    const onVisible = () => { if (document.visibilityState === 'visible') load(); };
    document.addEventListener('visibilitychange', onVisible);
    return () => document.removeEventListener('visibilitychange', onVisible);
  }, [load]);

  const toggleScanCat = (cat) =>
    setScanCategories(prev => prev.includes(cat) ? prev.filter(c => c !== cat) : [...prev, cat]);

  const runScan = async () => {
    if (!scanRegion.trim() || scanCategories.length === 0) return;
    setScanning(true);
    setScanMsg(null);
    try {
      const r = await fetch(`${API}/pipeline/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ region: scanRegion.trim(), categories: scanCategories }),
      });
      if (!r.ok) throw new Error(`API ${r.status}`);
      setScanMsg({ type: 'ok', text: `Pipeline started for ${scanRegion} · ${scanCategories.length} categories` });
      setScanRegion('');
      setScanCategories([]);
      setTimeout(() => { setScanOpen(false); setScanMsg(null); }, 1800);
    } catch (e) {
      setScanMsg({ type: 'err', text: e.message });
    } finally {
      setScanning(false);
    }
  };

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
        <div style={{ display: 'flex', gap: '.5rem' }}>
          <button className="btn btn-ghost btn-sm" onClick={load} disabled={loading}>
            ↻ Refresh
          </button>
          <button className="btn btn-primary btn-sm" onClick={() => setScanOpen(true)}>
            + Scan
          </button>
        </div>
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

      {scanOpen && (
        <div className="modal-overlay" onClick={() => setScanOpen(false)}>
          <div className="modal-sheet" onClick={e => e.stopPropagation()}>
            <div className="modal-head">
              <span>Run Discovery</span>
              <button className="modal-close" onClick={() => setScanOpen(false)}>✕</button>
            </div>
            <div className="modal-body">
              <div className="field">
                <label className="field-label" htmlFor="scan-region">Region</label>
                <input
                  id="scan-region"
                  className="field-input"
                  placeholder="e.g. Austin, TX"
                  value={scanRegion}
                  onChange={e => setScanRegion(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && runScan()}
                  autoFocus
                />
              </div>
              <div className="field" style={{ marginTop: '1rem' }}>
                <div className="field-label">Categories ({scanCategories.length} selected)</div>
                <div className="tag-group" style={{ marginTop: '.5rem' }}>
                  {ALL_CATEGORIES.map(cat => (
                    <button
                      key={cat}
                      className={`tag-btn${scanCategories.includes(cat) ? ' selected' : ''}`}
                      onClick={() => toggleScanCat(cat)}
                    >
                      {cat}
                    </button>
                  ))}
                </div>
              </div>
              {scanMsg && (
                <div className={scanMsg.type === 'ok' ? 'scan-msg-ok' : 'scan-msg-err'}>
                  {scanMsg.text}
                </div>
              )}
              <button
                className="btn btn-primary"
                style={{ width: '100%', marginTop: '1.25rem' }}
                onClick={runScan}
                disabled={scanning || !scanRegion.trim() || scanCategories.length === 0}
              >
                {scanning ? 'Starting…' : '▶ Run Pipeline'}
              </button>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
}
