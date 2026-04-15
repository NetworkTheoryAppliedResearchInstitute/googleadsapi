#!/usr/bin/env python3
"""
NTARI P2-002 — Claude Benefit Ad Group
Document Reference: P2-002 Implementation Manual v7.0

Adds the "AI Research Tools / Claude Access" ad group to the existing
EN_Mission_Search campaign. Framing is mission-first (membership benefit),
not commercial, to comply with Google Ad Grants content policy.

Destination: https://ntari.org/#register
"""

from __future__ import annotations

import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv()

API_BASE    = "http://localhost/api/v1"
API_KEY     = os.getenv("API_SECRET_KEY", "")
CUSTOMER_ID = os.getenv("GOOGLE_ADS_CUSTOMER_ID", "3038760876")
CPC_BID     = 2_000_000   # $2.00 Ad Grants cap

MISSION_CAMPAIGN_NAME = "EN_Mission_Search"
FINAL_URL             = "https://ntari.org/#register"

HEADLINES = [
    {"text": "AI Research Tools Included",  "pinned_field": "HEADLINE_1"},
    {"text": "Join & Access Claude AI"},
    {"text": "NTARI Member AI Benefits"},
    {"text": "Claude AI for Researchers"},
    {"text": "Member Research AI Tools"},
    {"text": "AI Access with Membership"},
    {"text": "Research Network + AI"},
    {"text": "Join NTARI - AI Included"},
    {"text": "Open Research + Claude AI"},
    {"text": "Member-Rate Claude Access"},
]

DESCRIPTIONS = [
    {"text": "NTARI members access Claude AI at member rates - join the open research network free."},
    {"text": "Register as an NTARI member and unlock Claude AI for applied commons research."},
    {"text": "Free NTARI membership includes member-rate access to Claude AI for open research."},
    {"text": "Join NTARI's network. Members get Claude AI access at exclusive member rates."},
]

KEYWORDS = [
    "NTARI Claude access",
    "Claude AI membership benefit",
    "AI research tools membership",
    "join research network AI",
    "Claude AI member access",
    "nonprofit AI research tools",
    "AI tools research network",
]


def find_campaign_id(session: httpx.Client) -> str:
    resp = session.get(f"{API_BASE}/customers/{CUSTOMER_ID}/campaigns/")
    resp.raise_for_status()
    for c in resp.json():
        if c["name"] == MISSION_CAMPAIGN_NAME:
            return c["campaign_id"]
    raise RuntimeError(f"Campaign '{MISSION_CAMPAIGN_NAME}' not found.")


def create_ad_group(session: httpx.Client, campaign_id: str) -> str:
    resp = session.post(
        f"{API_BASE}/customers/{CUSTOMER_ID}/ad-groups/",
        json={
            "campaign_id": campaign_id,
            "name": "AI Research Tools / Claude Access",
            "cpc_bid_micros": CPC_BID,
            "status": "ENABLED",
        },
        timeout=30,
    )
    resp.raise_for_status()
    ag_id = resp.json()["ad_group_id"]
    print(f"  Ad group created: {ag_id}")
    return ag_id


def add_keywords(session: httpx.Client, ag_id: str) -> None:
    added = 0
    for kw_text in KEYWORDS:
        resp = session.post(
            f"{API_BASE}/customers/{CUSTOMER_ID}/keywords/",
            json={
                "ad_group_id": ag_id,
                "keyword_text": kw_text,
                "match_type": "PHRASE",
                "cpc_bid_micros": CPC_BID,
                "status": "ENABLED",
            },
            timeout=30,
        )
        resp.raise_for_status()
        added += 1
        print(f"  Added: {kw_text}")
    print(f"  {added}/{len(KEYWORDS)} keywords added.")


def create_rsa(session: httpx.Client, ag_id: str) -> None:
    resp = session.post(
        f"{API_BASE}/customers/{CUSTOMER_ID}/ads/",
        json={
            "ad_group_id": ag_id,
            "headlines": HEADLINES,
            "descriptions": DESCRIPTIONS,
            "final_urls": [FINAL_URL],
            "path1": "Join",
            "path2": "AI-Access",
            "status": "PAUSED",
        },
        timeout=30,
    )
    resp.raise_for_status()
    print(f"  RSA created: {resp.json()['ad_id']}")


def main():
    print("\n" + "=" * 60)
    print("  NTARI — Claude Benefit Ad Group")
    print("  Adding to: EN_Mission_Search")
    print("=" * 60)

    if not API_KEY:
        print("ERROR  API_SECRET_KEY not set in .env")
        sys.exit(1)

    with httpx.Client(headers={"X-API-Key": API_KEY}) as session:
        print(f"\n1. Finding {MISSION_CAMPAIGN_NAME}...")
        campaign_id = find_campaign_id(session)
        print(f"   Campaign ID: {campaign_id}")

        print("\n2. Creating ad group...")
        ag_id = create_ad_group(session, campaign_id)

        print("\n3. Adding keywords...")
        add_keywords(session, ag_id)

        print("\n4. Creating RSA...")
        create_rsa(session, ag_id)

    print("\n" + "=" * 60)
    print("  DONE")
    print("=" * 60)
    print("\nNext steps:")
    print("  - Review ad group in Google Ads UI under EN_Mission_Search")
    print("  - Confirm RSA copy before enabling the campaign")
    print(f"  - Destination: {FINAL_URL}\n")


if __name__ == "__main__":
    main()
