"""Keyword management — all match types, negatives, shared lists, Quality Score."""

from __future__ import annotations

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

from src.auth.client import normalize_customer_id, resource_name_to_id
from src.models.keywords import (
    CreateKeywordRequest,
    CreateNegativeKeywordRequest,
    UpdateKeywordBidRequest,
    KeywordResponse,
    SharedNegativeListRequest,
    BulkCreateKeywordsRequest,
)
from src.utils.error_handling import handle_google_ads_exception

AD_GRANTS_MAX_CPC_MICROS = 2_000_000


class KeywordService:
    def __init__(self, client: GoogleAdsClient) -> None:
        self.client = client
        self.svc = client.get_service("AdGroupCriterionService")

    # ── Add keyword ───────────────────────────────────────────────────────────

    def add(
        self, customer_id: str, req: CreateKeywordRequest
    ) -> KeywordResponse:
        customer_id = normalize_customer_id(customer_id)
        ops = [self._build_keyword_op(customer_id, req)]

        try:
            resp = self.svc.mutate_ad_group_criteria(
                customer_id=customer_id, operations=ops
            )
        except GoogleAdsException as exc:
            handle_google_ads_exception(exc)

        rn = resp.results[0].resource_name
        return KeywordResponse(
            resource_name=rn,
            criterion_id=resource_name_to_id(rn),
            ad_group_id=req.ad_group_id,
            keyword_text=req.keyword_text,
            match_type=req.match_type.value,
            status=req.status.value,
            cpc_bid_micros=req.cpc_bid_micros,
        )

    def add_bulk(
        self, customer_id: str, req: BulkCreateKeywordsRequest
    ) -> dict:
        """Add many keywords — uses BatchJobService for large sets."""
        customer_id = normalize_customer_id(customer_id)
        if req.use_batch_job or len(req.keywords) > 500:
            from src.services.batch_service import BatchService
            bs = BatchService(self.client)
            ops = [
                self._build_keyword_op(customer_id, kw, as_batch_op=True)
                for kw in req.keywords
            ]
            return bs.submit_operations(customer_id, ops)

        # Regular mutate in chunks of 10,000
        ops = [self._build_keyword_op(customer_id, kw) for kw in req.keywords]
        results = []
        chunk_size = 5_000
        for i in range(0, len(ops), chunk_size):
            chunk = ops[i : i + chunk_size]
            try:
                resp = self.svc.mutate_ad_group_criteria(
                    customer_id=customer_id,
                    operations=chunk,
                    partial_failure=True,
                )
                results.extend(
                    [r.resource_name for r in resp.results if r.resource_name]
                )
            except GoogleAdsException as exc:
                handle_google_ads_exception(exc)

        return {"created_count": len(results), "resource_names": results}

    # ── Negative keywords ─────────────────────────────────────────────────────

    def add_negative(
        self, customer_id: str, req: CreateNegativeKeywordRequest
    ) -> dict:
        customer_id = normalize_customer_id(customer_id)

        if req.ad_group_id:
            # Ad group–level negative
            op = self.client.get_type("AdGroupCriterionOperation")
            criterion = op.create
            ag_svc = self.client.get_service("AdGroupService")
            criterion.ad_group = ag_svc.ad_group_path(customer_id, req.ad_group_id)
            criterion.negative = True
            criterion.keyword.text = req.keyword_text
            criterion.keyword.match_type = (
                self.client.enums.KeywordMatchTypeEnum[req.match_type.value]
            )
            try:
                resp = self.svc.mutate_ad_group_criteria(
                    customer_id=customer_id, operations=[op]
                )
            except GoogleAdsException as exc:
                handle_google_ads_exception(exc)
            return {"resource_name": resp.results[0].resource_name}

        elif req.campaign_id:
            # Campaign-level negative
            cm_svc = self.client.get_service("CampaignCriterionService")
            op = self.client.get_type("CampaignCriterionOperation")
            criterion = op.create
            campaign_svc = self.client.get_service("CampaignService")
            criterion.campaign = campaign_svc.campaign_path(
                customer_id, req.campaign_id
            )
            criterion.negative = True
            criterion.keyword.text = req.keyword_text
            criterion.keyword.match_type = (
                self.client.enums.KeywordMatchTypeEnum[req.match_type.value]
            )
            try:
                resp = cm_svc.mutate_campaign_criteria(
                    customer_id=customer_id, operations=[op]
                )
            except GoogleAdsException as exc:
                handle_google_ads_exception(exc)
            return {"resource_name": resp.results[0].resource_name}

        else:
            raise ValueError("Provide either campaign_id or ad_group_id.")

    # ── Shared negative lists ─────────────────────────────────────────────────

    def create_shared_negative_list(
        self, customer_id: str, req: SharedNegativeListRequest
    ) -> dict:
        customer_id = normalize_customer_id(customer_id)
        shared_set_svc = self.client.get_service("SharedSetService")
        shared_criterion_svc = self.client.get_service("SharedCriterionService")
        campaign_shared_set_svc = self.client.get_service("CampaignSharedSetService")

        # 1. Create the shared set
        ss_op = self.client.get_type("SharedSetOperation")
        ss_op.create.name = req.list_name
        ss_op.create.type_ = self.client.enums.SharedSetTypeEnum.NEGATIVE_KEYWORDS
        ss_resp = shared_set_svc.mutate_shared_sets(
            customer_id=customer_id, operations=[ss_op]
        )
        shared_set_rn = ss_resp.results[0].resource_name

        # 2. Add keywords to the shared set
        kw_ops = []
        for kw in req.keywords:
            op = self.client.get_type("SharedCriterionOperation")
            op.create.shared_set = shared_set_rn
            op.create.keyword.text = kw.keyword_text
            op.create.keyword.match_type = (
                self.client.enums.KeywordMatchTypeEnum[kw.match_type.value]
            )
            kw_ops.append(op)
        shared_criterion_svc.mutate_shared_criteria(
            customer_id=customer_id, operations=kw_ops
        )

        # 3. Attach to campaigns
        campaign_svc = self.client.get_service("CampaignService")
        css_ops = []
        for cid in req.campaign_ids:
            op = self.client.get_type("CampaignSharedSetOperation")
            op.create.campaign = campaign_svc.campaign_path(customer_id, cid)
            op.create.shared_set = shared_set_rn
            css_ops.append(op)
        if css_ops:
            campaign_shared_set_svc.mutate_campaign_shared_sets(
                customer_id=customer_id, operations=css_ops
            )

        return {
            "shared_set_resource_name": shared_set_rn,
            "keyword_count": len(req.keywords),
            "attached_campaigns": req.campaign_ids,
        }

    # ── Update keyword bid / status ───────────────────────────────────────────

    def update(
        self, customer_id: str, req: UpdateKeywordBidRequest
    ) -> dict:
        customer_id = normalize_customer_id(customer_id)
        ag_svc = self.client.get_service("AdGroupService")
        rn = self.svc.ad_group_criterion_path(
            customer_id, req.ad_group_id, req.criterion_id
        )

        op = self.client.get_type("AdGroupCriterionOperation")
        criterion = op.update
        criterion.resource_name = rn
        fields: list[str] = []

        if req.cpc_bid_micros is not None:
            criterion.cpc_bid_micros = req.cpc_bid_micros
            fields.append("cpc_bid_micros")
        if req.status is not None:
            from src.models.keywords import KeywordStatus
            criterion.status = self.client.enums.AdGroupCriterionStatusEnum[
                req.status.value
            ]
            fields.append("status")

        from google.protobuf import field_mask_pb2
        op.update_mask.CopyFrom(field_mask_pb2.FieldMask(paths=fields))

        try:
            resp = self.svc.mutate_ad_group_criteria(
                customer_id=customer_id, operations=[op]
            )
        except GoogleAdsException as exc:
            handle_google_ads_exception(exc)

        return {"resource_name": resp.results[0].resource_name}

    # ── Remove keyword ────────────────────────────────────────────────────────

    def remove(self, customer_id: str, ad_group_id: str, criterion_id: str) -> dict:
        customer_id = normalize_customer_id(customer_id)
        rn = self.svc.ad_group_criterion_path(customer_id, ad_group_id, criterion_id)
        op = self.client.get_type("AdGroupCriterionOperation")
        op.remove = rn

        try:
            resp = self.svc.mutate_ad_group_criteria(
                customer_id=customer_id, operations=[op]
            )
        except GoogleAdsException as exc:
            handle_google_ads_exception(exc)

        return {"removed": resp.results[0].resource_name}

    # ── Quality Score retrieval ───────────────────────────────────────────────

    def get_quality_scores(
        self, customer_id: str, ad_group_id: str
    ) -> list[dict]:
        customer_id = normalize_customer_id(customer_id)
        ga_service = self.client.get_service("GoogleAdsService")
        query = f"""
            SELECT
                ad_group_criterion.criterion_id,
                ad_group_criterion.keyword.text,
                ad_group_criterion.keyword.match_type,
                ad_group_criterion.quality_info.quality_score,
                ad_group_criterion.quality_info.creative_quality_score,
                ad_group_criterion.quality_info.post_click_quality_score,
                ad_group_criterion.quality_info.search_predicted_ctr
            FROM ad_group_criterion
            WHERE
                ad_group_criterion.type = 'KEYWORD'
                AND ad_group.id = {ad_group_id}
                AND ad_group_criterion.status != 'REMOVED'
        """
        results = []
        for row in ga_service.search(customer_id=customer_id, query=query):
            crit = row.ad_group_criterion
            results.append(
                {
                    "criterion_id": str(crit.criterion_id),
                    "keyword_text": crit.keyword.text,
                    "match_type": crit.keyword.match_type.name,
                    "quality_score": crit.quality_info.quality_score,
                    "creative_quality": crit.quality_info.creative_quality_score.name,
                    "post_click_quality": crit.quality_info.post_click_quality_score.name,
                    "predicted_ctr": crit.quality_info.search_predicted_ctr.name,
                }
            )
        return results

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _build_keyword_op(
        self,
        customer_id: str,
        req: CreateKeywordRequest,
        as_batch_op: bool = False,
    ):
        op = self.client.get_type("AdGroupCriterionOperation")
        criterion = op.create
        ag_svc = self.client.get_service("AdGroupService")
        criterion.ad_group = ag_svc.ad_group_path(customer_id, req.ad_group_id)
        criterion.status = self.client.enums.AdGroupCriterionStatusEnum[
            req.status.value
        ]
        criterion.keyword.text = req.keyword_text
        criterion.keyword.match_type = self.client.enums.KeywordMatchTypeEnum[
            req.match_type.value
        ]
        if req.cpc_bid_micros is not None:
            criterion.cpc_bid_micros = req.cpc_bid_micros
        for url in req.final_urls:
            criterion.final_urls.append(url)
        return op
