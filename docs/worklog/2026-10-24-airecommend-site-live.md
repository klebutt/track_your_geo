# 2026-10-24 AI Recommend site live

## What shipped

- **PR #1** — `site/` directory: static site generator (`build.py`), booking page, privacy policy, `/r/<slug>/` report pages, D1 logging for link opens
- **PR #2** — PECR privacy wording fix: updated to corporate-subscriber basis (Ltd/LLP only)

## Live at

- https://airecommend.co.uk (Cloudflare Pages project `airecommend`)
- D1 database `airecommend-log` logs `/r/*` opens

## Key decisions

- **CTA:** 15-min Google Calendar booking link (not Cal.com/Calendly)
- **Footer:** "AI Recommend is a trading name of Kieran Le Butt" (not incorporated)
- **Team:** Kieran only on site (Sam removed)
- **No price ask:** £5–20 soft WTP removed from wave-2 reports and site

## Deploy steps (Kieran)

```bash
cd site && python build.py
wrangler pages deploy dist --project-name airecommend
```

## Follow-ups

- Generic batch runner PR (in progress) for wave-2 reports
- Build private `/r/<slug>/` pages with hash gate vs vault PDF
- New email signature in AgentMail
