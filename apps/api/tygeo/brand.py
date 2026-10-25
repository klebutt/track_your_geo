"""AI Recommend brand constants — single source of truth.

Imported by:
- tygeo.plain_report (for CTA in reports)
- site/config.py (for site build)
"""

# Booking link (Google Calendar 15-min appointment)
BOOKING_LINK_RAW = "https://calendar.app.google/omsy1ZoJ7SsduLq87"
BOOKING_SHORT_URL = "https://airecommend.co.uk/book"
BOOKING_LINK = BOOKING_SHORT_URL  # preferred link for reports and site

# Contact email
CONTACT_EMAIL = "kieran@airecommend.co.uk"

# Trading name line for footer (update when incorporated)
# Pre-incorporation: "AI Recommend is a trading name of Kieran Le Butt"
# Post-incorporation: "{Company} Ltd, registered in England & Wales no. XXXXXXX"
TRADING_NAME_LINE = "AI Recommend is a trading name of Kieran Le Butt"

# PDF / report colours (RGB) - mirror site/public/styles.css :root variables
COLOR_PRIMARY = (30, 64, 175)  # --color-primary #1e40af
COLOR_PRIMARY_DARK = (30, 58, 138)  # --color-primary-dark #1e3a8a
COLOR_TEXT = (30, 41, 59)  # --color-text #1e293b
COLOR_TEXT_MUTED = (100, 116, 139)  # --color-text-muted #64748b
COLOR_BG_ALT = (248, 250, 252)  # --color-bg-alt #f8fafc
COLOR_BORDER = (226, 232, 240)  # --color-border #e2e8f0

# Site domain shown in PDF footers
SITE_DOMAIN = "airecommend.co.uk"
