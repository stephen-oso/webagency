import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import Layout from '../../components/Layout';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const STEPS = ['gather', 'build', 'publish', 'outreach'];

function jobDotClass(status) {
  if (!status || status === 'failed') return 'job-dot err';
  if (status === 'success' || status === 'done') return 'job-dot ok';
  return 'job-dot running';
}

function timeAgo(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  const diff = Math.floor((Date.now() - d) / 1000);
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return d.toLocaleDateString();
}

function Toast({ message, type }) {
  return <div className={`toast toast-${type}`}>{message}</div>;
}

export default function BusinessDetail() {
  const router = useRouter();
  const { id } = router.query;

  const [biz, setBiz] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [retryStep, setRetryStep] = useState('build');
  const [acting, setActing] = useState(false);
  const [toasts, setToasts] = useState([]);

  const addToast = (message, type = 'success') => {
    const t = { id: Date.now(), message, type };
    setToasts(prev => [...prev, t]);
    setTimeout(() => setToasts(prev => prev.filter(x => x.id !== t.id)), 3500);
  };

  const load = async () => {
    if (!id) return;
    try {
      const r = await fetch(`${API}/businesses/${id}`);
      if (!r.ok) throw new Error(`API ${r.status}`);
      setBiz(await r.json());
      setError(null);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [id]);

  const act = async (endpoint, method = 'POST', body) => {
    setActing(true);
    try {
      const r = await fetch(`${API}/businesses/${id}/${endpoint}`, {
        method,
        headers: body ? { 'Content-Type': 'application/json' } : undefined,
        body: body ? JSON.stringify(body) : undefined,
      });
      if (!r.ok) {
        const err = await r.json().catch(() => ({ detail: r.statusText }));
        throw new Error(err.detail || r.statusText);
      }
      addToast(`${endpoint.charAt(0).toUpperCase() + endpoint.slice(1)} successful`, 'success');
      await load();
    } catch (e) {
      addToast(e.message, 'error');
    } finally {
      setActing(false);
    }
  };

  const reviewStatus = biz?.site?.review_status;

  if (loading) return (
    <Layout title="Business">
      <div className="loading-wrap"><div className="spinner" /></div>
    </Layout>
  );

  if (error || !biz) return (
    <Layout title="Business">
      <div className="error-msg">Could not load business: {error}</div>
    </Layout>
  );

  const photos = biz.asset?.photos || [];
  const hours = biz.asset?.hours?.weekday_text || [];

  return (
    <Layout title={biz.name}>
      <Link href="/" className="detail-back">← Pipeline</Link>

      <div className="detail-header">
        <div>
          <div className="detail-title">{biz.name}</div>
          <div className="detail-meta">
            {biz.city}, {biz.state} · {biz.category}
            {biz.website_score != null && ` · Site score: ${biz.website_score}`}
          </div>
        </div>
        <div className="detail-actions">
          {biz.site && reviewStatus !== 'approved' && (
            <button
              className="btn btn-success"
              onClick={() => act('approve')}
              disabled={acting}
            >
              ✓ Approve
            </button>
          )}
          {biz.site && reviewStatus !== 'rejected' && (
            <button
              className="btn btn-danger"
              onClick={() => act('reject')}
              disabled={acting}
            >
              ✕ Reject
            </button>
          )}
          <div className="retry-row">
            <select
              className="step-select"
              value={retryStep}
              onChange={e => setRetryStep(e.target.value)}
            >
              {STEPS.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
            <button
              className="btn btn-ghost btn-sm"
              onClick={() => act('retry', 'POST', { step: retryStep })}
              disabled={acting}
            >
              ↻ Retry
            </button>
          </div>
        </div>
      </div>

      <div className="detail-grid">
        {/* Left column */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>

          {/* Photos */}
          <div className="card">
            <div className="card-head">
              Photos
              <span style={{ fontWeight: 400, textTransform: 'none', letterSpacing: 0 }}>
                {photos.length} available
              </span>
            </div>
            <div className="card-body">
              {photos.length > 0 ? (
                <div className="photo-grid">
                  {photos.slice(0, 8).map((src, i) => (
                    <img key={i} src={src} alt="" loading="lazy" />
                  ))}
                  {Array.from({ length: Math.max(0, 4 - (photos.slice(0, 8).length % 4 || 4)) }).map((_, i) => (
                    <div key={`ph-${i}`} className="photo-placeholder">No photo</div>
                  ))}
                </div>
              ) : (
                <div className="column-empty">No photos gathered yet</div>
              )}
            </div>
          </div>

          {/* Live site preview */}
          {biz.site?.vercel_url && (
            <div className="card">
              <div className="card-head">
                Live Site
                <div style={{ display: 'flex', alignItems: 'center', gap: '.5rem' }}>
                  {reviewStatus && (
                    <span className={`badge badge-${reviewStatus}`}>{reviewStatus}</span>
                  )}
                  <a href={biz.site.vercel_url} target="_blank" rel="noopener noreferrer"
                    className="btn btn-ghost btn-sm">
                    ↗ Open
                  </a>
                </div>
              </div>
              <div className="card-body">
                <a href={biz.site.vercel_url} target="_blank" rel="noopener noreferrer"
                  className="preview-url">
                  {biz.site.vercel_url}
                </a>
                <iframe
                  src={biz.site.vercel_url}
                  className="preview-frame"
                  title="Site preview"
                  sandbox="allow-scripts allow-same-origin"
                />
              </div>
            </div>
          )}

          {/* Jobs log */}
          {biz.recent_jobs?.length > 0 && (
            <div className="card">
              <div className="card-head">Recent Jobs</div>
              <div className="card-body">
                {biz.recent_jobs.map(job => (
                  <div key={job.id} className="job-row">
                    <div className={jobDotClass(job.status)} />
                    <div style={{ flex: 1 }}>
                      <div className="job-step">{job.step} <span style={{ fontWeight: 400, color: 'var(--muted)', fontSize: '.75rem' }}>({job.status})</span></div>
                      <div className="job-time">{timeAgo(job.last_run_at)}</div>
                      {job.error_msg && <div className="job-err">{job.error_msg}</div>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right column */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>

          {/* Business info */}
          <div className="card">
            <div className="card-head">Business Info</div>
            <div className="card-body">
              {[
                ['Status', biz.status],
                ['Address', biz.address],
                ['Phone', biz.phone],
                ['Email', biz.email],
                ['Existing site', biz.existing_website],
                ['Rating', biz.asset?.rating ? `★ ${biz.asset.rating} (${biz.asset.review_count?.toLocaleString()} reviews)` : null],
                ['Price range', biz.asset?.price_range],
                ['Template', biz.site?.template_used],
              ].filter(([, v]) => v).map(([label, value]) => (
                <div key={label} className="info-row">
                  <span className="info-label">{label}</span>
                  <span className="info-value">{value}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Hours */}
          {hours.length > 0 && (
            <div className="card">
              <div className="card-head">Hours</div>
              <div className="card-body">
                {hours.map((h, i) => (
                  <div key={i} style={{ fontSize: '.78rem', lineHeight: '1.9', color: 'var(--muted)' }}>{h}</div>
                ))}
              </div>
            </div>
          )}

          {/* Outreach */}
          {biz.outreach && (
            <div className="card">
              <div className="card-head">Outreach</div>
              <div className="card-body">
                {[
                  ['To', biz.outreach.email_to],
                  ['Email', biz.outreach.email_status],
                  ['Form', biz.outreach.form_status],
                ].filter(([, v]) => v).map(([label, value]) => (
                  <div key={label} className="info-row">
                    <span className="info-label">{label}</span>
                    <span className="info-value">{value}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Services */}
          {biz.asset?.services?.length > 0 && (
            <div className="card">
              <div className="card-head">Services</div>
              <div className="card-body">
                {biz.asset.services.map((s, i) => (
                  <div key={i} style={{ fontSize: '.82rem', padding: '.25rem 0', borderBottom: i < biz.asset.services.length - 1 ? '1px solid var(--border)' : 'none', color: 'var(--text)' }}>{s}</div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="toast-stack">
        {toasts.map(t => <Toast key={t.id} {...t} />)}
      </div>
    </Layout>
  );
}
