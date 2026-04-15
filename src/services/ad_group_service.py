"""Ad group CRUD — creation, updates, status, CPC bids, ad group-level targeting."""

from __future__ import annotations

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
from google.protobuf import field_mask_pb2

from src.auth.client import normalize_customer_id, resource_name_to_id
from src.models.ad_groups import (
    CreateAdGroupRequest,
    UpdateAdGroupRequest,
    AdGroupResponse,
)
from src.utils.error_handling import handle_google_ads_exception

AD_GRANTS_MAX_CPC_MICROS = 2_000_000  # $2.00


class AdGroupService:
    def __init__(self, client: GoogleAdsClient) -> None:
        self.client = client
        self.svc = client.get_service("AdGroupService")

    def create(
        self, customer_id: str, req: CreateAdGroupRequest
    ) -> AdGroupResponse:
        customer_id = normalize_customer_id(customer_id)

        op = self.client.get_type("AdGroupOperation")
        ag = op.create

        campaign_svc = self.client.get_service("CampaignService")
        ag.campaign = campaign_svc.campaign_path(customer_id, req.campaign_id)
        ag.name = req.name
        ag.status = self.client.enums.AdGroupStatusEnum[req.status.value]
        ag.type_ = self.client.enums.AdGroupTypeEnum[req.ad_group_type.value]

        if req.cpc_bid_micros is not None:
            ag.cpc_bid_micros = req.cpc_bid_micros

        try:
            resp = self.svc.mutate_ad_groups(
                customer_id=customer_id, operations=[op]
            )
        except GoogleAdsException as exc:
            handle_google_ads_exception(exc)

        rn = resp.results[0].resource_name
        return AdGroupResponse(
            resource_name=rn,
            ad_group_id=resource_name_to_id(rn),
            name=req.name,
            status=req.status.value,
            ad_group_type=req.ad_group_type.value,
            campaign_id=req.campaign_id,
            cpc_bid_micros=req.cpc_bid_micros,
        )

    def get(self, customer_id: str, ad_group_id: str) -> dict:
        customer_id = normalize_customer_id(customer_id)
        ga_service = self.client.get_service("GoogleAdsService")
        query = f"""
            SELECT
                ad_group.id,
                ad_group.name,
                ad_group.status,
                ad_group.type,
                ad_group.campaign,
                ad_group.cpc_bid_micros
            FROM ad_group
            WHERE ad_group.id = {ad_group_id}
        """
        rows = list(ga_service.search(customer_id=customer_id, query=query))
        if not rows:
            return {}
        ag = rows[0].ad_group
        return {
            "ad_group_id": str(ag.id),
            "name": ag.name,
            "status": ag.status.name,
            "type": ag.type_.name,
            "campaign": ag.campaign,
            "cpc_bid_micros": ag.cpc_bid_micros,
        }

    def list(self, customer_id: str, campaign_id: str | None = None) -> list[dict]:
        customer_id = normalize_customer_id(customer_id)
        ga_service = self.client.get_service("GoogleAdsService")
        where_clause = "WHERE ad_group.status != 'REMOVED'"
        if campaign_id:
            where_clause += f" AND campaign.id = {campaign_id}"
        query = f"""
            SELECT
                ad_group.id,
                ad_group.name,
                ad_group.status,
                ad_group.type,
                ad_group.campaign,
                ad_group.cpc_bid_micros
            FROM ad_group
            {where_clause}
            ORDER BY ad_group.name
        """
        results = []
        for row in ga_service.search(customer_id=customer_id, query=query):
            ag = row.ad_group
            results.append(
                {
                    "ad_group_id": str(ag.id),
                    "name": ag.name,
                    "status": ag.status.name,
                    "type": ag.type_.name,
                    "campaign": ag.campaign,
                    "cpc_bid_micros": ag.cpc_bid_micros,
                }
            )
        return results

    def update(
        self, customer_id: str, ad_group_id: str, req: UpdateAdGroupRequest
    ) -> dict:
        customer_id = normalize_customer_id(customer_id)
        rn = self.svc.ad_group_path(customer_id, ad_group_id)

        op = self.client.get_type("AdGroupOperation")
        ag = op.update
        ag.resource_name = rn
        fields: list[str] = []

        if req.name is not None:
            ag.name = req.name
            fields.append("name")
        if req.status is not None:
            ag.status = self.client.enums.AdGroupStatusEnum[req.status.value]
            fields.append("status")
        if req.cpc_bid_micros is not None:
            ag.cpc_bid_micros = req.cpc_bid_micros
            fields.append("cpc_bid_micros")

        op.update_mask.CopyFrom(field_mask_pb2.FieldMask(paths=fields))

        try:
            resp = self.svc.mutate_ad_groups(
                customer_id=customer_id, operations=[op]
            )
        except GoogleAdsException as exc:
            handle_google_ads_exception(exc)

        return {"resource_name": resp.results[0].resource_name, "updated_fields": fields}

    def remove(self, customer_id: str, ad_group_id: str) -> dict:
        customer_id = normalize_customer_id(customer_id)
        rn = self.svc.ad_group_path(customer_id, ad_group_id)
        op = self.client.get_type("AdGroupOperation")
        op.remove = rn

        try:
            resp = self.svc.mutate_ad_groups(
                customer_id=customer_id, operations=[op]
            )
        except GoogleAdsException as exc:
            handle_google_ads_exception(exc)

        return {"removed": resp.results[0].resource_name}
