# Web Agency Automation Tool — Design Spec
**Date:** 2026-08-06
**Status:** Approved

---

## Overview

An autonomous pipeline that finds businesses in the US/Canada without websites (or with outdated ones), gathers their real photos and data from public sources, builds them a bespoke designer-quality Next.js website, publishes it, and sends personalized outreach with the live URL.

Built first for personal use. Architecture is designed to scale into a sellable multi-tenant SaaS product.

**Name:** TBD (placeholder: "webagency")

---

## Goals

- Phase 1: Personal tool. Run autonomously, check dashboard, land clients.
- Phase 2: Multi-tenant SaaS product. Paying users get their own pipeline instances.
- Zero AI-slop websites. Design is hand-crafted. AI only handles content insertion.
- Run for ~$10-15/mo personal use (Railway only; everything else free tier).

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Next.js Dashboard                     │
│         (pipeline view, CRM, review toggle, logs)       │
└────────────────────────┬────────────────────────────────┘
                         │ HTTP
┌────────────────────────▼────────────────────────────────┐
│                  FastAPI (Python)                        │
│         (REST API, job dispatch, status reads)          │
└──────┬──────────────────────────────────────┬───────────┘
       │ Enqueue                              │ Read/Write
┌──────▼──────┐                    ┌──────────▼──────────┐
│    Redis    │                    │     PostgreSQL       │
│  (Celery    │                    │  businesses, jobs,  │
│   queues)   │                    │  sites, outreach    │
└──────┬──────┘                    └─────────────────────┘
       │
