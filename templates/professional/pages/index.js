import Head from 'next/head';

export default function Page({ data }) {
  const { copy = {}, photos = [], business_data = {} } = data || {};
  const hero = photos[0] || null;
  const gallery = photos.slice(1, 7);
  const hours = business_data.hours?.weekday_text || [];

  return (
    <>
      <Head>
        <title>{business_data.name || 'Professional Services'}</title>
        <meta name="description" content={copy.meta_description || ''} />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Cormorant:ital,wght@0,300;0,500;1,300&family=Inter:wght@300;400;500&display=swap" rel="stylesheet" />
      </Head>

      <nav className="nav">
        <div className="nav-inner">
          <span className="nav-brand">{business_data.name}</span>
          <a href="#contact" className="nav-cta">{copy.cta_text || 'Get in Touch'}</a>
        </div>
      </nav>

      <section className="hero">
        <div className="hero-inner">
          {hero && <div className="hero-img" style={{ backgroundImage: `url(${hero})` }} />}
          <div className="hero-text">
            <p className="eyebrow">{business_data.city}, {business_data.state}</p>
            <h1>{copy.headline}</h1>
            <p className="lead">{copy.subheadline}</p>
            <a href="#contact" className="btn">{copy.cta_text || 'Schedule a Consultation'}</a>
          </div>
        </div>
      </section>

      <section className="about">
        <div className="wrap">
          <div className="about-inner">
            <div className="about-label">
              <span className="section-tag">About</span>
              <div className="gold-line" />
            </div>
            <p className="about-copy">{copy.about}</p>
          </div>
        </div>
      </section>

      {copy.services?.length > 0 && (
        <section className="services">
          <div className="wrap">
            <span className="section-tag">Practice Areas</span>
            <h2>Services</h2>
            <div className="services-grid">
              {copy.services.map((s, i) => (
                <div key={i} className="service-item">
                  <div className="item-dot" />
                  <span>{s}</span>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      {gallery.length > 0 && (
        <section className="gallery">
          <div className="gallery-grid">
            {gallery.map((src, i) => (
              <div key={i} className="gallery-cell">
                <img src={src} alt="" loading="lazy" />
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="info" id="contact">
        <div className="wrap info-inner">
          <div className="info-left">
            <span className="section-tag">Contact</span>
            <h2>{business_data.name}</h2>
            <p className="info-sub">{business_data.city}, {business_data.state}</p>
          </div>
          <div className="info-right">
            <div className="info-grid">
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
                  <span className="section-tag">Office Hours</span>
                  {hours.map((h, i) => <p key={i} className="hour-row">{h}</p>)}
                </div>
              )}
              {business_data.rating && (
                <div>
                  <span className="section-tag">Client Rating</span>
                  <p>★ {business_data.rating} ({business_data.review_count?.toLocaleString() || 0} reviews)</p>
                </div>
              )}
            </div>
          </div>
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
