import Head from 'next/head';

export default function Page({ data }) {
  const { copy = {}, photos = [], business_data = {} } = data || {};
  const hero = photos[0] || null;
  const gallery = photos.slice(1, 7);
  const hours = business_data.hours?.weekday_text || [];
  const badges = ['Licensed & Insured', '24/7 Emergency', 'Free Estimates', 'Satisfaction Guaranteed'];

  return (
    <>
      <Head>
        <title>{business_data.name || 'Plumbing Services'}</title>
        <meta name="description" content={copy.meta_description || ''} />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Anton&family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,700&display=swap" rel="stylesheet" />
      </Head>

      <div className="emergency-bar">
        <span>24/7 Emergency Service Available</span>
        {business_data.phone && (
          <a href={`tel:${business_data.phone}`} className="emergency-phone">Call Now: {business_data.phone}</a>
        )}
      </div>

      <nav className="nav">
        <div className="nav-inner">
          <span className="nav-brand">{business_data.name}</span>
          <a href="#contact" className="nav-cta">{copy.cta_text || 'Get Free Quote'}</a>
        </div>
      </nav>

      <section className="hero" style={hero ? { backgroundImage: `url(${hero})` } : {}}>
        <div className="hero-veil" />
        <div className="hero-body">
          <div className="trust-pill">Licensed & Insured · {business_data.city}, {business_data.state}</div>
          <h1>{copy.headline}</h1>
          <p className="hero-sub">{copy.subheadline}</p>
          <div className="hero-actions">
            <a href="#contact" className="btn-primary">{copy.cta_text || 'Get Free Estimate'}</a>
            {business_data.phone && (
              <a href={`tel:${business_data.phone}`} className="btn-outline">{business_data.phone}</a>
            )}
          </div>
        </div>
      </section>

      <section className="trust-bar">
        <div className="wrap trust-grid">
          {badges.map((b, i) => (
            <div key={i} className="trust-badge">
              <div className="badge-check">✓</div>
              <span>{b}</span>
            </div>
          ))}
        </div>
      </section>

      {copy.services?.length > 0 && (
        <section className="services">
          <div className="wrap">
            <span className="section-tag">Our Services</span>
            <h2>What We Fix</h2>
            <div className="services-grid">
              {copy.services.map((s, i) => (
                <div key={i} className="service-card">
                  <span className="service-icon">⚙</span>
                  <span>{s}</span>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      <section className="about">
        <div className="wrap">
          <span className="section-tag">About Us</span>
          <p className="about-copy">{copy.about}</p>
        </div>
      </section>

      {gallery.length > 0 && (
        <section className="gallery">
          {gallery.map((src, i) => (
            <div key={i} className="gallery-cell">
              <img src={src} alt="" loading="lazy" />
            </div>
          ))}
        </section>
      )}

      <section className="info" id="contact">
        <div className="wrap">
          <h2>Get In Touch</h2>
          <div className="info-grid">
            <div>
              <span className="section-tag">Location</span>
              <p>{business_data.city}, {business_data.state}</p>
            </div>
            {business_data.phone && (
              <div>
                <span className="section-tag">Phone</span>
                <a href={`tel:${business_data.phone}`}>{business_data.phone}</a>
              </div>
            )}
            {business_data.email && (
              <div>
                <span className="section-tag">Email</span>
                <a href={`mailto:${business_data.email}`}>{business_data.email}</a>
              </div>
            )}
            {hours.length > 0 && (
              <div>
                <span className="section-tag">Hours</span>
                {hours.map((h, i) => <p key={i} className="hour-row">{h}</p>)}
              </div>
            )}
            {business_data.rating && (
              <div>
                <span className="section-tag">Rating</span>
                <p>★ {business_data.rating} ({business_data.review_count?.toLocaleString() || 0} reviews)</p>
              </div>
            )}
          </div>
          {business_data.phone && (
            <a href={`tel:${business_data.phone}`} className="cta-block">
              <span>{copy.cta_text || 'Call Now for a Free Quote'}</span>
              <strong>{business_data.phone}</strong>
            </a>
          )}
        </div>
      </section>

      <footer>
        <p>© {new Date().getFullYear()} {business_data.name} · {business_data.city}, {business_data.state}</p>
      </footer>
    </>
  );
}

export async function getStaticProps() {
  const data = require('../site_data.json');
  return { props: { data } };
}
