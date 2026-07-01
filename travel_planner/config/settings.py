# ── Azure AI Foundry ──────────────────────────────────────────────────────────
AZURE_ENDPOINT   = "https://proj-app.services.ai.azure.com/openai/v1"
AZURE_DEPLOYMENT = "DeepSeek-V3.2"
AZURE_SCOPE      = "https://ai.azure.com/.default"

# ── Tavily ────────────────────────────────────────────────────────────────────
TAVILY_MAX_RESULTS  = 5
TAVILY_SEARCH_DEPTH = "advanced"   # "basic" | "advanced"

# ── Active prompt versions — change here to switch globally ───────────────────
ACTIVE_PROMPT_VERSIONS = {
    "supervisor":      "v1",
    "places":          "v1",
    "itinerary":       "v1",
    "recommendations": "v1",
    "formatter":       "v1",
}

# ── App UI ────────────────────────────────────────────────────────────────────
APP_TITLE      = "AI Travel Planner"
APP_ICON       = "✈️"
APP_LAYOUT     = "wide"
SIDEBAR_TITLE  = "🗺️ My Trips"
NEW_TRIP_LABEL = "➕ Plan a New Trip"
THREAD_ID_LEN  = 8

# ── User preference options ───────────────────────────────────────────────────
TRIP_STYLES = [
    "Cultural & Historic",
    "Adventure & Outdoors",
    "Food & Culinary",
    "Relaxed & Leisure",
    "Luxury",
    "Budget Backpacker",
]
TRAVEL_GROUPS      = ["Solo", "Couple", "Family with Kids", "Group of Friends"]
BUDGETS            = ["Budget ($)", "Mid-range ($$)", "Luxury ($$$)"]
PACES              = ["Slow & Leisurely", "Moderate", "Fast-paced (see everything)"]
ACCOMMODATION_TYPES = ["Hotel", "Boutique / B&B", "Hostel", "Airbnb / Apartment", "Resort"]

# ── Sidebar static text ───────────────────────────────────────────────────────
HOW_IT_WORKS = (
    "1. **Supervisor** — parses your query & preferences\n"
    "2. **Places Agent** — finds real spots via Tavily\n"
    "3. **Itinerary Agent** — builds your day-by-day plan\n"
    "4. **Recommendations Agent** — visa, weather & tips\n"
    "5. **Formatter** — polishes into a travel guide"
)

# ── Example query chips ───────────────────────────────────────────────────────
EXAMPLE_QUERIES = [
    "5 days in Tokyo",
    "Weekend in Barcelona",
    "10-day New Zealand road trip",
    "3 days in Rome",
]
