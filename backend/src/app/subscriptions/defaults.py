"""Built-in subscription services, seeded on first startup.

(name, keyword, type) — keyword is matched case-insensitively against the
transaction description. Users can add/remove rules from the Subscriptions page.
"""
DEFAULT_SUBSCRIPTION_RULES = [
    # OTT / streaming video
    ("Netflix", "NETFLIX", "OTT"),
    ("Amazon Prime", "PRIME VIDEO", "OTT"),
    ("Disney+ Hotstar", "HOTSTAR", "OTT"),
    ("JioCinema", "JIOCINEMA", "OTT"),
    ("SonyLIV", "SONYLIV", "OTT"),
    ("Zee5", "ZEE", "OTT"),
    ("YouTube", "YOUTUBE", "OTT"),
    # Music
    ("Spotify", "SPOTIFY", "Music"),
    ("Apple", "APPLE", "Music"),
    ("Gaana", "GAANA", "Music"),
    # AI tools
    ("Claude / Anthropic", "ANTHROPIC", "AI"),
    ("Claude", "CLAUDE", "AI"),
    ("ChatGPT / OpenAI", "OPENAI", "AI"),
    ("ChatGPT", "CHATGPT", "AI"),
    ("Perplexity", "PERPLEXITY", "AI"),
    ("Cursor", "CURSOR", "AI"),
    ("GitHub Copilot", "COPILOT", "AI"),
    ("Midjourney", "MIDJOURNEY", "AI"),
    ("Gemini", "GEMINI", "AI"),
    # Productivity / creative
    ("Notion", "NOTION", "Productivity"),
    ("Canva", "CANVA", "Productivity"),
    ("Adobe", "ADOBE", "Productivity"),
    ("GitHub", "GITHUB", "Productivity"),
    ("LinkedIn", "LINKEDIN", "Productivity"),
    # Cloud storage
    ("Google One", "GOOGLE ONE", "Cloud"),
    ("iCloud", "ICLOUD", "Cloud"),
    ("Dropbox", "DROPBOX", "Cloud"),
]
