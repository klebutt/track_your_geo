"""Built-in demo pilots (real brand names).

GEO probes use **brand-neutral** prompts only: the question must not name the
tracked brand, so visibility reflects whether the model brings the brand up on
its own (closer to organic user queries). More probes = smoother sampling of
that behaviour at higher API cost.
"""

HARDCODED_PILOT_SPECS: list[dict] = [
    {
        "id": "dishoom-london",
        "brand_name": "Dishoom",
        "location": "London, UK",
        "competitors": ["The Ivy", "Hawksmoor", "Gaucho"],
        "queries": [
            "What are the best restaurants for a business dinner in {location}? Mention specific names.",
            "Top 5 casual dining spots in {location} — list brands or restaurant names.",
            "Where should I take a team of 8 for lunch near the City of London?",
            "Best places for late dinner after theatre in {location}.",
            "I'm visiting {location} and want a buzzy Indian or South Asian restaurant — what do people recommend? Name venues.",
            "Quiet restaurants in central London good for a client dinner — list a few with names.",
            "Best spots in {location} for a long weekend brunch with friends; name actual restaurants.",
            "Popular Indian restaurants in {location} for first-time visitors — name a few specific venues.",
            "Hen party dinner in central London — fun atmosphere, not too expensive. What are good options by name?",
            "Best restaurants near Covent Garden for pre-theatre dining; I need names not just areas.",
        ],
        "seed_domains": ["example-travel.com", "example-foodguide.co.uk"],
        "brand_domains": ["dishoom.com"],
    },
    {
        "id": "clio-uk",
        "brand_name": "Clio",
        "location": "United Kingdom",
        "competitors": ["Actionstep", "Smokeball", "LEAP Legal Software"],
        "queries": [
            "What is the best CRM for small UK law firms in 2026? Name products.",
            "Compare leading legal practice management tools available in the {location} market.",
            "Which tools do UK solicitors use for case management and billing?",
            "Top options for compliance-heavy legal workflows — name vendors.",
            "If I am opening a 10-person law firm, what software stack should I consider?",
            "Best cloud-based practice management for UK conveyancing firms — name products people actually use.",
            "Legal billing and time recording software for UK firms: what are the main players?",
            "Case management software for high-street solicitors in England and Wales — list top options by name.",
            "Document automation and templates for small law firms in the UK — which vendors come up most?",
            "Replacing legacy on-premise legal software with something modern in the UK — what should I shortlist?",
        ],
        "seed_domains": ["example-legaltech.io", "lawgazette.example"],
        "brand_domains": ["clio.com"],
    },
    {
        "id": "sdl-surveying-uk",
        "brand_name": "SDL Surveying",
        "location": "United Kingdom",
        "competitors": ["e.surv", "Countrywide Home Surveys", "RightSurvey"],
        "queries": [
            "What are the best companies for a RICS Level 2 homebuyer survey in England? Name specific firms.",
            "Who should I use for a RICS Level 3 building survey before buying a house in the UK? List providers by name.",
            "Compare leading residential property surveying firms in the {location} — name companies people recommend.",
            "I'm buying my first home in the UK — which RICS chartered surveyors do buyers mention most often?",
            "Best ways to get quotes for a pre-purchase home survey in the UK — name websites or brands.",
            "Snagging survey providers for new-build homes in England and Wales — who are the main players?",
            "How do I choose a surveyor for a house purchase survey? Name reputable UK firms.",
            "RICS surveyors for older or listed properties in the UK — which specialists should I shortlist?",
            "Independent surveyors versus estate-agent recommended surveyors in the UK — who are trusted names?",
            "Mortgage valuation versus full structural survey in the UK — which surveying companies should I consider?",
        ],
        "seed_domains": ["rics.org", "hoa.org.uk"],
        "brand_domains": ["sdlsurveying.co.uk"],
    },
]
