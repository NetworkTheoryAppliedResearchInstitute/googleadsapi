from typing import Optional

from fastapi import APIRouter, Depends, Query

from src.api.deps import get_ad_group_service, verify_api_key
from src.models.ad_groups import CreateAdGroupRequest, UpdateAdGroupRequest
from src.services.ad_group_service import AdGroupService

router = APIRouter(
    prefix="/customers/{customer_id}/ad-groups",
    tags=["Ad Groups"],
    dependencies=[Depends(verify_api_key)],
)


@router.get("/")
def list_ad_groups(
    customer_id: str,
    campaign_id: Optional[str] = Query(None),
    svc: AdGroupService = Depends(get_ad_group_service),
):
    return svc.list(customer_id, campaign_id)


@router.get("/{ad_group_id}")
def get_ad_group(
    customer_id: str,
    ad_group_id: str,
    svc: AdGroupService = Depends(get_ad_group_service),
):
    return svc.get(customer_id, ad_group_id)


@router.post("/", status_code=201)
def create_ad_group(
    customer_id: str,
    body: CreateAdGroupRequest,
    svc: AdGroupService = Depends(get_ad_group_service),
):
    return svc.create(customer_id, body)


@router.patch("/{ad_group_id}")
def update_ad_group(
    customer_id: str,
    ad_group_id: str,
    body: UpdateAdGroupRequest,
    svc: AdGroupService = Depends(get_ad_group_service),
):
    return svc.update(customer_id, ad_group_id, body)


@router.delete("/{ad_group_id}")
def remove_ad_group(
    customer_id: str,
    ad_group_id: str,
    svc: AdGroupService = Depends(get_ad_group_service),
):
    return svc.remove(customer_id, ad_group_id)
