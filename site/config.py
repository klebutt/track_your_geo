"""AI Recommend site configuration.

PLACEHOLDERS FOR KIERAN TO FILL IN:
====================================
1. BOOKING_LINK - Google Calendar 15-min appointment URL
2. KIERAN_PHONE - Kieran's phone number (optional, can be empty string)
3. CONTACT_ADDRESS - Business contact address (optional, can be empty string)
4. TRADING_NAME_LINE - Trading name/company line for footer

Once incorporated, update TRADING_NAME_LINE to:
    "{Company} Ltd, registered in England & Wales no. XXXXXXX"
"""

# =============================================================================
# PLACEHOLDERS - KIERAN MUST FILL THESE IN BEFORE DEPLOY
# =============================================================================

# Booking link (Google Calendar 15-min appointment)
BOOKING_LINK = "https://calendar.app.google/omsy1ZoJ7SsduLq87"

# Kieran's details
KIERAN_SURNAME = "Le Butt"
KIERAN_PHONE = ""  # Optional, leave empty if not wanted

# Contact address (for privacy page and email signature)
# Optional: leave empty to show only email, no address line
CONTACT_ADDRESS = ""

# Trading name line for footer (update when incorporated)
# Pre-incorporation: "AI Recommend is a trading name of Kieran Le Butt"
# Post-incorporation: "{Company} Ltd, registered in England & Wales no. XXXXXXX"
TRADING_NAME_LINE = "AI Recommend is a trading name of Kieran Le Butt"

# =============================================================================
# FIXED CONFIGURATION (do not change without good reason)
# =============================================================================

DOMAIN = "airecommend.co.uk"
SITE_URL = f"https://{DOMAIN}"
CONTACT_EMAIL = f"kieran@{DOMAIN}"

# Privacy policy details
DATA_RETENTION_MONTHS = 12

# Cloudflare Pages project name (for wrangler deploy)
PAGES_PROJECT_NAME = "airecommend"

# D1 database name
D1_DATABASE_NAME = "airecommend-log"
