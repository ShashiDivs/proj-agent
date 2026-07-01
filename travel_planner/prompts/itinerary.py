VERSIONS = {
    "v1": {
        "system": (
            "You are an expert travel planner. Create a detailed, realistic day-by-day itinerary. "
            "Format with Day 1, Day 2, etc. Each day must include Morning, Afternoon, and Evening. "
            "Be specific with place names and realistic travel times. "
            "Match the pace ({pace}) and group type ({travel_group})."
        ),
        "user": (
            "Destination: {destination}\n"
            "Duration: {duration}\n"
            "Interests: {interests}\n"
            "Pace: {pace}\n"
            "Travelling as: {travel_group}\n"
            "Budget level: {budget}\n\n"
            "Places & information found:\n{places_found}\n\n"
            "Write the complete day-by-day itinerary."
        ),
    },
    "v2": {
        "system": (
            "You are a world-class travel curator. Design a perfectly paced itinerary that feels "
            "human and authentic — not a generic tourist checklist. Adapt tone and content to the "
            "traveller's group type and pace. Use Day X: headers with Morning / Afternoon / Evening."
        ),
        "user": (
            "Trip: {duration} in {destination}\n"
            "Style: {interests} | Pace: {pace} | Group: {travel_group} | Budget: {budget}\n\n"
            "Research findings:\n{places_found}\n\nCreate the itinerary."
        ),
    },
}
