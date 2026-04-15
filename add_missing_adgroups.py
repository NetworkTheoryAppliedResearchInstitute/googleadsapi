#!/usr/bin/env python3
"""Add the 6 missing ad groups to EN_Projects_Search campaign."""

import httpx, os, time
from dotenv import load_dotenv

load_dotenv()

API_BASE    = "http://localhost/api/v1"
API_KEY     = os.getenv("API_SECRET_KEY", "")
CUSTOMER_ID = os.getenv("GOOGLE_ADS_CUSTOMER_ID", "")
CAMPAIGN_ID = "23708771733"  # EN_Projects_Search
CPC_BID     = 2_000_000

HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

MISSING_AD_GROUPS = [
    {
        "name": "SOHOLink Platform",
        "keywords": [
            "SOHO network link", "distributed contributor platform",
            "SOHO community network", "remote contributor tools",
            "SOHOLink NTARI", "SOHO contributor platform",
            "distributed SOHO tools", "SOHO network platform",
        ],
        "headlines": [
            "SOHOLink Platform",
            "Distributed Contributor Tools",
            "SOHO Community Network",
            "Remote Contributor Platform",
            "SOHOLink — Connect & Build",
            "NTARI SOHOLink Project",
            "SOHO Network Platform",
            "Build SOHO Contributor Network",
            "Commons Contributor Tools",
            "Join SOHOLink",
        ],
        "descriptions": [
            "SOHOLink is NTARI's platform for connecting SOHO contributors — tools and governance.",
            "Remote and home-office contributors need dedicated infrastructure. SOHOLink provides this.",
            "SOHOLink connects SOHO contributors globally in a community-governed, AGPL-3 platform.",
            "From tools to governance: SOHOLink is NTARI's SOHO contributor ecosystem project. Free.",
        ],
        "final_url": "https://ntari.org/projects#soholink",
        "path1": "SOHOLink", "path2": "Platform",
    },
    {
        "name": "MCAS Community Assessment",
        "keywords": [
            "MCAS NTARI", "community assessment system",
            "commons metrics", "network community analytics",
            "community assessment framework", "commons measurement system",
            "community metrics framework", "open source community assessment",
        ],
        "headlines": [
            "MCAS Community Assessment",
            "Commons Metrics Framework",
            "Network Community Analytics",
            "Assess Your Community",
            "MCAS — NTARI Project",
            "Open Community Metrics",
            "Commons Assessment Tools",
            "Measure Network Communities",
            "NTARI MCAS System",
            "Community Analytics Framework",
        ],
        "descriptions": [
            "NTARI's MCAS provides frameworks for assessing the health and governance of commons.",
            "How do you measure a commons community? MCAS provides metrics and assessment tools. Free.",
            "Open source community assessment for distributed networks. MCAS is NTARI's analytics tool.",
            "Access MCAS — NTARI's system for measuring network health, contributor engagement.",
        ],
        "final_url": "https://ntari.org/projects#mcas",
        "path1": "MCAS", "path2": "Assessment",
    },
    {
        "name": "Lighthouse Navigation Framework",
        "keywords": [
            "Lighthouse NTARI", "digital commons guidance",
            "open knowledge navigation", "commons research framework",
            "knowledge navigation system", "digital commons navigation",
            "open research navigation", "commons knowledge guidance",
        ],
        "headlines": [
            "Lighthouse Knowledge Framework",
            "Navigate Digital Commons",
            "Open Knowledge Navigation",
            "Lighthouse — NTARI Project",
            "Commons Research Guidance",
            "Digital Commons Navigation",
            "NTARI Lighthouse Initiative",
            "Navigate Open Research",
            "Knowledge Commons Guidance",
            "Light the Way — Open Research",
        ],
        "descriptions": [
            "NTARI's Lighthouse develops navigation frameworks for the digital commons. Free access.",
            "The commons is vast. Lighthouse provides frameworks for navigating open research. Free.",
            "Open knowledge navigation for practitioners. Lighthouse is NTARI's commons framework.",
            "Access Lighthouse — NTARI's project making digital commons research discoverable. Free.",
        ],
        "final_url": "https://ntari.org/projects#lighthouse",
        "path1": "Lighthouse", "path2": "Commons",
    },
    {
        "name": "AgriNet Agricultural Commons",
        "keywords": [
            "AgriNet NTARI", "agricultural commons network",
            "open source agriculture network", "cooperative farming technology",
            "agricultural commons technology", "open source farming network",
            "cooperative agriculture commons", "rural commons technology",
        ],
        "headlines": [
            "AgriNet Agricultural Commons",
            "Open Source Farming Network",
            "Cooperative Agriculture Tech",
            "Agricultural Commons Research",
            "AgriNet — NTARI Project",
            "Open Farming Infrastructure",
            "Rural Commons Technology",
            "NTARI AgriNet Initiative",
            "Agriculture & the Commons",
            "Build Cooperative Farm Network",
        ],
        "descriptions": [
            "NTARI's AgriNet develops commons-based technology frameworks for cooperative farming.",
            "Open source agriculture needs commons infrastructure. AgriNet addresses cooperative farms.",
            "AgriNet connects agricultural researchers, farmers, and rural tech advocates via commons.",
            "Access NTARI's AgriNet — frameworks for cooperative agricultural commons. AGPL-3. Free.",
        ],
        "final_url": "https://ntari.org/projects#agrinet",
        "path1": "AgriNet", "path2": "Commons",
    },
    {
        "name": "COER Commons Open Education",
        "keywords": [
            "commons open education", "COER NTARI",
            "open educational resources commons", "OER commons platform",
            "commons open education resource", "open education commons",
            "OER commons governance", "community open education resource",
        ],
        "headlines": [
            "Commons Open Education",
            "COER — Open Education",
            "OER Commons Platform",
            "Open Education for the Commons",
            "COER — NTARI Project",
            "Free Open Education Resources",
            "Govern Open Education Commons",
            "NTARI COER Initiative",
            "Education Belongs to Everyone",
            "Open Educational Resources",
        ],
        "descriptions": [
            "NTARI's COER develops open educational resources for the commons — freely available.",
            "Education is a commons resource. COER provides frameworks for community-governed OER.",
            "Open educational resources need governance. COER addresses OER commons design. Free.",
            "Access NTARI's COER — open education resources for commons practitioners and researchers.",
        ],
        "final_url": "https://ntari.org/projects#coer",
        "path1": "COER", "path2": "Education",
    },
    {
        "name": "LBTAS Local Business Support",
        "keywords": [
            "LBTAS NTARI", "local business technology assistance",
            "small business commons support", "local economic commons",
            "small business technology commons", "local business digital commons",
            "community business technology", "local economic development commons",
        ],
        "headlines": [
            "Local Business Tech Assistance",
            "LBTAS — NTARI Project",
            "Small Business Commons Support",
            "Local Economic Commons",
            "Community Business Technology",
            "LBTAS Local Tech Assistance",
            "NTARI LBTAS Initiative",
            "Support Local Business Commons",
            "Local Economic Development",
            "Tech Assistance for Community",
        ],
        "descriptions": [
            "NTARI's LBTAS provides technology assistance for local businesses in commons-based models.",
            "Small businesses need commons-compatible technology. LBTAS delivers open frameworks.",
            "From local business commons to community economic development: LBTAS bridges tech.",
            "Access NTARI's LBTAS — local business technology assistance rooted in commons governance.",
        ],
        "final_url": "https://ntari.org/projects#lbtas",
        "path1": "LBTAS", "path2": "Local",
    },
]


