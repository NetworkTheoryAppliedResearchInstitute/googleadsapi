#!/usr/bin/env python3
"""
NTARI P2-002 — Full Anglophone Geo Expansion
Document Reference: P2-002 Implementation Manual v7.0

Patches the 3 v7.0 campaigns with the complete Anglophone geo-target list.
The campaigns were built with 6 Tier 1 countries; this script adds all
remaining countries from the NTARI Anglophone Census (March 2026).

Usage:
    python add_geo_targets.py           # patch all 3 v7.0 campaigns
    python add_geo_targets.py --dry-run # print what would be sent, no API calls
"""

from __future__ import annotations

import argparse
import os
import time

import httpx
from dotenv import load_dotenv

load_dotenv()

API_BASE    = "http://localhost/api/v1"
API_KEY     = os.getenv("API_SECRET_KEY", "")
CUSTOMER_ID = os.getenv("GOOGLE_ADS_CUSTOMER_ID", "3038760876")

# ── Campaigns to target (v7.0 names) ──────────────────────────────────────────
V7_CAMPAIGN_NAMES = {
    "EN_BlogContent_Search",
    "EN_Mission_Search",
    "EN_Support_Search",
}

# ── Geo IDs already applied at campaign creation (Tier 1) ─────────────────────
TIER_1_APPLIED = {2840, 2826, 2124, 2036, 2554, 2372}

# ── Full Anglophone geo target list (IDs = 2 + ISO 3166-1 numeric) ────────────
# Source: NTARI Anglophone Census March 2026 — ~1.5B global reach
NEW_GEO_TARGETS = [
    # South Asia
    (2356, "India"),
    (2586, "Pakistan"),
    (2050, "Bangladesh"),
    (2144, "Sri Lanka"),
    # Southeast Asia
    (2608, "Philippines"),
    (2702, "Singapore"),
    (2458, "Malaysia"),
    (2344, "Hong Kong"),
    # Africa — West
    (2566, "Nigeria"),
    (2288, "Ghana"),
    (2120, "Cameroon"),
    (2694, "Sierra Leone"),
    (2430, "Liberia"),
    (2270, "Gambia"),
    # Africa — East
    (2404, "Kenya"),
    (2834, "Tanzania"),
    (2800, "Uganda"),
    (2646, "Rwanda"),
    # Africa — Southern
    (2710, "South Africa"),
    (2716, "Zimbabwe"),
    (2894, "Zambia"),
    (2454, "Malawi"),
    (2072, "Botswana"),
    (2516, "Namibia"),
    # Middle East
    (2784, "UAE"),
    # Europe
    (2470, "Malta"),
    (2292, "Gibraltar"),
    # Caribbean
    (2388, "Jamaica"),
    (2780, "Trinidad & Tobago"),
    (2052, "Barbados"),
    (2328, "Guyana"),
    (2084, "Belize"),
    (2044, "Bahamas"),
    (2028, "Antigua & Barbuda"),
    (2060, "Bermuda"),
    (2136, "Cayman Islands"),
    # Oceania
    (2598, "Papua New Guinea"),
    (2242, "Fiji"),
    (2090, "Solomon Islands"),
    (2548, "Vanuatu"),
    # Indian Ocean / Islands
    (2690, "Seychelles"),
    (2480, "Mauritius"),
]


def get_v7_campaign_ids(session: httpx.Client) -> dict[str, str]:
    """List campaigns and return {name: campaign_id} for the 3 v7.0 campaigns."""
    resp = session.get(f"{API_BASE}/customers/{CUSTOMER_ID}/campaigns/")
    resp.raise_for_status()
    campaigns = resp.json()
    found = {}
    for c in campaigns:
        if c["name"] in V7_CAMPAIGN_NAMES:
            found[c["name"]] = c["campaign_id"]
    return found


