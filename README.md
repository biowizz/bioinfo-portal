# Bioinfo Portal

Static site listing bioinformatics conferences and jobs, built with
[Eleventy](https://www.11ty.dev/) and deployed to GitHub Pages.

## Structure

- `data/conferences/`, `data/jobs/` — one YAML file per listing (see schema below)
- `site/` — Eleventy templates, layouts, CSS, and client-side JS
- `scripts/add_listing.py` — paste a URL or raw text, get a parsed YAML listing
- `.github/workflows/build-deploy.yml` — builds and deploys to GitHub Pages on push to `main`

## Local development

```bash
npm install
npm run serve   # local dev server with live reload
npm run build   # build to _site/
```

## Listing schema

```yaml
type: job                # job | conference
title: "Postdoctoral Bioinformatician"
organization: "EMBL Heidelberg"
location: "Heidelberg, Germany"
remote: false
deadline: "2026-10-15"
start_date: null          # relevant for conferences
end_date: null
tags: [genomics, single-cell, postdoc]
source_url: "https://www.embl.org/jobs/..."
added_on: "2026-08-24"
description: >
  Short 2-3 sentence summary.
```
