"""AI Recommend site configuration.

Brand constants (BOOKING_LINK, CONTACT_EMAIL, TRADING_NAME_LINE) are imported
from tygeo.brand — the single source of truth for both API and site.

PLACEHOLDERS FOR KIERAN TO FILL IN:
====================================
1. KIERAN_PHONE - Kieran's phone number (optional, can be empty string)
2. CONTACT_ADDRESS - Business contact address (optional, can be empty string)

Once incorporated, update TRADING_NAME_LINE in apps/api/tygeo/brand.py to:
    "{Company} Ltd, registered in England & Wales no. XXXXXXX"
"""

# =============================================================================
# BRAND CONSTANTS (imported from tygeo.brand — single source of truth)
# =============================================================================
# Note: site/build.py adds apps/api to sys.path before importing this module.
try:
    from tygeo.brand import BOOKING_LINK, CONTACT_EMAIL, TRADING_NAME_LINE
except ImportError:
    # Fallback for standalone imports (e.g., scripts that don't set up paths)
    BOOKING_LINK = "https://calendar.app.google/omsy1ZoJ7SsduLq87"
    CONTACT_EMAIL = "kieran@airecommend.co.uk"
    TRADING_NAME_LINE = "AI Recommend is a trading name of Kieran Le Butt"

# =============================================================================
# KIERAN'S DETAILS
# =============================================================================
KIERAN_SURNAME = "Le Butt"
KIERAN_PHONE = ""  # Optional, leave empty if not wanted

# Contact address (for privacy page and email signature)
# Optional: leave empty to show only email, no address line
CONTACT_ADDRESS = ""

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
