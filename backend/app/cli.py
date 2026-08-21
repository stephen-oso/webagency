"""agency - CLI for the WebAgency pipeline."""
import os
import sys

import click
import httpx

_API_URL = os.environ.get("WEBAGENCY_API_URL", "http://localhost:8000")


def _api(method: str, path: str, **kwargs) -> dict:
    try:
        r = httpx.request(method, f"{_API_URL}{path}", timeout=10, **kwargs)
        r.raise_for_status()
        return r.json()
    except httpx.HTTPStatusError as e:
        click.echo(f"Error {e.response.status_code}: {e.response.text}", err=True)
        sys.exit(1)
    except httpx.RequestError:
        click.echo(f"Cannot reach {_API_URL} — is the server running?", err=True)
        sys.exit(1)


@click.group()
def cli():
    """WebAgency pipeline CLI.

    Set WEBAGENCY_API_URL to point at a remote server (default: http://localhost:8000).
    """


@cli.command()
@click.argument("region")
@click.argument("categories", nargs=-1, required=True)
def run(region, categories):
    """Kick off a discovery run.

    \b
    Example:
        agency run "Austin, TX" plumber dentist salon
    """
    _api("POST", "/pipeline/run", json={"region": region, "categories": list(categories)})
    click.echo(f"Queued: {region} — {', '.join(categories)}")


@cli.command("ls")
@click.option("--status", "-s", default=None, help="Filter by status (discovered / built / outreached)")
@click.option("--limit", "-n", default=50, help="Max results (default 50)")
def list_businesses(status, limit):
    """List businesses in the pipeline."""
    params = {"limit": limit}
    if status:
        params["status"] = status
    businesses = _api("GET", "/businesses", params=params)
    if not businesses:
        click.echo("No businesses found.")
        return

    click.echo(f"\n{'UUID':<36}  {'NAME':<28}  {'CITY':<14}  {'CATEGORY':<14}  {'STATUS':<14}  SCORE")
    click.echo("─" * 118)
    for b in businesses:
        score = str(b["website_score"]) if b.get("website_score") is not None else "—"
        click.echo(
            f"{str(b['id']):<36}  {b['name'][:28]:<28}  {b['city'][:14]:<14}  "
            f"{b['category'][:14]:<14}  {b['status'][:14]:<14}  {score}"
        )
    click.echo(f"\n{len(businesses)} result(s).")


@cli.command()
@click.argument("business_id")
def show(business_id):
    """Show full detail for a business."""
    b = _api("GET", f"/businesses/{business_id}")
    click.echo(f"\n{b['name']}  —  {b['city']}, {b['state']}")
    click.echo(f"ID:       {b['id']}")
    click.echo(f"Status:   {b['status']}   Score: {b.get('website_score') or '—'}")
    click.echo(f"Category: {b.get('category', '—')}")
    if b.get("address"):
        click.echo(f"Address:  {b['address']}")
    if b.get("phone"):
        click.echo(f"Phone:    {b['phone']}")
    if b.get("email"):
        click.echo(f"Email:    {b['email']}")
    if b.get("existing_website"):
        click.echo(f"Website:  {b['existing_website']}")

    if b.get("site"):
        s = b["site"]
        click.echo(f"\n── Site ─────────────────────────────")
        click.echo(f"URL:      {s.get('vercel_url') or '(not deployed)'}")
        click.echo(f"Review:   {s.get('review_status') or 'pending'}")
        click.echo(f"Template: {s.get('template_used') or '—'}")
        if s.get("deployed_at"):
            click.echo(f"Deployed: {s['deployed_at'][:16]}")

    if b.get("outreach"):
        o = b["outreach"]
        click.echo(f"\n── Outreach ─────────────────────────")
        if o.get("email_to"):
            click.echo(f"To:     {o['email_to']}")
        click.echo(f"Email:  {o.get('email_status') or '—'}   Form: {o.get('form_status') or '—'}")

    if b.get("recent_jobs"):
        click.echo(f"\n── Recent Jobs ──────────────────────")
        for j in b["recent_jobs"]:
            ts = (j.get("last_run_at") or "")[:16] or "—"
            err = f"  ← {j['error_msg'][:70]}" if j.get("error_msg") else ""
            click.echo(f"  {j.get('step'):<12}  {j.get('status'):<10}  {ts}{err}")
    click.echo()


@cli.command()
@click.argument("business_id")
def approve(business_id):
    """Approve a site and trigger outreach."""
    result = _api("POST", f"/businesses/{business_id}/approve")
    click.echo(f"Approved.  Site ID: {result.get('site_id')}")


@cli.command()
@click.argument("business_id")
def reject(business_id):
    """Reject a business (no outreach sent)."""
    _api("POST", f"/businesses/{business_id}/reject")
    click.echo("Rejected.")


@cli.command()
@click.argument("business_id")
@click.argument("step", type=click.Choice(["gather", "build", "publish", "outreach"]))
def retry(business_id, step):
    """Re-queue a pipeline step for a business.

    \b
    Steps: gather  build  publish  outreach
    Example:
        agency retry <uuid> build
    """
    _api("POST", f"/businesses/{business_id}/retry", json={"step": step})
    click.echo(f"Queued {step} for {business_id[:8]}…")


@cli.command()
@click.option("--status", "-s", default=None, help="Filter: pending / running / done / failed")
@click.option("--limit", "-n", default=20, help="Max results (default 20)")
def jobs(status, limit):
    """Show recent pipeline jobs."""
    params = {"limit": limit}
    if status:
        params["status"] = status
    job_list = _api("GET", "/jobs", params=params)
    if not job_list:
        click.echo("No jobs found.")
        return

    click.echo(f"\n{'STEP':<12}  {'STATUS':<10}  {'BUSINESS':<8}  {'LAST RUN':<16}  ERROR")
    click.echo("─" * 100)
    for j in job_list:
        ts = (j.get("last_run_at") or "")[:16] or "—"
        err = (j.get("error_msg") or "")[:50]
        bid = str(j.get("business_id") or "")[:8]
        click.echo(f"{j.get('step') or '—':<12}  {j.get('status') or '—':<10}  {bid:<8}  {ts:<16}  {err}")
    click.echo()
