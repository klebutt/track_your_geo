"""AI Recommend site configuration.

PLACEHOLDERS FOR KIERAN TO FILL IN:
====================================
1. BOOKING_LINK - Cal.com or Calendly 15-min event URL
2. KIERAN_SURNAME - Kieran's surname for display
3. KIERAN_PHONE - Kieran's phone number (optional, can be empty string)
4. SAM_SURNAME - Sam's surname for display
5. SAM_PHOTO_PATH - Path to Sam's photo (relative to public/)
6. CONTACT_ADDRESS - Contact address for privacy page and footer
7. TRADING_NAME_LINE - Trading name/company line for footer

Once incorporated, update TRADING_NAME_LINE to:
    "{Company} Ltd, registered in England & Wales no. XXXXXXX"
"""

# =============================================================================
# PLACEHOLDERS - KIERAN MUST FILL THESE IN BEFORE DEPLOY
# =============================================================================

# Booking link (Cal.com or Calendly 15-min event)
# Example: "https://cal.com/kieran/15min" or "https://calendly.com/kieran/15min"
BOOKING_LINK = "https://PLACEHOLDER_BOOKING_LINK"

# Kieran's details
KIERAN_SURNAME = "PLACEHOLDER_KIERAN_SURNAME"
KIERAN_PHONE = ""  # Optional, leave empty if not wanted

# Sam's details
SAM_SURNAME = "PLACEHOLDER_SAM_SURNAME"
SAM_PHOTO_PATH = "images/sam.jpg"  # Kieran must add this image to site/public/images/

# Contact address (for privacy page and email signature)
# Use a business address, not a home address
CONTACT_ADDRESS = "PLACEHOLDER_CONTACT_ADDRESS"

# Trading name line for footer (update when incorporated)
# Pre-incorporation: "AI Recommend is a trading name of Kieran {Surname} and Sam {Surname}"
# Post-incorporation: "{Company} Ltd, registered in England & Wales no. XXXXXXX"
TRADING_NAME_LINE = "AI Recommend is a trading name of Kieran PLACEHOLDER_KIERAN_SURNAME and Sam PLACEHOLDER_SAM_SURNAME"

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
