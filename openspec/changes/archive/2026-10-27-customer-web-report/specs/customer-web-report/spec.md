## ADDED Requirements

### Requirement: Private report pages

Report URLs under `/r/*` MUST send `noindex, nofollow, noarchive` and MUST NOT appear as public sitemap entries.

#### Scenario: Headers on report path

- **WHEN** a client requests `/r/<slug>/`
- **THEN** the response includes `X-Robots-Tag: noindex, nofollow, noarchive`

### Requirement: Web report content parity with PDF

`/r/<slug>/` MUST render report body HTML from `build_customer_report_body_html` so section order matches the customer PDF.

#### Scenario: Sample fictional page

- **WHEN** the sample fixture is built
- **THEN** `/r/sample/` uses only fictional Riverside Accountants data

### Requirement: Report view logging

A Cloudflare Pages function on `/r/*` MUST log slug, path, timestamp, country, user agent, and ASN to D1 when configured, without storing IP addresses.

#### Scenario: Logging failure is non-fatal

- **WHEN** D1 insert fails
- **THEN** the static page still returns 200
