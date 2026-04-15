"""Portfolio (shared) bidding strategy management."""

from __future__ import annotations

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

from src.auth.client import normalize_customer_id, resource_name_to_id
from src.models.bidding import (
    BiddingStrategyType,
    CreatePortfolioBiddingStrategyRequest,
    BiddingStrategyResponse,
)
from src.utils.error_handling import handle_google_ads_exception


class BiddingService:
    def __init__(self, client: GoogleAdsClient) -> None:
        self.client = client
        self.svc = client.get_service("BiddingStrategyService")

    def create(
        self, customer_id: str, req: CreatePortfolioBiddingStrategyRequest
    ) -> BiddingStrategyResponse:
        customer_id = normalize_customer_id(customer_id)
        op = self.client.get_type("BiddingStrategyOperation")
        strategy = op.create
        strategy.name = req.name

        bst = req.strategy_type

        if bst == BiddingStrategyType.TARGET_CPA:
            if not req.target_cpa_micros:
                raise ValueError("target_cpa_micros required for TARGET_CPA.")
            strategy.target_cpa.target_cpa_micros = req.target_cpa_micros

        elif bst == BiddingStrategyType.TARGET_ROAS:
            if not req.target_roas:
                raise ValueError("target_roas required for TARGET_ROAS.")
            tr = strategy.target_roas
            tr.target_roas = req.target_roas
            # Smart Bidding Exploration (v21+): optional ROAS tolerance range
            if req.target_roas_min is not None:
                tr.cpc_bid_floor_micros = int(req.target_roas_min * 1_000_000)
            if req.target_roas_max is not None:
                tr.cpc_bid_ceiling_micros = int(req.target_roas_max * 1_000_000)

        elif bst == BiddingStrategyType.MAXIMIZE_CLICKS:
            mc = strategy.maximize_clicks
            if req.cpc_bid_ceiling_micros:
                mc.cpc_bid_ceiling_micros = req.cpc_bid_ceiling_micros

        elif bst == BiddingStrategyType.MAXIMIZE_CONVERSIONS:
            mv = strategy.maximize_conversions
            if req.target_cpa_micros:
                mv.target_cpa_micros = req.target_cpa_micros

        elif bst == BiddingStrategyType.TARGET_IMPRESSION_SHARE:
            tis = strategy.target_impression_share
            if req.target_impression_share_location:
                tis.location = self.client.enums.TargetImpressionShareLocationEnum[
                    req.target_impression_share_location.value
                ]
            if req.target_impression_share_fraction is not None:
                tis.location_fraction_micros = int(
                    req.target_impression_share_fraction * 1_000_000
                )
            if req.cpc_bid_ceiling_micros:
                tis.cpc_bid_ceiling_micros = req.cpc_bid_ceiling_micros

        elif bst == BiddingStrategyType.TARGET_SPEND:
            ts = strategy.target_spend
            if req.cpc_bid_ceiling_micros:
                ts.cpc_bid_ceiling_micros = req.cpc_bid_ceiling_micros
            if req.target_spend_micros:
                ts.target_spend_micros = req.target_spend_micros

        else:
            raise ValueError(f"Unsupported portfolio bidding strategy: {bst}")

        try:
            resp = self.svc.mutate_bidding_strategies(
                customer_id=customer_id, operations=[op]
            )
        except GoogleAdsException as exc:
            handle_google_ads_exception(exc)

        rn = resp.results[0].resource_name
        return BiddingStrategyResponse(
            resource_name=rn,
            strategy_id=resource_name_to_id(rn),
            name=req.name,
            strategy_type=bst.value,
        )

    def list(self, customer_id: str) -> list[dict]:
        customer_id = normalize_customer_id(customer_id)
        ga_service = self.client.get_service("GoogleAdsService")
        query = """
            SELECT
                bidding_strategy.id,
                bidding_strategy.name,
                bidding_strategy.type,
                bidding_strategy.status,
                bidding_strategy.campaign_count
            FROM bidding_strategy
            WHERE bidding_strategy.status != 'REMOVED'
        """
        results = []
        for row in ga_service.search(customer_id=customer_id, query=query):
            bs = row.bidding_strategy
            results.append(
                {
                    "strategy_id": str(bs.id),
                    "name": bs.name,
                    "type": bs.type_.name,
                    "status": bs.status.name,
                    "campaign_count": bs.campaign_count,
                }
            )
        return results

    def remove(self, customer_id: str, strategy_id: str) -> dict:
        customer_id = normalize_customer_id(customer_id)
        rn = self.svc.bidding_strategy_path(customer_id, strategy_id)
        op = self.client.get_type("BiddingStrategyOperation")
        op.remove = rn
        try:
            resp = self.svc.mutate_bidding_strategies(
                customer_id=customer_id, operations=[op]
            )
        except GoogleAdsException as exc:
            handle_google_ads_exception(exc)
        return {"removed": resp.results[0].resource_name}
