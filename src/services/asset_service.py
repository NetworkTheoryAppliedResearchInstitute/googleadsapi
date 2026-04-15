"""Asset management — create assets and link them at account/campaign/ad-group level.

Assets are immutable once created; only their associations can be paused/removed.
"""

from __future__ import annotations

import base64

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

from src.auth.client import normalize_customer_id, resource_name_to_id
from src.models.assets import (
    AssetType,
    AssetLinkLevel,
    AssetFieldType,
    CreateAssetRequest,
    LinkAssetRequest,
    SitelinkAsset,
    CalloutAsset,
    StructuredSnippetAsset,
    CallAsset,
    PriceAsset,
    PromotionAsset,
    ImageAsset,
    LeadFormAsset,
)
from src.utils.error_handling import handle_google_ads_exception


class AssetService:
    def __init__(self, client: GoogleAdsClient) -> None:
        self.client = client
        self.svc = client.get_service("AssetService")

    # ── Create ────────────────────────────────────────────────────────────────

    def create(self, customer_id: str, req: CreateAssetRequest) -> dict:
        customer_id = normalize_customer_id(customer_id)
        op = self.client.get_type("AssetOperation")
        asset = op.create

        builder = {
            AssetType.SITELINK: self._build_sitelink,
            AssetType.CALLOUT: self._build_callout,
            AssetType.STRUCTURED_SNIPPET: self._build_structured_snippet,
            AssetType.CALL: self._build_call,
            AssetType.PRICE: self._build_price,
            AssetType.PROMOTION: self._build_promotion,
            AssetType.IMAGE: self._build_image,
            AssetType.LEAD_FORM: self._build_lead_form,
        }.get(req.asset_type)

        if builder is None:
            raise ValueError(f"Unsupported asset type: {req.asset_type}")

        builder(asset, req)

        try:
            resp = self.svc.mutate_assets(
                customer_id=customer_id, operations=[op]
            )
        except GoogleAdsException as exc:
            handle_google_ads_exception(exc)

        rn = resp.results[0].resource_name
        return {
            "resource_name": rn,
            "asset_id": resource_name_to_id(rn),
            "asset_type": req.asset_type.value,
        }

    # ── Link ──────────────────────────────────────────────────────────────────

    def link(self, customer_id: str, req: LinkAssetRequest) -> dict:
        """Link an existing asset to an account, campaign, or ad group."""
        customer_id = normalize_customer_id(customer_id)
        field_type_enum = self.client.enums.AssetFieldTypeEnum[req.field_type.value]

        if req.link_level == AssetLinkLevel.CUSTOMER:
            svc = self.client.get_service("CustomerAssetService")
            op = self.client.get_type("CustomerAssetOperation")
            op.create.asset = req.asset_resource_name
            op.create.field_type = field_type_enum
            try:
                resp = svc.mutate_customer_assets(
                    customer_id=customer_id, operations=[op]
                )
            except GoogleAdsException as exc:
                handle_google_ads_exception(exc)
            return {"resource_name": resp.results[0].resource_name}

        elif req.link_level == AssetLinkLevel.CAMPAIGN:
            if not req.campaign_id:
                raise ValueError("campaign_id required for CAMPAIGN link level.")
            svc = self.client.get_service("CampaignAssetService")
            op = self.client.get_type("CampaignAssetOperation")
            op.create.asset = req.asset_resource_name
            op.create.field_type = field_type_enum
            campaign_svc = self.client.get_service("CampaignService")
            op.create.campaign = campaign_svc.campaign_path(
                customer_id, req.campaign_id
            )
            try:
                resp = svc.mutate_campaign_assets(
                    customer_id=customer_id, operations=[op]
                )
            except GoogleAdsException as exc:
                handle_google_ads_exception(exc)
            return {"resource_name": resp.results[0].resource_name}

        elif req.link_level == AssetLinkLevel.AD_GROUP:
            if not req.ad_group_id:
                raise ValueError("ad_group_id required for AD_GROUP link level.")
            svc = self.client.get_service("AdGroupAssetService")
            op = self.client.get_type("AdGroupAssetOperation")
            op.create.asset = req.asset_resource_name
            op.create.field_type = field_type_enum
            ag_svc = self.client.get_service("AdGroupService")
            op.create.ad_group = ag_svc.ad_group_path(customer_id, req.ad_group_id)
            try:
                resp = svc.mutate_ad_group_assets(
                    customer_id=customer_id, operations=[op]
                )
            except GoogleAdsException as exc:
                handle_google_ads_exception(exc)
            return {"resource_name": resp.results[0].resource_name}

        raise ValueError(f"Unknown link level: {req.link_level}")

    def pause_link(
        self, customer_id: str, asset_link_resource_name: str, link_level: AssetLinkLevel
    ) -> dict:
        """Pause an asset association (assets cannot be deleted, only associations)."""
        customer_id = normalize_customer_id(customer_id)
        from google.protobuf import field_mask_pb2

        if link_level == AssetLinkLevel.CAMPAIGN:
            svc = self.client.get_service("CampaignAssetService")
            op = self.client.get_type("CampaignAssetOperation")
            op.update.resource_name = asset_link_resource_name
            op.update.status = self.client.enums.AssetLinkStatusEnum.PAUSED
            op.update_mask.CopyFrom(field_mask_pb2.FieldMask(paths=["status"]))
            resp = svc.mutate_campaign_assets(customer_id=customer_id, operations=[op])
        elif link_level == AssetLinkLevel.AD_GROUP:
            svc = self.client.get_service("AdGroupAssetService")
            op = self.client.get_type("AdGroupAssetOperation")
            op.update.resource_name = asset_link_resource_name
            op.update.status = self.client.enums.AssetLinkStatusEnum.PAUSED
            op.update_mask.CopyFrom(field_mask_pb2.FieldMask(paths=["status"]))
            resp = svc.mutate_ad_group_assets(customer_id=customer_id, operations=[op])
        else:
            svc = self.client.get_service("CustomerAssetService")
            op = self.client.get_type("CustomerAssetOperation")
            op.update.resource_name = asset_link_resource_name
            op.update.status = self.client.enums.AssetLinkStatusEnum.PAUSED
            op.update_mask.CopyFrom(field_mask_pb2.FieldMask(paths=["status"]))
            resp = svc.mutate_customer_assets(customer_id=customer_id, operations=[op])

        return {"paused": resp.results[0].resource_name}

    # ── Asset builders ────────────────────────────────────────────────────────

    def _build_sitelink(self, asset, req: CreateAssetRequest) -> None:
        data: SitelinkAsset = req.sitelink
        sl = asset.sitelink_asset
        sl.link_text = data.link_text
        if data.description1:
            sl.description1 = data.description1
        if data.description2:
            sl.description2 = data.description2
        for url in data.final_urls:
            sl.final_urls.append(url)
        for url in data.final_mobile_urls:
            sl.final_mobile_urls.append(url)

    def _build_callout(self, asset, req: CreateAssetRequest) -> None:
        asset.callout_asset.callout_text = req.callout.callout_text

    def _build_structured_snippet(self, asset, req: CreateAssetRequest) -> None:
        data: StructuredSnippetAsset = req.structured_snippet
        ss = asset.structured_snippet_asset
        ss.header = data.header
        for v in data.values:
            ss.values.append(v)

    def _build_call(self, asset, req: CreateAssetRequest) -> None:
        data: CallAsset = req.call
        c = asset.call_asset
        c.phone_number = data.phone_number
        c.country_code = data.country_code
        if data.call_conversion_reporting_state:
            c.call_conversion_reporting_state = (
                self.client.enums.CallConversionReportingStateEnum[
                    data.call_conversion_reporting_state
                ]
            )

    def _build_price(self, asset, req: CreateAssetRequest) -> None:
        data: PriceAsset = req.price
        p = asset.price_asset
        p.type_ = self.client.enums.PriceExtensionTypeEnum[data.type]
        if data.price_qualifier:
            p.price_qualifier = self.client.enums.PriceExtensionPriceQualifierEnum[
                data.price_qualifier
            ]
        p.language_code = data.language_code
        for item in data.items:
            pi = self.client.get_type("PriceOffering")
            pi.header = item.header
            pi.description = item.description
            pi.price.amount_micros = item.price_micros
            pi.price.currency_code = item.currency_code
            if item.unit:
                pi.unit = self.client.enums.PriceExtensionPriceUnitEnum[item.unit]
            for url in item.final_urls:
                pi.final_urls.append(url)
            p.price_offerings.append(pi)

    def _build_promotion(self, asset, req: CreateAssetRequest) -> None:
        data: PromotionAsset = req.promotion
        pr = asset.promotion_asset
        pr.promotion_target = data.promotion_target
        pr.money_amount_off.amount_micros = data.money_off_amount_micros or 0
        pr.money_amount_off.currency_code = data.currency_code
        if data.percent_off:
            pr.percent_off = data.percent_off * 1_000_000  # micros
        if data.occasion:
            pr.occasion = self.client.enums.PromotionExtensionOccasionEnum[
                data.occasion
            ]
        for url in data.final_urls:
            pr.final_urls.append(url)
        if data.start_date:
            pr.start_date = data.start_date
        if data.end_date:
            pr.end_date = data.end_date

    def _build_image(self, asset, req: CreateAssetRequest) -> None:
        data: ImageAsset = req.image
        img = asset.image_asset
        if data.image_data_base64:
            img.data = base64.b64decode(data.image_data_base64)
        elif data.image_url:
            img.full_size.url = data.image_url
        img.mime_type = self.client.enums.MimeTypeEnum[data.mime_type]

    def _build_lead_form(self, asset, req: CreateAssetRequest) -> None:
        data: LeadFormAsset = req.lead_form
        lf = asset.lead_form_asset
        lf.business_name = data.business_name
        lf.headline = data.headline
        lf.description = data.description
        lf.privacy_policy_url = data.privacy_policy_url
        if data.post_submit_headline:
            lf.post_submit_headline = data.post_submit_headline
        if data.post_submit_description:
            lf.post_submit_description = data.post_submit_description