┌──────▼──────────────────────────────────────────────────┐
│                    Celery Workers                        │
│                                                         │
│  [1] Discover → [2] Gather → [3] Build → [4] Publish   │
│                                          → [5] Outreach │
└─────────────────────────────────────────────────────────┘
```

Workers chain automatically. When step N completes for a business, it enqueues step N+1. Review mode pauses the chain between Publish and Outreach.

---

## Stack

| Layer | Technology |
|---|---|
| Pipeline workers | Python + Celery |
| Job queue | Redis |
| REST API | FastAPI |
| Database | PostgreSQL |
| Asset storage | Cloudflare R2 (photos) |
| Dashboard | Next.js + Tailwind |
| Client sites | Next.js (15 hand-crafted templates) |
| Site hosting | Vercel (personal) → self-hosted nginx (at scale) |
| Worker hosting | Railway |
| Email outreach | Resend |
| Form outreach | Playwright (headless) |
| AI (copy only) | Claude API (claude-sonnet-4-6) |
| Business discovery | Google Places API + Yelp Fusion API |
| Email lookup | Hunter.io (free tier personal) |

---

## The Five Pipeline Workers

### Worker 1 — Discover

Inputs: region (city, state/province), business categories

1. Query Google Places API (Nearby Search) for businesses in the region by category.
2. Query Yelp Fusion for the same region + category.
3. Cross-reference results, deduplicate by name + address.
4. For each business, check if they have a real website:
   - No website field in the listing → immediate candidate
   - Has a website → Playwright visits it, scores it 0-10 (404, parked domain, last-updated >3yrs, mobile-broken = low score = candidate)
5. Score candidates by "likelihood to buy" (no social presence, local service business, fewer than 10 reviews, older listing).
6. Write top candidates to `businesses` table with status `discovered`.

Retry: 3 attempts, 60s backoff.

### Worker 2 — Gather

Inputs: `business_id`

1. Pull all available photos from Google Places Photos API. Store to Cloudflare R2.
2. Pull full business details: hours, description, rating, review count, address, phone.
3. Pull Yelp business details: additional photos, categories, price range.
4. Attempt light social scan: check if a Facebook/Instagram page exists (public only).
5. Write everything to `business_assets` table.
6. Update `businesses.status` → `gathering_done`.

Retry: 3 attempts, 120s backoff.

### Worker 3 — Build

Inputs: `business_id`, gathered assets

**Design rule: AI never touches layout or design. AI only fills in content.**

1. Map business category to one of 8 industry templates (see Template Library below).
2. Send gathered data + photos to Claude API with a structured prompt:
   - Generate page copy: headline, subheadline, about blurb, services list, CTA text.
   - Copy must reference real details from reviews and listing (no generic filler).
   - Extract dominant brand colors from photos if available.
3. Clone the selected template. Slot in:
   - Real photos (hero, gallery, about section — placed correctly per template layout)
   - Generated copy
   - Real hours, address, phone, services
   - Color overrides if brand colors extracted
4. Output: a complete Next.js project directory ready to deploy.
5. Update `businesses.status` → `built`.

Retry: 3 attempts, 180s backoff.

### Worker 4 — Publish

Inputs: `business_id`, built Next.js project path

1. Deploy the generated project to Vercel via Vercel CLI / API.
2. Assign subdomain: `{slug}.{youragency-domain}.com`
3. Store Vercel deployment URL + custom subdomain in `sites` table.
4. **If review mode is ON:** set `sites.review_status = pending_review`, stop chain. Dashboard shows site for approval.
5. **If review mode is OFF:** set `sites.review_status = approved`, enqueue Worker 5 immediately.
6. Update `businesses.status` → `published`.

Publisher is abstracted behind a `Publisher` interface. Vercel is the default implementation. Self-hosted nginx is an alternate implementation swappable at config time (for scale).

Retry: 3 attempts, 60s backoff.

### Worker 5 — Outreach

Inputs: `business_id`, `site_id`

Runs two parallel sub-tasks:

**Email outreach:**
1. Look up business email via Hunter.io domain search.
2. Fall back to email found in Google/Yelp listing.
3. Compose personalized email via Claude API:
   - References real business name, city, specific detail from their listing.
   - Includes live site URL prominently.
   - Subject: "I built [Business Name] a website — take a look"
   - Tone: direct, not salesy. "Here's what I built you. Want to keep it?"
4. Send via Resend. Log result to `outreach` table.

**Contact form outreach:**
1. Playwright visits the business's existing website (if any) or Google listing.
2. Finds and fills contact form with personalized message + site URL.
3. Logs result to `outreach` table.

Daily cap: configurable per user (default 20 outreach attempts/day) to avoid spam flags.
Retry: 3 attempts, 300s backoff.

---

## Template Library

15 hand-crafted Next.js templates, one per industry vertical. All designed properly — real typography system, intentional layout, looks agency-built. AI never modifies the template structure.

| # | Vertical | Key Sections |
|---|---|---|
| 1 | Restaurant / Café | Hero with food photo, menu highlights, hours, reservations CTA |
| 2 | Plumber / Trades | Emergency CTA prominent, services, coverage area, trust badges |
| 3 | Hair Salon / Beauty | Gallery-forward, team, booking CTA, services + pricing |
| 4 | Dentist / Medical | Trust-first, services, team bios, insurance info, booking |
| 5 | Landscaping / Outdoor | Before/after gallery, services, coverage area, seasonal CTA |
| 6 | Retail / Boutique | Product highlights, story, hours, location, social links |
| 7 | General Trades | Services grid, about, coverage, quote request form |
| 8 | Professional Services | Clean/minimal, services, about, credentials, contact |
| 9 | Auto Repair / Mechanic | Bold/industrial, services, trust badges, location + hours |
| 10 | Cleaning Services | Before/after, residential vs commercial toggle, quote form |
| 11 | Gym / Fitness | Energy-forward, classes/services, schedule, membership CTA |
| 12 | Photography / Creative | Full-bleed portfolio gallery, packages, about, booking |
| 13 | Real Estate Agent | Listings grid, agent bio, testimonials, contact |
| 14 | Childcare / Daycare | Warm/safe, program overview, staff, enrollment CTA |
| 15 | Pet Services | Playful, services (grooming/boarding/vet), gallery, booking |

Each template is a standalone Next.js app using static export. Deployed independently to Vercel per client.

---

## Data Model

```sql
-- Core business record
businesses (
  id UUID PRIMARY KEY,
  name TEXT,
  address TEXT,
  city TEXT,
  state TEXT,
  phone TEXT,
  email TEXT,
  category TEXT,
  google_place_id TEXT,
  yelp_id TEXT,
  existing_website TEXT,
  website_score INT,        -- 0-10, lower = better candidate
  status TEXT,              -- discovered | gathering | built | published | outreached | responded
  user_id UUID,             -- for multi-tenant Phase 2
  created_at TIMESTAMPTZ
)

-- Gathered assets
business_assets (
  id UUID PRIMARY KEY,
  business_id UUID REFERENCES businesses,
  photos JSONB,             -- array of R2 URLs
  description TEXT,
  hours JSONB,
  rating NUMERIC,
  review_count INT,
  reviews_summary TEXT,
  social_links JSONB,
  services JSONB,
  price_range TEXT,
  raw_google JSONB,
  raw_yelp JSONB
)

