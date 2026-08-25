import { useEffect, useState } from 'react';
import Layout from '../components/Layout';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const ALL_CATEGORIES = [
  'restaurant', 'plumber', 'salon', 'dentist', 'landscaping',
  'retail', 'trades', 'professional', 'auto', 'cleaning',
  'gym', 'photography', 'realestate', 'childcare', 'petservices',
];

function Toast({ message, type }) {
  return <div className={`toast toast-${type}`}>{message}</div>;
}

export default function SettingsPage() {
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [dailyCap, setDailyCap] = useState('');
  const [toasts, setToasts] = useState([]);

  // Run pipeline form
  const [region, setRegion] = useState('');
  const [categories, setCategories] = useState([]);
  const [running, setRunning] = useState(false);

  const addToast = (message, type = 'success') => {
    const t = { id: Date.now(), message, type };
    setToasts(prev => [...prev, t]);
    setTimeout(() => setToasts(prev => prev.filter(x => x.id !== t.id)), 3500);
  };

  const loadSettings = async () => {
    try {
      const r = await fetch(`${API}/settings`);
      if (!r.ok) throw new Error(`API ${r.status}`);
      const d = await r.json();
      setSettings(d);
      setDailyCap(String(d.outreach_daily_cap));
    } catch (e) {
      addToast(`Failed to load settings: ${e.message}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadSettings(); }, []);

  const toggleReviewMode = async () => {
    const next = !settings.review_mode;
    setSaving(true);
    try {
      const r = await fetch(`${API}/settings`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ review_mode: next }),
      });
      if (!r.ok) throw new Error(`API ${r.status}`);
      const d = await r.json();
      setSettings(d);
      addToast(`Review mode ${next ? 'enabled' : 'disabled'}`);
    } catch (e) {
      addToast(e.message, 'error');
    } finally {
      setSaving(false);
    }
  };

  const saveDailyCap = async () => {
    const val = parseInt(dailyCap, 10);
    if (isNaN(val) || val < 1) { addToast('Daily cap must be a positive number', 'error'); return; }
    setSaving(true);
    try {
      const r = await fetch(`${API}/settings`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ outreach_daily_cap: val }),
      });
      if (!r.ok) throw new Error(`API ${r.status}`);
      const d = await r.json();
      setSettings(d);
      setDailyCap(String(d.outreach_daily_cap));
      addToast('Daily cap saved');
    } catch (e) {
      addToast(e.message, 'error');
    } finally {
      setSaving(false);
    }
  };

  const toggleCategory = (cat) => {
    setCategories(prev =>
      prev.includes(cat) ? prev.filter(c => c !== cat) : [...prev, cat]
    );
  };

  const runPipeline = async () => {
    if (!region.trim()) { addToast('Enter a region (e.g. "Austin, TX")', 'error'); return; }
    if (categories.length === 0) { addToast('Select at least one category', 'error'); return; }
    setRunning(true);
    try {
      const r = await fetch(`${API}/pipeline/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ region: region.trim(), categories }),
      });
      if (!r.ok) throw new Error(`API ${r.status}`);
      addToast(`Pipeline started for ${region} · ${categories.length} categories`);
      setRegion('');
      setCategories([]);
    } catch (e) {
      addToast(e.message, 'error');
    } finally {
      setRunning(false);
    }
  };

  return (
    <Layout title="Settings">
      {loading ? (
        <div className="loading-wrap"><div className="spinner" /></div>
      ) : (
        <div className="settings-grid">
          {/* Left: global settings */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>

            <div className="card">
              <div className="card-head">Pipeline Settings</div>
              <div className="card-body">
                <div className="toggle-row">
                  <div>
                    <div className="toggle-info-label">Review Mode</div>
                    <div className="toggle-info-sub">
                      When on, outreach is paused until you approve each site.
                    </div>
                  </div>
                  <label className="toggle">
                    <input
                      type="checkbox"
                      checked={settings?.review_mode ?? false}
                      onChange={toggleReviewMode}
                      disabled={saving}
                    />
                    <span className="toggle-track" />
                  </label>
                </div>

                <div style={{ paddingTop: '.875rem' }}>
                  <div className="field">
                    <label className="field-label" htmlFor="daily-cap">Daily Outreach Cap</label>
                    <div className="field-sub">Max emails / form fills per day across all businesses.</div>
                    <div style={{ display: 'flex', gap: '.5rem', marginTop: '.4rem' }}>
                      <input
                        id="daily-cap"
                        type="number"
                        min="1"
                        max="500"
                        className="field-input"
                        style={{ maxWidth: '120px' }}
                        value={dailyCap}
                        onChange={e => setDailyCap(e.target.value)}
                        onKeyDown={e => e.key === 'Enter' && saveDailyCap()}
                      />
                      <button className="btn btn-primary btn-sm" onClick={saveDailyCap} disabled={saving}>
                        Save
                      </button>
                    </div>
                  </div>
                </div>

                <div style={{ paddingTop: '.875rem' }}>
                  <div className="field">
                    <label className="field-label">Agency Domain</label>
                    <div className="field-sub">Set in AGENCY_DOMAIN env var. Restart to change.</div>
                    <input
                      className="field-input"
                      style={{ maxWidth: '280px', marginTop: '.4rem' }}
                      value={settings?.agency_domain || ''}
                      readOnly
                    />
                  </div>
                </div>
              </div>
            </div>

          </div>

          {/* Right: run pipeline */}
          <div className="card">
            <div className="card-head">Run Discovery</div>
            <div className="card-body">
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div className="field">
                  <label className="field-label" htmlFor="region">Region</label>
                  <div className="field-sub">City, state or general area to search.</div>
                  <input
                    id="region"
                    type="text"
                    className="field-input"
                    placeholder="e.g. Austin, TX"
                    value={region}
                    onChange={e => setRegion(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && runPipeline()}
                    style={{ marginTop: '.4rem' }}
                  />
                </div>

                <div className="field">
                  <div className="field-label">Categories</div>
                  <div className="field-sub" style={{ marginBottom: '.5rem' }}>
                    Select one or more verticals to discover ({categories.length} selected).
                  </div>
                  <div className="tag-group">
                    {ALL_CATEGORIES.map(cat => (
                      <button
                        key={cat}
                        className={`tag-btn${categories.includes(cat) ? ' selected' : ''}`}
                        onClick={() => toggleCategory(cat)}
                      >
                        {cat}
                      </button>
                    ))}
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '.5rem' }}>
                  <button
                    className="btn btn-primary"
                    onClick={runPipeline}
                    disabled={running}
                    style={{ flex: 1 }}
                  >
                    {running ? 'Starting…' : '▶ Run Pipeline'}
                  </button>
                  {categories.length > 0 && (
                    <button className="btn btn-ghost" onClick={() => setCategories([])}>
                      Clear
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="toast-stack">
        {toasts.map(t => <Toast key={t.id} {...t} />)}
      </div>
    </Layout>
  );
}
