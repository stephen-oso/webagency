import Head from 'next/head';

export default function Page({ data }) {
  const { copy = {}, photos = [], business_data = {} } = data || {};
  const hero = photos[0] || null;
  const gallery = photos.slice(1, 7);
  const hours = business_data.hours?.weekday_text || [];

  return (
    <>
      <Head>
        <title>{business_data.name || 'Gym & Fitness'}</title>
        <meta name="description" content={copy.meta_description || ''} />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Space+Grotesk:wght@300;400;700&display=swap" rel="stylesheet" />
      </Head>

      <nav className="nav">
        <div className="nav-inner">
          <span className="nav-brand">{business_data.name}</span>
          <a href="#contact" className="nav-cta">{copy.cta_text || 'Join Now'}</a>
        </div>
      </nav>

      <section className="hero" style={hero ? { backgroundImage: `url(${hero})` } : {}}>
        <div className="hero-veil" />
        <div className="hero-body">
          <p className="eyebrow">{business_data.city}, {business_data.state}</p>
          <h1>{copy.headline}</h1>
          <p className="hero-sub">{copy.subheadline}</p>
          <div className="hero-actions">
            <a href="#contact" className="btn-green">{copy.cta_text || 'Start Today'}</a>
            {business_data.phone && (
              <a href={`tel:${business_data.phone}`} className="btn-outline">{business_data.phone}</a>
            )}
          </div>
        </div>
      </section>

      {copy.services?.length > 0 && (
        <section className="services">
          <div className="wrap">
            <p className="section-tag">What We Offer</p>
            <h2>Train With Us</h2>
            <div className="services-grid">
              {copy.services.map((s, i) => (
                <div key={i} className="service-card">
                  <div className="card-line" />
                  <span>{s}</span>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      <section className="about">
        <div className="wrap about-inner">
          <div>
            <p className="section-tag">About</p>
            <p className="about-copy">{copy.about}</p>
          </div>
          {business_data.rating && (
            <div className="rating-block">
              <span className="rating-num">★{business_data.rating}</span>
              <span className="rating-label">{business_data.review_count?.toLocaleString()} member reviews</span>
            </div>
          )}
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
          <h2>Come In</h2>
          <div className="info-grid">
            <div>
              <p className="section-tag">Location</p>
              <p>{business_data.city}, {business_data.state}</p>
            </div>
            {business_data.phone && (
              <div>
                <p className="section-tag">Phone</p>
                <a href={`tel:${business_data.phone}`}>{business_data.phone}</a>
              </div>
            )}
            {business_data.email && (
              <div>
                <p className="section-tag">Email</p>
                <a href={`mailto:${business_data.email}`}>{business_data.email}</a>
              </div>
            )}
            {hours.length > 0 && (
              <div>
                <p className="section-tag">Hours</p>
                {hours.map((h, i) => <p key={i} className="hour-row">{h}</p>)}
              </div>
            )}
          </div>
          <a href="#contact" className="join-cta">{copy.cta_text || 'Get Started Today'}</a>
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