-- Generated + published sites
sites (
  id UUID PRIMARY KEY,
  business_id UUID REFERENCES businesses,
  template_used TEXT,
  vercel_url TEXT,
  custom_subdomain TEXT,
  review_status TEXT,       -- pending | approved | rejected
  deployed_at TIMESTAMPTZ
)

-- Outreach attempts and responses
outreach (
  id UUID PRIMARY KEY,
  business_id UUID REFERENCES businesses,
  site_id UUID REFERENCES sites,
  email_to TEXT,
  email_sent_at TIMESTAMPTZ,
  email_status TEXT,        -- sent | bounced | opened | replied
  form_submitted_at TIMESTAMPTZ,
  form_status TEXT,         -- submitted | failed | skipped
  response_text TEXT,
  responded_at TIMESTAMPTZ
)

-- Pipeline job tracking
jobs (
  id UUID PRIMARY KEY,
  business_id UUID REFERENCES businesses,
  step TEXT,                -- discover | gather | build | publish | outreach
  status TEXT,              -- queued | running | success | failed
  error_msg TEXT,
  attempts INT DEFAULT 0,
  last_run_at TIMESTAMPTZ
)
```

---

## Dashboard

### Pipeline View (main screen)
Live kanban with columns: Discovered → Gathering → Built → Published → Outreached → Responded.

Each card shows:
- Business name + city
- Category badge
- Current step + time in step
- Site thumbnail (once built)
- Quick approve/reject buttons (when review mode is on)

Review mode toggle lives in the top bar. Flipping it on pauses all pipelines at the Publish → Outreach transition.

### Business Detail
Click any card to open:
- Full gathered data (photos, hours, reviews)
- Live site preview in iframe
- Approve / Reject / Retry buttons
- Outreach log (email status, form status, any replies)
- Manual override: skip a step, re-run a step

### Settings
- Target region (city + radius)
- Business categories to target
- Review mode toggle
- Outreach daily cap
- API key configuration (Google, Yelp, Hunter.io, Resend)
- Vercel token + domain

### CLI
FastAPI exposes a REST API. A thin Python CLI (`agency`) wraps it:

```bash
agency run --region "Toronto, ON" --category plumber
agency status
agency approve <business_id>
agency reject <business_id>
agency retry <business_id> --step build
```

---

## Error Handling

- Every Celery task: max 3 retries, exponential backoff (60s, 120s, 300s)
- Failed jobs surface in dashboard with exact error message
- Manual retry available per business per step
- Dead-letter queue for jobs that exhaust retries — never silently lost
- Playwright steps use rotating user agents to reduce scraping blocks

---

## Hosting & Cost

### Personal use (~$10-15/mo)
- Railway: Python workers + Redis + Postgres (~$10-15/mo)
- Vercel Hobby: dashboard + client sites (free)
- Cloudflare R2: photo storage (free tier)
- Google Places: $200/mo free credit (covers personal volume)
- Yelp Fusion: free tier
- Resend: free tier (3,000 emails/mo)
- Hunter.io: free tier (25 lookups/mo)
- Claude API: covered by existing Anthropic API key (same one used in your other projects)

### Scaling to product
- 10 users → ~$550/mo infrastructure, $3,990/mo revenue (~86% margin)
- 100 users → ~$5,200/mo infrastructure, $39,900/mo revenue (~87% margin)
- At scale: swap Vercel client site hosting for self-hosted nginx (Publisher interface makes this a config change)

---

## Phasing

### Phase 1 — Personal Tool (this spec)
- Full 5-step pipeline working end-to-end
- 15 hand-crafted Next.js templates
- Next.js dashboard with pipeline kanban + review mode
- CLI wrapper
- Email + contact form outreach
- Deployed: Railway (workers) + Vercel (dashboard + client sites)

### Phase 2 — Product (future spec)
- Multi-user accounts + authentication
- Billing (Stripe)
- Per-user pipeline isolation
- White-label option
- Analytics: open rates, response rates, conversion tracking
- More templates, more verticals
- Admin dashboard (owner view across all users)

---

## Open Questions / Decisions Deferred
- Final product name (placeholder: "webagency")
- Custom domain for client site subdomains (e.g. `youragency.com`)
- Whether to use Hunter.io or an alternative for email lookup at scale
- Exact Claude prompt structure for copy generation (to be tuned during build)
