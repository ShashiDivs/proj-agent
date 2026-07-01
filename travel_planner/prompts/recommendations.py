VERSIONS = {
    "v1": {
        "search_visa":     "visa requirements and entry rules for visiting {destination}",
        "search_weather":  "best time to visit {destination} weather climate seasons",
        "search_safety":   "safety tips and local customs etiquette in {destination}",
        "search_currency": "currency payment methods and budget tips in {destination}",
        "system": (
            "You are a seasoned travel advisor. Summarise the research into clear, actionable tips "
            "under these headings: 📋 Visa & Entry | 🌤️ Best Time & Weather | "
            "🛡️ Safety & Local Customs | 💰 Currency & Budget | 🎒 Packing Tips. "
            "Keep each section to 3–5 bullet points. "
            "Tailor advice for a {travel_group} on a {budget} budget."
        ),
        "user": (
            "Destination: {destination}\n"
            "Travel group: {travel_group}\n"
            "Budget: {budget}\n\n"
            "Research data:\n{raw_tips}"
        ),
    },
    "v2": {
        "search_visa":     "entry visa passport requirements {destination} tourists",
        "search_weather":  "{destination} weather by month best season to visit",
        "search_safety":   "{destination} tourist safety local laws customs tipping",
        "search_currency": "{destination} local currency cash vs card ATM fees budget traveller",
        "system": (
            "You are a practical travel expert. Convert raw research into crisp, scannable tips. "
            "Use emoji headers: 📋 Visa & Entry | 🌤️ Weather | 🛡️ Safety | 💰 Money | 🎒 Packing. "
            "Customise for a {travel_group} group on a {budget} budget. Bullet points only."
        ),
        "user": (
            "Destination: {destination} | Group: {travel_group} | Budget: {budget}\n\n"
            "Raw research:\n{raw_tips}"
        ),
    },
}
