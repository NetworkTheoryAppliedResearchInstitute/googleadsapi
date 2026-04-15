#!/usr/bin/env python3
"""
NTARI P2-002 — English Broadcast Campaign Build
Document Reference: P2-002 Implementation Manual v7.0

Builds 3 consolidated English campaigns via the FastAPI batch endpoint.
All campaigns are created PAUSED — review in Google Ads UI before enabling.

Usage:
    python execute_plan.py
    python execute_plan.py --dry-run          # validate configs, no API calls
    python execute_plan.py --campaign 2       # build only campaign #2 (0-indexed)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()

API_BASE    = "http://localhost/api/v1"
API_KEY     = os.getenv("API_SECRET_KEY", "")
CUSTOMER_ID = os.getenv("GOOGLE_ADS_CUSTOMER_ID", "7184173294")

# ── Geo target constant IDs ───────────────────────────────────────────────────
# IDs = 2 + ISO 3166-1 numeric code
# Source: NTARI P2-002 Anglophone Census (March 2026), ~1.5B global reach

# TIER 1 — Core native English-speaking nations
GEO_US  = 2840   # United States      — 302M English speakers
GEO_UK  = 2826   # United Kingdom     — 98.2% proficiency
GEO_CA  = 2124   # Canada             — 87% English speakers
GEO_AU  = 2036   # Australia          — 72% English-only
GEO_NZ  = 2554   # New Zealand        — 95.4% proficiency
GEO_IE  = 2372   # Ireland            — near-universal

# SOUTH ASIA
GEO_IN  = 2356   # India              — 128-265M English speakers
GEO_PK  = 2586   # Pakistan           — 118M (4th largest globally)
GEO_BD  = 2050   # Bangladesh         — ~29M speakers
GEO_LK  = 2144   # Sri Lanka          — 5.2M (23.8%)

# SOUTHEAST ASIA
GEO_PH  = 2608   # Philippines        — ~90M, EF EPI 22nd globally
GEO_SG  = 2702   # Singapore          — 93%+, EF EPI 3rd globally
GEO_MY  = 2458   # Malaysia           — 60-72% proficiency
GEO_HK  = 2344   # Hong Kong          — 46-53% proficiency

# AFRICA — WEST
GEO_NG  = 2566   # Nigeria            — 60M English + 121M Pidgin
GEO_GH  = 2288   # Ghana              — 67% literate English
GEO_CM  = 2120   # Cameroon           — 8.8M English + 14.7M Pidgin
GEO_SL  = 2694   # Sierra Leone       — Krio 97% (de facto national)
GEO_LR  = 2430   # Liberia            — English official
GEO_GM  = 2270   # Gambia             — English official

# AFRICA — EAST
GEO_KE  = 2404   # Kenya              — 60-70%, EF EPI 19th globally
GEO_TZ  = 2834   # Tanzania           — ~7M English speakers
GEO_UG  = 2800   # Uganda             — 39% (~29M speakers)
GEO_RW  = 2646   # Rwanda             — 21% rapidly growing; adopted 2008

# AFRICA — SOUTHERN
GEO_ZA  = 2710   # South Africa       — 50% (~31M) proficiency
GEO_ZW  = 2716   # Zimbabwe           — ~90% — highest proficiency in Africa
GEO_ZM  = 2894   # Zambia             — English official
GEO_MW  = 2454   # Malawi             — English official
GEO_BW  = 2072   # Botswana           — English official
GEO_NA  = 2516   # Namibia            — English official

# MIDDLE EAST
GEO_AE  = 2784   # UAE                — 70-90% functional; de facto business language

# EUROPE (beyond Tier 1)
GEO_MT  = 2470   # Malta              — 88-96% proficiency; official language
GEO_GI  = 2292   # Gibraltar          — 100% English; sole official language

# CARIBBEAN
GEO_JM  = 2388   # Jamaica            — English + Jamaican Patois
GEO_TT  = 2780   # Trinidad & Tobago  — English official
GEO_BB  = 2052   # Barbados           — English + Bajan Creole
GEO_GY  = 2328   # Guyana             — 91% English
GEO_BZ  = 2084   # Belize             — 75% English
GEO_BS  = 2044   # Bahamas            — English + Bahamian Creole
GEO_AG  = 2028   # Antigua & Barbuda  — English official
GEO_BM  = 2060   # Bermuda            — English official
GEO_KY  = 2136   # Cayman Islands     — English official

# OCEANIA
GEO_PG  = 2598   # Papua New Guinea   — Tok Pisin 5-6M speakers
GEO_FJ  = 2242   # Fiji               — English official lingua franca
GEO_SB  = 2090   # Solomon Islands    — Pijin 90%+
GEO_VU  = 2548   # Vanuatu            — trilingual (English/French/Bislama)

# INDIAN OCEAN / ISLANDS
GEO_SC  = 2690   # Seychelles         — English official
GEO_MU  = 2480   # Mauritius          — English official

GEO_ALL = [
    # Tier 1
    GEO_US, GEO_UK, GEO_CA, GEO_AU, GEO_NZ, GEO_IE,
    # South Asia
    GEO_IN, GEO_PK, GEO_BD, GEO_LK,
    # Southeast Asia
    GEO_PH, GEO_SG, GEO_MY, GEO_HK,
    # Africa West
    GEO_NG, GEO_GH, GEO_CM, GEO_SL, GEO_LR, GEO_GM,
    # Africa East
    GEO_KE, GEO_TZ, GEO_UG, GEO_RW,
    # Africa South
    GEO_ZA, GEO_ZW, GEO_ZM, GEO_MW, GEO_BW, GEO_NA,
    # Middle East
    GEO_AE,
    # Europe
    GEO_MT, GEO_GI,
    # Caribbean
    GEO_JM, GEO_TT, GEO_BB, GEO_GY, GEO_BZ, GEO_BS, GEO_AG, GEO_BM, GEO_KY,
    # Oceania
    GEO_PG, GEO_FJ, GEO_SB, GEO_VU,
    # Islands
    GEO_SC, GEO_MU,
]

LANG_EN = [1000]

# Budget allocation per v7.0 manual §12 ($10K/month Ad Grants)
BLOG_BUDGET    = 181_000_000  # micros — 55% → ~$181/day
MISSION_BUDGET =  82_000_000  # micros — 25% → ~$82/day
SUPPORT_BUDGET =  33_000_000  # micros — 10% → ~$33/day

CPC_BID = 2_000_000  # micros — $2.00 Ad Grants hard cap

# ── Helper: build an RSA ───────────────────────────────────────────────────────
def rsa(headlines: list, descriptions: list, final_url: str,
        path1: str = "", path2: str = "") -> dict:
    """headlines[0] is always pinned to HEADLINE_1."""
    hl_list = [
        {"text": headlines[0], "pinned_field": "HEADLINE_1"},
        *[{"text": h} for h in headlines[1:]],
    ]
    desc_list = [{"text": d} for d in descriptions]
    ad: dict = {"headlines": hl_list, "descriptions": desc_list,
                "final_urls": [final_url]}
    if path1:
        ad["path1"] = path1
    if path2:
        ad["path2"] = path2
    return ad

def kw(text: str, match_type: str = "PHRASE") -> dict:
    return {"text": text, "match_type": match_type, "cpc_bid_micros": CPC_BID}

def ag(name: str, keywords: list, ads: list) -> dict:
    return {"name": name, "cpc_bid_micros": CPC_BID,
            "keywords": keywords, "ads": ads}

def campaign(name: str, ad_groups: list, daily_budget_micros: int = BLOG_BUDGET) -> dict:
    return {
        "name": name,
        "daily_budget_micros": daily_budget_micros,
        "bidding_strategy_type": "MANUAL_CPC",
        "geo_target_constant_ids": GEO_ALL,
        "language_constant_ids": LANG_EN,
        "ad_groups": ad_groups,
    }

# ══════════════════════════════════════════════════════════════════════════════
# CAMPAIGN 1 — EN_BlogContent_Search
# Purpose: Drive mission-aligned research & content traffic
# Budget: ~$181/day (55% of Ad Grants allocation)
# ══════════════════════════════════════════════════════════════════════════════
EN_BLOG_CONTENT = campaign("EN_BlogContent_Search", [

    ag("Open Source / AGPL", [
        kw("open source AGPL license"),
        kw("what is open source"),
        kw("AGPL-3 explained"),
        kw("copyleft software license"),
        kw("AGPL vs GPL"),
        kw("open source commons"),
        kw("free software licensing"),
    ], [rsa(
        headlines=[
            "Open Source Explained",          # ≤30 — pinned H1
            "What Is Open Source?",
            "AGPL-3 License Guide",
            "Copyleft Software Licensing",
            "Build the Digital Commons",
            "AGPL vs GPL Compared",
            "Commons-Based Licensing",
            "Open Source Research",
            "NTARI Open Commons",
            "Free Software Licensing",
        ],
        descriptions=[
            "NTARI's research on open source and AGPL-3 licensing — building the digital commons.",
            "Copyleft is foundational to the commons. NTARI's AGPL-3 research. Open access.",
            "Understand AGPL-3 licensing and its role in open commons infrastructure. Free.",
            "Join a global network building open commons. Research, frameworks, tools — all open.",
        ],
        final_url="https://www.ntari.org/post/what-does-open-source-mean",
        path1="Open-Source", path2="AGPL-3",
    )]),

    ag("Mycelium / Decentralized Internet", [
        kw("mycelium network model"),
        kw("decentralized internet design"),
        kw("peer-to-peer network architecture"),
        kw("distributed network commons"),
        kw("beyond platform monopolies"),
        kw("open network infrastructure"),
    ], [rsa(
        headlines=[
            "Mycelium Network Design",        # ≤30 — pinned H1
            "Decentralized Internet",
            "Peer-to-Peer Networks",
            "Distributed Network Models",
            "Beyond Platform Monopolies",
            "Open Network Architecture",
            "Commons Network Research",
            "Decentralized Web Design",
            "NTARI Network Research",
            "Build Open Networks",
        ],
        descriptions=[
            "NTARI research on mycelium-inspired decentralized internet design and peer network models.",
            "Beyond centralized platforms: applied research on distributed, commons-based networks.",
            "How does the internet mirror mycelium? NTARI's open research on network architecture.",
            "Distributed systems, open protocols, and the commons. NTARI applied network research.",
        ],
        final_url="https://www.ntari.org/post/mycelium-and-the-decentralized-internet",
        path1="Networks", path2="Mycelium",
    )]),

    ag("Capital Extraction / Platform Economics", [
        kw("platform capital extraction"),
        kw("digital platform economics"),
        kw("rent extraction platforms"),
        kw("platform monopoly economics"),
        kw("digital commons economics"),
        kw("platform capitalism research"),
    ], [rsa(
        headlines=[
            "Platform Capital Extraction",    # ≤30 — pinned H1
            "Digital Platform Economics",
            "How Platforms Extract Value",
            "Rent Extraction Online",
            "Commons vs Platform Models",
            "Digital Rent Research",
            "Applied Economics Research",
            "NTARI Platform Analysis",
            "Economic Commons Research",
            "Beyond Platform Capitalism",
        ],
        descriptions=[
            "NTARI research on how digital platforms extract capital from producers and communities.",
            "Platform economics and rent extraction: applied research from NTARI's commons team.",
            "Who benefits from digital platforms? NTARI research on value extraction and the commons.",
            "How platform rent extraction undermines the commons. NTARI's applied research. Free.",
        ],
        final_url="https://www.ntari.org/post/capital-extraction",
        path1="Economics", path2="Platforms",
    )]),

    ag("Community Economics / MSP", [
        kw("community economics model"),
        kw("minimum sustainable projection"),
        kw("cooperative economic framework"),
        kw("commons-based economics"),
        kw("local economy commons"),
        kw("community economic design"),
    ], [rsa(
        headlines=[
            "Community Economics Model",      # ≤30 — pinned H1
            "Minimum Sustainable Living",
            "Cooperative Economics",
            "Commons Economic Models",
            "Beyond GDP Economics",
            "Applied Community Finance",
            "Sustaining Communities",
            "NTARI Economics Research",
            "Local Economy Frameworks",
            "Open Economic Research",
        ],
        descriptions=[
            "NTARI's community economics research: minimum sustainable models for cooperative living.",
            "What does sustainable community economics look like? NTARI's applied research. Free.",
            "Beyond GDP: commons-based economic models and minimum sustainable projections. NTARI.",
            "Cooperative economics for local communities. NTARI open research — digital commons.",
        ],
        final_url="https://www.ntari.org/post/community-economics",
        path1="Economics", path2="Community",
    )]),

    ag("Network Economics / Observational Diversity", [
        kw("network economics theory"),
        kw("observational diversity networks"),
        kw("distributed economic networks"),
        kw("applied network economics"),
        kw("network theory applied"),
        kw("economic network research"),
    ], [rsa(
        headlines=[
            "Network Economics Theory",       # ≤30 — pinned H1
            "Observational Diversity",
            "Distributed Economic Nets",
            "Network Theory Economics",
            "Applied Network Research",
            "Economic Network Design",
            "Open Economics Research",
            "NTARI Network Economics",
            "Digital Network Theory",
            "Commons Network Models",
        ],
        descriptions=[
            "NTARI research on network economics and observational diversity in distributed systems.",
            "How do networks shape economic behavior? NTARI's applied theory — open access. Free.",
            "Observational diversity and network economics: NTARI's commons-based research framework.",
            "Applied network theory for economic design. NTARI open research — digital commons.",
        ],
        final_url="https://www.ntari.org/post/network-economics",
        path1="Network", path2="Economics",
    )]),

    ag("Institutional Design / Consul Democracy", [
        kw("consul democracy model"),
        kw("institutional design governance"),
        kw("democratic institution design"),
        kw("commons governance framework"),
        kw("applied governance research"),
        kw("open governance design"),
    ], [rsa(
        headlines=[
            "Institutional Design Guide",     # ≤30 — pinned H1
            "Consul Democracy Model",
            "Democratic Design Research",
            "Governance Institution Design",
            "Open Governance Frameworks",
            "Commons Governance Design",
            "Applied Governance Research",
            "NTARI Governance Research",
            "Design Better Institutions",
            "Resilient Governance Models",
        ],
        descriptions=[
            "NTARI's research on consul democracy and institutional design for open communities.",
            "How do you design durable institutions? NTARI's applied governance research. Free.",
            "Consul democracy and commons governance: frameworks for resilient institutions. NTARI.",
            "Open governance design for the digital age. NTARI applied research — commons-based.",
        ],
        final_url="https://www.ntari.org/post/institutional-design",
        path1="Governance", path2="Design",
    )]),

    ag("Overview Effect / Perspective Shift", [
        kw("overview effect astronaut"),
        kw("cognitive perspective shift"),
        kw("global perspective change"),
        kw("overview effect research"),
        kw("systemic worldview shift"),
        kw("perspective transformation research"),
    ], [rsa(
        headlines=[
            "Overview Effect Research",       # ≤30 — pinned H1
            "Cognitive Perspective Shift",
            "Astronaut Overview Effect",
            "Shifted Worldview Research",
            "Global Perspective Change",
            "Overview Experience Study",
            "Systemic Perspective Shift",
            "NTARI Perspective Research",
            "Applied Cognition Research",
            "Open Mind Research",
        ],
        descriptions=[
            "NTARI's research on the overview effect and how perspective shifts change systems.",
            "What happens when worldview shifts at scale? NTARI's applied perspective research. Free.",
            "The overview effect and systemic cognition: NTARI's open research on perspective change.",
            "How radical perspective shifts transform governance and community. NTARI open research.",
        ],
        final_url="https://www.ntari.org/post/overview-effect",
        path1="Research", path2="Perspective",
    )]),

    ag("Network State / Digital Governance", [
        kw("network state concept"),
        kw("digital governance theory"),
        kw("online nation governance"),
        kw("decentralized state design"),
        kw("digital community governance"),
        kw("network state research"),
    ], [rsa(
        headlines=[
            "Network State Concept",          # ≤30 — pinned H1
            "Digital Governance Theory",
            "Online Nation Governance",
            "Network State Research",
            "Digital Community Design",
            "Decentralized Governance",
            "Applied Digital Governance",
            "NTARI Governance Theory",
            "Build Digital Nations",
            "Commons Digital Governance",
        ],
        descriptions=[
            "NTARI research on network states: digital governance theory for online communities.",
            "What is the network state? NTARI's applied research on digital community governance.",
            "Decentralized governance for digital communities. NTARI open research — commons-based.",
            "Beyond nation-states: applied digital governance theory from NTARI. Open access.",
        ],
        final_url="https://www.ntari.org/post/network-state",
        path1="Governance", path2="Network",
    )]),

    ag("Marine Corps / Developer Discipline", [
        kw("developer discipline principles"),
        kw("engineering team culture"),
        kw("software developer discipline"),
        kw("high performance dev teams"),
        kw("Marine Corps software culture"),
        kw("disciplined engineering culture"),
    ], [rsa(
        headlines=[
            "Developer Discipline Guide",     # ≤30 — pinned H1
            "Marine Corps Dev Culture",
            "Engineering Discipline",
            "Software Team Discipline",
            "NTARI Developer Research",
            "High-Performance Dev Teams",
            "Disciplined Engineering",
            "Applied Developer Culture",
            "Build Better Dev Teams",
            "Open Dev Culture Research",
        ],
        descriptions=[
            "NTARI research on developer discipline: what Marine Corps culture teaches engineers.",
            "High-performance engineering teams and the discipline behind them. NTARI open research.",
            "From Marine Corps to dev culture: NTARI's applied research on engineering discipline.",
            "Build disciplined, high-performing developer teams. NTARI open research — free access.",
        ],
        final_url="https://www.ntari.org/post/marine-corps",
        path1="Dev", path2="Discipline",
    )]),

    ag("What Is Anthropology", [
        kw("what is anthropology"),
        kw("cultural anthropology definition"),
        kw("applied anthropology research"),
        kw("social anthropology explained"),
        kw("digital anthropology"),
        kw("network anthropology theory"),
    ], [rsa(
        headlines=[
            "What Is Anthropology",           # ≤30 — pinned H1
            "Applied Anthropology Guide",
            "Cultural Anthropology",
            "Anthropology Explained",
            "Social Anthropology Research",
            "NTARI Anthropology Research",
            "Human Culture Research",
            "Applied Social Science",
            "Digital Anthropology",
            "Network Anthropology",
        ],
        descriptions=[
            "NTARI's applied anthropology research: cultural frameworks for digital communities.",
            "What is anthropology and why does it matter online? NTARI open research. Free access.",
            "From cultural to digital anthropology: NTARI's commons-based research framework.",
            "Applied social science for network communities. NTARI open research — free access.",
        ],
        final_url="https://www.ntari.org/post/what-is-anthropology",
        path1="Research", path2="Anthropology",
    )]),

    ag("Scientific Method / Knowledge Commons", [
        kw("scientific method commons"),
        kw("knowledge commons research"),
        kw("open science methodology"),
        kw("commons-based research"),
        kw("applied scientific method"),
        kw("open knowledge commons"),
    ], [rsa(
        headlines=[
            "Scientific Method Commons",      # ≤30 — pinned H1
            "Open Science Research",
            "Knowledge Commons Method",
            "Applied Science Research",
            "Open Scientific Research",
            "NTARI Science Research",
            "Commons-Based Science",
            "Research Method Commons",
            "Open Knowledge Research",
            "Scientific Commons Design",
        ],
        descriptions=[
            "NTARI research on the scientific method as a foundation for knowledge commons design.",
            "How does open science build the commons? NTARI's applied methodology research. Free.",
            "Knowledge commons and scientific method: NTARI's open research framework. Free access.",
            "Applied science for the digital commons. NTARI open research — community-governed.",
        ],
        final_url="https://www.ntari.org/post/scientific-method",
        path1="Science", path2="Commons",
    )]),

    ag("Node-Nexus", [
        kw("NTARI research network"),
        kw("digital commons hub"),
        kw("applied research commons"),
        kw("open research network"),
        kw("commons knowledge network"),
        kw("NTARI node nexus"),
    ], [rsa(
        headlines=[
            "NTARI Node Nexus",               # ≤30 — pinned H1
            "Digital Commons Hub",
            "Research Network Node",
            "Open Research Commons",
            "Applied Network Research",
            "NTARI Research Network",
            "Digital Commons Research",
            "Commons Knowledge Hub",
            "Open Collaborative Research",
            "Join the NTARI Network",
        ],
        descriptions=[
            "NTARI's Node-Nexus: the hub for applied digital commons research and open collaboration.",
            "Connect with global commons researchers. NTARI Node-Nexus — open access, AGPL-3.",
            "Applied research, governance frameworks, and open tools. NTARI's digital commons hub.",
            "The Node-Nexus connects researchers, practitioners, and communities. Free to join.",
        ],
        final_url="https://www.ntari.org/node-nexus",
        path1="Node", path2="Nexus",
    )]),

], BLOG_BUDGET)


# ══════════════════════════════════════════════════════════════════════════════
# CAMPAIGN 2 — EN_Mission_Search
# Purpose: Brand awareness, mission discovery, contributor registration
# Budget: ~$82/day (25% of Ad Grants allocation)
# ══════════════════════════════════════════════════════════════════════════════
EN_MISSION = campaign("EN_Mission_Search", [

    ag("Mission / About", [
        kw("NTARI mission"),
        kw("applied network research institute"),
        kw("digital commons research"),
        kw("network theory research"),
        kw("open research institute"),
        kw("SOHO network culture"),
    ], [rsa(
        headlines=[
            "NTARI Applied Research",         # ≤30 — pinned H1
            "Digital Commons Institute",
            "SOHO Network Research",
            "Open Research Institute",
            "Network Theory Research",
            "NTARI Mission & Vision",
            "Applied Commons Research",
            "Who Is NTARI",
            "Digital Commons Mission",
            "Open Science Institute",
        ],
        descriptions=[
            "NTARI builds open digital commons infrastructure — applied research, AGPL-3 licensed.",
            "We are a 501(c)(3) applying network theory to build the digital commons. Open access.",
            "NTARI's mission: applied research for digital commons infrastructure. Free to access.",
            "SOHO network culture, applied research, and open governance. Learn about NTARI.",
        ],
        final_url="https://www.ntari.org/home",
        path1="About", path2="NTARI",
    )]),

    ag("Member Registration / Join", [
        kw("join research network"),
        kw("digital commons membership"),
        kw("NTARI member registration"),
        kw("open research community join"),
        kw("network member registration"),
        kw("join nonprofit network"),
    ], [rsa(
        headlines=[
            "Join the NTARI Network",         # ≤30 — pinned H1
            "Become a Network Member",
            "Digital Commons Membership",
            "Register Free Today",
            "Open Research Community",
            "NTARI Member Benefits",
            "Join Open Research Network",
            "Commons Network Membership",
            "Apply to Join NTARI",
            "Free Network Membership",
        ],
        descriptions=[
            "Register as an NTARI network member. Join the open digital commons — free membership.",
            "Contribute to applied commons research. NTARI membership is free and open. Join now.",
            "Become part of a global commons research network. NTARI member registration is free.",
            "NTARI members collaborate on open research, governance, and digital commons tools.",
        ],
        final_url="https://www.ntari.org/#register",
        path1="Join", path2="NTARI",
    )]),

], MISSION_BUDGET)


# ══════════════════════════════════════════════════════════════════════════════
# CAMPAIGN 3 — EN_Support_Search
# Purpose: Donor acquisition
# Budget: ~$33/day (10% of Ad Grants allocation)
# ══════════════════════════════════════════════════════════════════════════════
EN_SUPPORT = campaign("EN_Support_Search", [

    ag("Donate / Support", [
        kw("support digital commons"),
        kw("donate nonprofit research"),
        kw("fund open source research"),
        kw("give to digital commons"),
        kw("support open research"),
        kw("nonprofit research donation"),
    ], [rsa(
        headlines=[
            "Support the Digital Commons",    # ≤30 — pinned H1
            "Donate to NTARI",
            "Fund Open Research",
            "Support Open Commons",
            "Give to Digital Commons",
            "Nonprofit Commons Research",
            "Fund NTARI Research",
            "Sustain Open Research",
            "Commons Research Donor",
            "NTARI Donation Page",
        ],
        descriptions=[
            "Support NTARI's open digital commons research. 501(c)(3) nonprofit — tax deductible.",
            "Your donation funds open research, governance tools, and digital commons infrastructure.",
            "Help sustain applied commons research. NTARI is a 501(c)(3) — every dollar counts.",
            "Donate to NTARI and support the open digital commons. Free research for everyone.",
        ],
        final_url="https://www.ntari.org/donate",
        path1="Donate", path2="NTARI",
    )]),

], SUPPORT_BUDGET)


# ALL CAMPAIGNS IN BUILD ORDER
# ══════════════════════════════════════════════════════════════════════════════
ALL_CAMPAIGNS = [
    EN_BLOG_CONTENT,
    EN_MISSION,
    EN_SUPPORT,
]

# ══════════════════════════════════════════════════════════════════════════════
# EXECUTION
# ══════════════════════════════════════════════════════════════════════════════
def validate_configs() -> bool:
    """Check all RSA headlines and descriptions stay within character limits."""
    errors = []
    for c in ALL_CAMPAIGNS:
        for ag in c["ad_groups"]:
            for ad in ag.get("ads", []):
                for hl in ad.get("headlines", []):
                    text = hl["text"] if isinstance(hl, dict) else hl
                    if len(text) > 30:
                        errors.append(
                            f"[{c['name']} / {ag['name']}] Headline too long "
                            f"({len(text)} chars): '{text}'"
                        )
                for desc in ad.get("descriptions", []):
                    text = desc["text"] if isinstance(desc, dict) else desc
                    if len(text) > 90:
                        errors.append(
                            f"[{c['name']} / {ag['name']}] Description too long "
                            f"({len(text)} chars): '{text}'"
                        )
    if errors:
        print("\nERROR  Character limit violations found:\n")
        for e in errors:
            print(f"  • {e}")
        return False
    print(f"OK  All {sum(len(c['ad_groups']) for c in ALL_CAMPAIGNS)} ad groups "
          f"validated — no character limit violations.")
    return True


def build_campaign(session: httpx.Client, cfg: dict, index: int, total: int) -> dict:
    print(f"\n[{index}/{total}] Building: {cfg['name']}")
    print(f"         Ad groups: {len(cfg['ad_groups'])}")
    try:
        resp = session.post(
            f"{API_BASE}/customers/{CUSTOMER_ID}/batch/build-campaign",
            params={"ad_grants_account": "true"},
            json=cfg,
            timeout=300,
        )
        resp.raise_for_status()
        result = resp.json()
        status = result.get("status", "UNKNOWN")
        ops    = result.get("operation_count", "?")
        print(f"         Status: {status} | Operations: {ops}")
        return {"campaign": cfg["name"], "success": True, "result": result}
    except httpx.HTTPStatusError as e:
        print(f"         ERROR  HTTP {e.response.status_code}: {e.response.text[:200]}")
        return {"campaign": cfg["name"], "success": False, "error": str(e)}
    except Exception as e:
        print(f"         ERROR  Error: {e}")
        return {"campaign": cfg["name"], "success": False, "error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="NTARI P2-002 Campaign Build")
    parser.add_argument("--dry-run", action="store_true",
                        help="Validate configs only — no API calls")
    parser.add_argument("--campaign", type=int, default=None,
                        help="Build only one campaign by index (0-based)")
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("  NTARI P2-002 - English Broadcast Campaign Build")
    print("  Document: P2-002 Implementation Manual v7.0")
    print("=" * 60)

    # Validate first
    if not validate_configs():
        sys.exit(1)

    if args.dry_run:
        print("\nOK  Dry run complete — all configs valid. No API calls made.")
        print(f"    Campaigns ready: {len(ALL_CAMPAIGNS)}")
        print(f"    Total ad groups: {sum(len(c['ad_groups']) for c in ALL_CAMPAIGNS)}")
        return

    if not API_KEY or API_KEY == "replace-with-a-strong-random-secret":
        print("\nERROR  API_SECRET_KEY not set in .env — cannot proceed.")
        sys.exit(1)

    campaigns_to_build = (
        [ALL_CAMPAIGNS[args.campaign]] if args.campaign is not None
        else ALL_CAMPAIGNS
    )

    print(f"\nCustomer ID : {CUSTOMER_ID}")
    print(f"Campaigns   : {len(campaigns_to_build)}")
    print(f"Ad groups   : {sum(len(c['ad_groups']) for c in campaigns_to_build)}")
    print("\nAll campaigns will be created PAUSED.")
    print("Review in Google Ads UI before enabling.\n")

    with httpx.Client(headers={"X-API-Key": API_KEY}) as session:
        results = []
        total = len(campaigns_to_build)
        for i, cfg in enumerate(campaigns_to_build, 1):
            result = build_campaign(session, cfg, i, total)
            results.append(result)
            if i < total:
                time.sleep(2)  # brief pause between batch jobs

    # Summary
    succeeded = [r for r in results if r["success"]]
    failed    = [r for r in results if not r["success"]]

    print("\n" + "=" * 60)
    print(f"  BUILD COMPLETE: {len(succeeded)}/{total} campaigns succeeded")
    print("=" * 60)
    if failed:
        print("\nFailed campaigns:")
        for r in failed:
            print(f"  • {r['campaign']}: {r.get('error', 'unknown error')}")

    print("\nNEXT  NEXT STEPS:")
    print("  1. Review campaigns in Google Ads UI (all are PAUSED)")
    print("  2. Add account-level negative keywords")
    print("  3. Link GA4 and verify conversion tracking is firing")
    print("  4. Enable campaigns one at a time — start with EN_BlogContent_Search")
    print("  5. Monitor CTR daily for first 2 weeks — must stay above 5%\n")

    # Save results to file
    out = Path("campaigns/build_results.json")
    out.write_text(json.dumps(results, indent=2, default=str))
    print(f"  Full results saved to: {out}\n")


if __name__ == "__main__":
    main()
