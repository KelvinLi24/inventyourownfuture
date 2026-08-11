# Invent Your Own Future Static Site

This repository contains a cleaned static export of the original Squarespace site. The site is now deployable as plain HTML, CSS, vanilla JavaScript, and static assets.

## Project Structure

```text
.
├── index.html
├── pages/
│   ├── about-us.html
│   ├── alumni-network.html
│   ├── career-blog.html
│   ├── contact.html
│   ├── events-and-camps.html
│   ├── internship-opportunities.html
│   ├── student-ambassador.html
│   ├── upcoming.html
│   └── ...
├── assets/
│   ├── css/
│   │   ├── static-site.css
│   │   └── vendor/
│   ├── images/
│   └── js/
│       └── main.js
├── reports/
│   ├── dependency-map.json
│   ├── migration-summary.json
│   └── validation.json
└── scripts/
    ├── check-site.py
    └── migrate_static_site.py
```

## Run Locally

```bash
python3 -m http.server 8080
```

Open:

```text
http://localhost:8080
```

## Deploy

Upload the repository root to any static host, including GitHub Pages, Cloudflare Pages, Netlify, Vercel Static, nginx, Apache, or ordinary shared hosting. No Node runtime, database, or Squarespace backend is required.

## External Dependencies

The migrated pages no longer request Squarespace domains for normal rendering.

Remaining intentional external services:

- Google Fonts: Manrope and Poppins.
- Instagram links.
- Google Forms links.
- Google Maps / Google pages linked from content.
- External article links, including The Standard.
- Original Open Graph/Twitter metadata still contains the public `www.inventyourownfuture.com` URL for sharing context; these are metadata values, not static rendering dependencies.

## Notes

- Original Chrome `*_files/` folders were consolidated into `assets/`.
- Duplicate assets were deduplicated by SHA-256 hash.
- Squarespace runtime, account, analytics/error-reporting, recaptcha, and editor/runtime scripts were removed.
- Mobile navigation, dropdown toggles, lazy image fallback, animation visibility, and static form submit handling are implemented in `assets/js/main.js`.
- Forms preserve their layout, but submissions are intentionally disabled in the static copy. Connect them to a static form provider before publishing live submissions.
- `scripts/check-site.py` validates local references, forbidden local paths, Squarespace URL residue, and external domains.

## Validation

Latest validation:

- Missing local references: 0
- Forbidden local/browser paths: 0
- Squarespace domains: 0
- Pages migrated: 18
- Unique assets copied: 96
- Duplicate source files removed through hash deduplication: 164
