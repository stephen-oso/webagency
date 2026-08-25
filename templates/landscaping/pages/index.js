import Head from 'next/head';

export default function Page({ data }) {
  const { copy = {}, photos = [], business_data = {} } = data || {};
  const hero = photos[0] || null;
  const gallery = photos.slice(1, 7);
  const hours = business_data.hours?.weekday_text || [];

  return (
    <>
      <Head>
        <title>{business_data.name || 'Landscaping'}</title>
        <meta name="description" content={copy.meta_description || ''} />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Crimson+Pro:ital,wght@0,400;0,700;1,400&family=Lato:wght@300;400;700&display=swap" rel="stylesheet" />
      </Head>

      <nav className="nav">
        <div className="nav-inner">
          <span className="nav-brand">{business_data.name}</span>
          <a href="#contact" className="nav-cta">{copy.cta_text || 'Free Estimate'}</a>
        </div>
      </nav>

      <section className="hero" style={hero ? { backgroundImage: `url(${hero})` } : {}}>
        <div className="hero-veil" />
        <div className="hero-body">
          <p className="eyebrow">Serving {business_data.city}, {business_data.state}</p>
          <h1>{copy.headline}</h1>
          <p className="hero-sub">{copy.subheadline}</p>
          <a href="#contact" className="btn">{copy.cta_text || 'Get Free Estimate'}</a>
        </div>
      </section>

      <section className="about">
        <div className="wrap about-inner">
          <div>
            <span className="section-tag">About Us</span>
            <p className="about-copy">{copy.about}</p>
          </div>
          <div className="stats">
            {business_data.rating && (
              <div className="stat">
                <span className="stat-val">★ {business_data.rating}</span>
                <span className="stat-label">{business_data.review_count?.toLocaleString()} Reviews</span>
              </div>
            )}
            <div className="stat">
              <span className="stat-val">{business_data.city}</span>
              <span className="stat-label">{business_data.state}</span>
            </div>
          </div>
        </div>
      </section>

      {copy.services?.length > 0 && (
        <section className="services">
          <div className="wrap">
            <span className="section-tag">What We Do</span>
            <h2>Our Services</h2>
            <div className="services-grid">
              {copy.services.map((s, i) => (
                <div key={i} className="service-card">
                  <span className="service-leaf">🌿</span>
                  <span>{s}</span>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

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
        <div className="wrap info-grid">
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
        </div>
        <div className="wrap" style={{ marginTop: '3rem' }}>
          <a href={business_data.phone ? `tel:${business_data.phone}` : `mailto:${business_data.email}`} className="cta-btn">
            {copy.cta_text || 'Request a Free Estimate'}
          </a>
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
