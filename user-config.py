# -*- coding: utf-8 -*-
"""
Pywikibot user-config.py for Moegirlpedia (萌娘百科).

Quick start (anonymous, HTML fallback):
  ─ Leave this file as-is.  The script will scrape HTML when the API blocks.

With authentication (bot password):
  1. Set your username below.
  2. Create user-password.py (copy from user-password.py.example).
  3. Run the fetch script.

  ⚠  IMPORTANT — Moegirlpedia limitation:
     Even with a valid bot password, Moegirlpedia's API blocks content-read
     actions (prop=revisions, action=parse) for ALL users. The login works,
     but the server rejects content retrieval.  This is a server-side policy,
     not a script bug.

     The script will log in successfully, detect the block, and fall back
     to HTML page scraping automatically.
"""

family = 'mgp'
mylang = 'mgp'

# ---------------------------------------------------------------------------
# Custom family — points to Moegirlpedia's API endpoint.
# Pywikibot will auto-generate a family class from this URL.
# ---------------------------------------------------------------------------
family_files['mgp'] = 'https://zh.moegirl.org.cn/api.php'

# ---------------------------------------------------------------------------
# Username
# ---------------------------------------------------------------------------
# Set this to YOUR Moegirlpedia username (e.g. 'MyBotAccount').
# Leave as-is or use an empty string to run anonymously (HTML fallback mode).
usernames['mgp']['mgp'] = 'MoeMoe1564364'

# ---------------------------------------------------------------------------
# Password file (optional — only needed for authenticated API access)
# ---------------------------------------------------------------------------
# Point to the file that stores your password / bot password.
# Copy user-password.py.example → user-password.py and fill in your
# credentials before enabling this.
password_file = 'user-password.py'

# ---------------------------------------------------------------------------
# Throttle & lag
# ---------------------------------------------------------------------------
put_throttle = 10   # Min seconds between writes (read-only, not relevant)
maxlag = 5          # Wait if site replication lag exceeds this (seconds)