# Ad groups already created in previous partial runs
EXISTING_AG_IDS = {
    "SOHOLink Platform": "193709188503",       # RSA + keywords already added
    "MCAS Community Assessment": "198711929167",  # keywords partially added, need RSA
}

# Ad groups that are fully complete (skip entirely)
COMPLETED_AG_NAMES = {
    "SOHOLink Platform",
    "MCAS Community Assessment",
    "Lighthouse Navigation Framework",
    "AgriNet Agricultural Commons",
}

# Ad groups where keywords are done but RSA still needed
SKIP_KEYWORDS_FOR = {
    "MCAS Community Assessment",
}

def add_keyword(s, ag_id, kw_text):
    for attempt in range(3):
        r = s.post(f"{API_BASE}/customers/{CUSTOMER_ID}/keywords/", json={
            "ad_group_id": ag_id,
            "keyword_text": kw_text,
            "match_type": "PHRASE",
            "cpc_bid_micros": CPC_BID,
        })
        if r.status_code == 503:
            print(f"  503 on keyword '{kw_text}', retrying in 3s...")
            time.sleep(3)
            continue
        r.raise_for_status()
        return
    raise RuntimeError(f"Failed to add keyword after 3 attempts: {kw_text}")


def run():
    with httpx.Client(headers=HEADERS, timeout=120) as s:
        for ag in MISSING_AD_GROUPS:
            if ag["name"] in COMPLETED_AG_NAMES:
                print(f"\nSkipping (already complete): {ag['name']}")
                continue
            print(f"\nProcessing ad group: {ag['name']}")

            # 1. Create ad group (or reuse if already created)
            if ag["name"] in EXISTING_AG_IDS:
                ag_id = EXISTING_AG_IDS[ag["name"]]
                print(f"  Ad group already exists: {ag_id}")
            else:
                for attempt in range(3):
                    r = s.post(f"{API_BASE}/customers/{CUSTOMER_ID}/ad-groups/", json={
                        "campaign_id": CAMPAIGN_ID,
                        "name": ag["name"],
                        "cpc_bid_micros": CPC_BID,
                    })
                    if r.status_code == 503:
                        print(f"  503 creating ad group, retrying in 3s...")
                        time.sleep(3)
                        continue
                    r.raise_for_status()
                    break
                ag_id = r.json()["ad_group_id"]
                print(f"  Ad group created: {ag_id}")

            # 2. Add keywords
            if ag["name"] in SKIP_KEYWORDS_FOR:
                print(f"  Keywords already added (skipping)")
            else:
                for kw_text in ag["keywords"]:
                    add_keyword(s, ag_id, kw_text)
                print(f"  Keywords added: {len(ag['keywords'])}")

            # 3. Create RSA
            hl_list = [
                {"text": ag["headlines"][0], "pinned_field": "HEADLINE_1"},
                *[{"text": h} for h in ag["headlines"][1:]],
            ]
            rsa_payload = {
                "ad_group_id": ag_id,
                "headlines": hl_list,
                "descriptions": [{"text": d} for d in ag["descriptions"]],
                "final_urls": [ag["final_url"]],
                "path1": ag.get("path1", ""),
                "path2": ag.get("path2", ""),
            }
            r = s.post(f"{API_BASE}/customers/{CUSTOMER_ID}/ads/", json=rsa_payload)
            r.raise_for_status()
            print(f"  RSA created: {r.json().get('ad_id', 'ok')}")

    print("\nDone — all 6 missing ad groups added to EN_Projects_Search.")


if __name__ == "__main__":
    run()
