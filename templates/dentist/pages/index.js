import Head from 'next/head';

export default function Page({ data }) {
  const { copy = {}, photos = [], business_data = {} } = data || {};
  const hero = photos[0] || null;
  const gallery = photos.slice(1, 7);
  const hours = business_data.hours?.weekday_text || [];

  return (
    <>
      <Head>
        <title>{business_data.name || 'Dental Practice'}</title>
        <meta name="description" content={copy.meta_description || ''} />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Libre+Baskerville:ital,wght@0,400;0,700;1,400&family=Source+Sans+3:wght@300;400;600&display=swap" rel="stylesheet" />
      </Head>

      <nav className="nav">
        <div className="nav-inner">
          <span className="nav-brand">{business_data.name}</span>
          <a href="#contact" className="nav-cta">{copy.cta_text || 'Book Appointment'}</a>
        </div>
      </nav>

      <section className="hero" style={hero ? { backgroundImage: `url(${hero})` } : {}}>
        <div className="hero-veil" />
        <div className="hero-body">
          <div className="trust-strip">
            <span>✓ Accepting New Patients</span>
            <span>✓ Most Insurance Accepted</span>
            <span>✓ Family Friendly</span>
          </div>
          <h1>{copy.headline}</h1>
          <p className="hero-sub">{copy.subheadline}</p>
          <div className="hero-actions">
            <a href="#contact" className="btn-primary">{copy.cta_text || 'Book Appointment'}</a>
            {business_data.phone && (
              <a href={`tel:${business_data.phone}`} className="btn-ghost">{business_data.phone}</a>
            )}
          </div>
        </div>
      </section>

      {copy.services?.length > 0 && (
        <section className="services">
          <div className="wrap">
            <div className="section-head">
              <span className="section-tag">Our Services</span>
              <h2>Comprehensive Dental Care</h2>
            </div>
            <div className="services-grid">
              {copy.services.map((s, i) => (
                <div key={i} className="service-card">
                  <div className="service-icon">+</div>
                  <span>{s}</span>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      <section className="about">
        <div className="wrap about-inner">
          <div className="about-text">
            <span className="section-tag">About Our Practice</span>
            <h2>{business_data.name}</h2>
            <p className="about-copy">{copy.about}</p>
          </div>
          {hero && <div className="about-img" style={{ backgroundImage: `url(${hero})` }} />}
        </div>
      </section>

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
        <div className="wrap">
          <h2>Visit Us</h2>
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
                <span className="section-tag">Office Hours</span>
                {hours.map((h, i) => <p key={i} className="hour-row">{h}</p>)}
              </div>
            )}
            {business_data.rating && (
              <div>
                <span className="section-tag">Patient Rating</span>
                <p>★ {business_data.rating} ({business_data.review_count?.toLocaleString() || 0} reviews)</p>
              </div>
            )}
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