def add_geo_target(session: httpx.Client, campaign_id: str, geo_id: int,
                   country: str, dry_run: bool) -> str:
    """POST a single geo target to a campaign. Returns 'ok', 'skip', or 'error:...'
    Retries up to 4 times on 503 with exponential backoff.
    """
    if geo_id in TIER_1_APPLIED:
        return "skip"  # already applied at campaign creation

    payload = {
        "campaign_id": campaign_id,
        "geo_target_constant_id": geo_id,
        "polarity": "POSITIVE",
    }

    if dry_run:
        print(f"    [DRY RUN] Would add {country} ({geo_id}) -> campaign {campaign_id}")
        return "ok"

    max_attempts = 4
    delay = 2.0
    for attempt in range(max_attempts):
        try:
            resp = session.post(
                f"{API_BASE}/customers/{CUSTOMER_ID}/targeting/geo",
                json=payload,
                timeout=60,
            )
            if resp.status_code == 201:
                return "ok"
            elif resp.status_code == 503 and attempt < max_attempts - 1:
                time.sleep(delay)
                delay *= 2  # exponential backoff
                continue
            else:
                return f"error:{resp.status_code} {resp.text[:80]}"
        except Exception as e:
            if attempt < max_attempts - 1:
                time.sleep(delay)
                delay *= 2
                continue
            return f"error:{e}"
    return "error:max retries exceeded"


def main():
    parser = argparse.ArgumentParser(description="NTARI Anglophone Geo Expansion")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be sent — no API calls")
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("  NTARI P2-002 — Anglophone Geo Expansion")
    print("  Adding", len(NEW_GEO_TARGETS), "new countries to 3 v7.0 campaigns")
    print("=" * 60)

    if not API_KEY:
        print("\nERROR  API_SECRET_KEY not set in .env")
        return

    with httpx.Client(headers={"X-API-Key": API_KEY}) as session:

        # Step 1: find the 3 v7.0 campaign IDs
        print("\nLooking up v7.0 campaign IDs...")
        campaign_ids = get_v7_campaign_ids(session)

        if not campaign_ids:
            print("ERROR  No v7.0 campaigns found. Have you run execute_plan.py yet?")
            return

        for name, cid in campaign_ids.items():
            print(f"  Found: {name} -> {cid}")

        missing = V7_CAMPAIGN_NAMES - set(campaign_ids.keys())
        if missing:
            print(f"\nWARN  Missing campaigns (will skip): {missing}")

        # Step 2: add geo targets to each campaign
        grand_ok = grand_err = 0

        for camp_name, camp_id in campaign_ids.items():
            print(f"\n-- {camp_name} (id={camp_id}) ------------------------------")
            ok = err = 0

            for geo_id, country in NEW_GEO_TARGETS:
                result = add_geo_target(session, camp_id, geo_id, country, args.dry_run)
                if result == "ok":
                    ok += 1
                    print(f"  OK  {country:<30} ({geo_id})")
                elif result == "skip":
                    pass  # Tier 1 already applied — silent
                else:
                    err += 1
                    print(f"  ERR {country:<30} ({geo_id}) -- {result}")

                if not args.dry_run:
                    time.sleep(0.6)  # avoid Google Ads API rate-limiting

            print(f"\n     {camp_name}: {ok} added, {err} errors")
            grand_ok += ok
            grand_err += err

    print("\n" + "=" * 60)
    label = "DRY RUN — " if args.dry_run else ""
    print(f"  {label}COMPLETE: {grand_ok} targets added, {grand_err} errors")
    print("=" * 60)

    if grand_err:
        print("\nNOTE  Some targets failed. Check errors above.")
        print("      Invalid geo IDs or unsupported territories are common causes.")
        print("      Verify in Google Ads UI — Locations tab on each campaign.\n")
    else:
        print("\nOK  All geo targets applied successfully.")
        print("    Verify in Google Ads UI: Settings > Locations on each campaign.\n")


if __name__ == "__main__":
    main()
