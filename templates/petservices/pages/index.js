import Head from 'next/head';

export default function Page({ data }) {
  const { copy = {}, photos = [], business_data = {} } = data || {};
  const hero = photos[0] || null;
  const gallery = photos.slice(1, 7);
  const hours = business_data.hours?.weekday_text || [];

  return (
    <>
      <Head>
        <title>{business_data.name || 'Pet Services'}</title>
        <meta name="description" content={copy.meta_description || ''} />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Fredoka+One&family=Nunito:wght@300;400;600;700&display=swap" rel="stylesheet" />
      </Head>

      <nav className="nav">
        <div className="nav-inner">
          <span className="nav-brand">{business_data.name}</span>
          <a href="#contact" className="nav-cta">{copy.cta_text || 'Book Now'}</a>
        </div>
      </nav>

      <section className="hero" style={hero ? { backgroundImage: `url(${hero})` } : {}}>
        <div className="hero-veil" />
        <div className="hero-body">
          <div className="hero-badge">{business_data.city}, {business_data.state}</div>
          <h1>{copy.headline}</h1>
          <p className="hero-sub">{copy.subheadline}</p>
          <div className="hero-actions">
            <a href="#contact" className="btn-coral">{copy.cta_text || 'Book an Appointment'}</a>
            {business_data.phone && (
              <a href={`tel:${business_data.phone}`} className="btn-outline">{business_data.phone}</a>
            )}
          </div>
        </div>
      </section>

      <section className="about">
        <div className="wrap about-inner">
          <div>
            <span className="section-tag">About Us</span>
            <p className="about-copy">{copy.about}</p>
            {business_data.rating && (
              <p className="rating">★ {business_data.rating} from {business_data.review_count?.toLocaleString()} happy pet parents</p>
            )}
          </div>
          {hero && <div className="about-img" style={{ backgroundImage: `url(${hero})` }} />}
        </div>
      </section>

      {copy.services?.length > 0 && (
        <section className="services">
          <div className="wrap">
            <span className="section-tag">What We Offer</span>
            <h2>Our Services</h2>
            <div className="services-grid">
              {copy.services.map((s, i) => (
                <div key={i} className="service-card">
                  <div className="card-paw">🐾</div>
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
        <div className="wrap info-inner">
          <div className="info-cta">
            <h2>Ready to Book?</h2>
            <a href={business_data.phone ? `tel:${business_data.phone}` : `mailto:${business_data.email}`} className="big-btn">
              {copy.cta_text || 'Get in Touch'}
            </a>
          </div>
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
