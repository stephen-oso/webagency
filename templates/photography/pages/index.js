import Head from 'next/head';

export default function Page({ data }) {
  const { copy = {}, photos = [], business_data = {} } = data || {};
  const hero = photos[0] || null;
  const gallery = photos.slice(0, 9);
  const hours = business_data.hours?.weekday_text || [];

  return (
    <>
      <Head>
        <title>{business_data.name || 'Photography'}</title>
        <meta name="description" content={copy.meta_description || ''} />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,600;1,400&family=Karla:ital,wght@0,300;0,400;1,300&display=swap" rel="stylesheet" />
      </Head>

      <nav className="nav">
        <div className="nav-inner">
          <span className="nav-brand">{business_data.name}</span>
          <div className="nav-right">
            <span className="nav-loc">{business_data.city}, {business_data.state}</span>
            <a href="#contact" className="nav-cta">{copy.cta_text || 'Book a Session'}</a>
          </div>
        </div>
      </nav>

      {hero && (
        <section className="hero" style={{ backgroundImage: `url(${hero})` }}>
          <div className="hero-body">
            <h1>{copy.headline}</h1>
            <p>{copy.subheadline}</p>
          </div>
        </section>
      )}

      <section className="intro">
        <div className="wrap intro-inner">
          <p className="intro-copy">{copy.about}</p>
          <a href="#contact" className="btn">{copy.cta_text || 'Book a Session'}</a>
        </div>
      </section>

      {copy.services?.length > 0 && (
        <section className="services">
          <div className="wrap">
            <p className="section-tag">Specialties</p>
            <div className="services-list">
              {copy.services.map((s, i) => (
                <span key={i} className="service-pill">{s}</span>
              ))}
            </div>
          </div>
        </section>
      )}

      {gallery.length > 0 && (
        <section className="gallery">
          <div className="gallery-masonry">
            {gallery.map((src, i) => (
              <div key={i} className="gallery-item">
                <img src={src} alt="" loading="lazy" />
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="info" id="contact">
        <div className="wrap info-inner">
          <div className="info-left">
            <span className="section-tag">Get In Touch</span>
            <h2>{copy.cta_text || 'Book a Session'}</h2>
          </div>
          <div className="info-right">
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
                  <span className="section-tag">Availability</span>
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
          </div>
        </div>
      </section>

      <footer>
        <p>{business_data.name} · {business_data.city}, {business_data.state} · © {new Date().getFullYear()}</p>
      </footer>
    </>
  );
}

export async function getStaticProps() {
  const data = require('../site_data.json');
  return { props: { data } };
}
