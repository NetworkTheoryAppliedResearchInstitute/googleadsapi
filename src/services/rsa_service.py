"""Responsive Search Ad (RSA) management — create, update, retrieve with performance data."""

from __future__ import annotations

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
from google.protobuf import field_mask_pb2

from src.auth.client import normalize_customer_id, resource_name_to_id
from src.models.ads import CreateRSARequest, UpdateRSARequest, RSAResponse
from src.utils.error_handling import handle_google_ads_exception


class RSAService:
    def __init__(self, client: GoogleAdsClient) -> None:
        self.client = client
        self.svc = client.get_service("AdGroupAdService")

    def create(self, customer_id: str, req: CreateRSARequest) -> RSAResponse:
        customer_id = normalize_customer_id(customer_id)

        op = self.client.get_type("AdGroupAdOperation")
        ad_group_ad = op.create

        ag_svc = self.client.get_service("AdGroupService")
        ad_group_ad.ad_group = ag_svc.ad_group_path(customer_id, req.ad_group_id)
        ad_group_ad.status = self.client.enums.AdGroupAdStatusEnum[req.status.value]

        ad = ad_group_ad.ad

        # Final URLs
        for url in req.final_urls:
            ad.final_urls.append(url)
        for url in req.final_mobile_urls:
            ad.final_mobile_urls.append(url)

        # Display URL paths
        if req.path1:
            ad.responsive_search_ad.path1 = req.path1
        if req.path2:
            ad.responsive_search_ad.path2 = req.path2

        # Headlines
        for h in req.headlines:
            asset = self.client.get_type("AdTextAsset")
            asset.text = h.text
            if h.pinned_field:
                asset.pinned_field = self.client.enums.ServedAssetFieldTypeEnum[
                    h.pinned_field.value
                ]
            ad.responsive_search_ad.headlines.append(asset)

        # Descriptions
        for d in req.descriptions:
            asset = self.client.get_type("AdTextAsset")
            asset.text = d.text
            if d.pinned_field:
                asset.pinned_field = self.client.enums.ServedAssetFieldTypeEnum[
                    d.pinned_field.value
                ]
            ad.responsive_search_ad.descriptions.append(asset)

        try:
            resp = self.svc.mutate_ad_group_ads(
                customer_id=customer_id, operations=[op]
            )
        except GoogleAdsException as exc:
            handle_google_ads_exception(exc)

        rn = resp.results[0].resource_name
        return RSAResponse(
            resource_name=rn,
            ad_id=resource_name_to_id(rn),
            ad_group_id=req.ad_group_id,
            status=req.status.value,
            headlines=[{"text": h.text, "pinned_field": h.pinned_field} for h in req.headlines],
            descriptions=[{"text": d.text, "pinned_field": d.pinned_field} for d in req.descriptions],
            final_urls=req.final_urls,
            path1=req.path1,
            path2=req.path2,
        )

    def get(self, customer_id: str, ad_group_id: str, ad_id: str) -> dict:
        customer_id = normalize_customer_id(customer_id)
        ga_service = self.client.get_service("GoogleAdsService")
        query = f"""
            SELECT
                ad_group_ad.ad.id,
                ad_group_ad.ad.responsive_search_ad.headlines,
                ad_group_ad.ad.responsive_search_ad.descriptions,
                ad_group_ad.ad.responsive_search_ad.path1,
                ad_group_ad.ad.responsive_search_ad.path2,
                ad_group_ad.ad.final_urls,
                ad_group_ad.status,
                ad_group_ad.policy_summary.approval_status
            FROM ad_group_ad
            WHERE
                ad_group_ad.ad.id = {ad_id}
                AND ad_group.id = {ad_group_id}
        """
        rows = list(ga_service.search(customer_id=customer_id, query=query))
        if not rows:
            return {}
        r = rows[0].ad_group_ad
        rsa = r.ad.responsive_search_ad
        return {
            "ad_id": str(r.ad.id),
            "status": r.status.name,
            "approval_status": r.policy_summary.approval_status.name,
            "headlines": [
                {"text": h.text, "pinned_field": h.pinned_field.name}
                for h in rsa.headlines
            ],
            "descriptions": [
                {"text": d.text, "pinned_field": d.pinned_field.name}
                for d in rsa.descriptions
            ],
            "path1": rsa.path1,
            "path2": rsa.path2,
            "final_urls": list(r.ad.final_urls),
        }

    def list(self, customer_id: str, ad_group_id: str) -> list[dict]:
        customer_id = normalize_customer_id(customer_id)
        ga_service = self.client.get_service("GoogleAdsService")
        query = f"""
            SELECT
                ad_group_ad.ad.id,
                ad_group_ad.ad.responsive_search_ad.headlines,
                ad_group_ad.ad.responsive_search_ad.descriptions,
                ad_group_ad.ad.responsive_search_ad.path1,
                ad_group_ad.ad.responsive_search_ad.path2,
                ad_group_ad.ad.final_urls,
                ad_group_ad.status
            FROM ad_group_ad
            WHERE
                ad_group.id = {ad_group_id}
                AND ad_group_ad.ad.type = 'RESPONSIVE_SEARCH_AD'
                AND ad_group_ad.status != 'REMOVED'
        """
        results = []
        for row in ga_service.search(customer_id=customer_id, query=query):
            r = row.ad_group_ad
            rsa = r.ad.responsive_search_ad
            results.append(
                {
                    "ad_id": str(r.ad.id),
                    "status": r.status.name,
                    "headlines": [h.text for h in rsa.headlines],
                    "descriptions": [d.text for d in rsa.descriptions],
                    "path1": rsa.path1,
                    "path2": rsa.path2,
                    "final_urls": list(r.ad.final_urls),
                }
            )
        return results

    def get_performance(
        self, customer_id: str, ad_group_id: str, date_range: str = "LAST_30_DAYS"
    ) -> list[dict]:
        """Retrieve per-asset performance via ad_group_ad_asset_view."""
        customer_id = normalize_customer_id(customer_id)
        ga_service = self.client.get_service("GoogleAdsService")
        query = f"""
            SELECT
                ad_group_ad_asset_view.ad_group_ad,
                ad_group_ad_asset_view.asset,
                ad_group_ad_asset_view.field_type,
                ad_group_ad_asset_view.performance_label,
                ad_group_ad_asset_view.pinned_field,
                metrics.impressions,
                metrics.clicks,
                metrics.ctr,
                metrics.conversions
            FROM ad_group_ad_asset_view
            WHERE
                ad_group.id = {ad_group_id}
                AND segments.date DURING {date_range}
        """
        results = []
        for row in ga_service.search(customer_id=customer_id, query=query):
            v = row.ad_group_ad_asset_view
            m = row.metrics
            results.append(
                {
                    "ad_group_ad": v.ad_group_ad,
                    "asset": v.asset,
                    "field_type": v.field_type.name,
                    "performance_label": v.performance_label.name,
                    "pinned": v.pinned_field.name,
                    "impressions": m.impressions,
                    "clicks": m.clicks,
                    "ctr": m.ctr,
                    "conversions": m.conversions,
                }
            )
        return results

    def update(
        self,
        customer_id: str,
        ad_group_id: str,
        ad_id: str,
        req: UpdateRSARequest,
    ) -> dict:
        customer_id = normalize_customer_id(customer_id)
        svc = self.client.get_service("AdGroupAdService")
        ag_svc = self.client.get_service("AdGroupService")

        # Build resource name as customers/{cid}/adGroupAds/{ag_id}~{ad_id}
        rn = f"customers/{customer_id}/adGroupAds/{ad_group_id}~{ad_id}"

        op = self.client.get_type("AdGroupAdOperation")
        ad_group_ad = op.update
        ad_group_ad.resource_name = rn
        fields: list[str] = []

        if req.status is not None:
            ad_group_ad.status = self.client.enums.AdGroupAdStatusEnum[req.status.value]
            fields.append("status")

        if req.final_urls is not None:
            for url in req.final_urls:
                ad_group_ad.ad.final_urls.append(url)
            fields.append("ad.final_urls")

        if req.path1 is not None:
            ad_group_ad.ad.responsive_search_ad.path1 = req.path1
            fields.append("ad.responsive_search_ad.path1")

        if req.path2 is not None:
            ad_group_ad.ad.responsive_search_ad.path2 = req.path2
            fields.append("ad.responsive_search_ad.path2")

        if req.headlines is not None:
            for h in req.headlines:
                asset = self.client.get_type("AdTextAsset")
                asset.text = h.text
                if h.pinned_field:
                    asset.pinned_field = self.client.enums.ServedAssetFieldTypeEnum[
                        h.pinned_field.value
                    ]
                ad_group_ad.ad.responsive_search_ad.headlines.append(asset)
            fields.append("ad.responsive_search_ad.headlines")

        if req.descriptions is not None:
            for d in req.descriptions:
                asset = self.client.get_type("AdTextAsset")
                asset.text = d.text
                if d.pinned_field:
                    asset.pinned_field = self.client.enums.ServedAssetFieldTypeEnum[
                        d.pinned_field.value
                    ]
                ad_group_ad.ad.responsive_search_ad.descriptions.append(asset)
            fields.append("ad.responsive_search_ad.descriptions")

        op.update_mask.CopyFrom(field_mask_pb2.FieldMask(paths=fields))

        try:
            resp = svc.mutate_ad_group_ads(customer_id=customer_id, operations=[op])
        except GoogleAdsException as exc:
            handle_google_ads_exception(exc)

        return {"resource_name": resp.results[0].resource_name}

    def remove(self, customer_id: str, ad_group_id: str, ad_id: str) -> dict:
        customer_id = normalize_customer_id(customer_id)
        rn = f"customers/{customer_id}/adGroupAds/{ad_group_id}~{ad_id}"
        op = self.client.get_type("AdGroupAdOperation")
        op.remove = rn
        try:
            resp = self.svc.mutate_ad_group_ads(
                customer_id=customer_id, operations=[op]
            )
        except GoogleAdsException as exc:
            handle_google_ads_exception(exc)
        return {"removed": resp.results[0].resource_name}
