from fastapi import APIRouter, Depends

from src.api.deps import get_targeting_service, verify_api_key
from src.models.targeting import (
    GeoTargetRequest,
    LanguageTargetRequest,
    DemographicTargetRequest,
    DeviceTargetRequest,
    AdScheduleRequest,
    AudienceTargetRequest,
)
from src.services.targeting_service import TargetingService

router = APIRouter(
    prefix="/customers/{customer_id}/targeting",
    tags=["Targeting"],
    dependencies=[Depends(verify_api_key)],
)


@router.post("/geo", status_code=201)
def add_geo_target(
    customer_id: str,
    body: GeoTargetRequest,
    svc: TargetingService = Depends(get_targeting_service),
):
    return svc.add_geo_target(customer_id, body)


@router.post("/language", status_code=201)
def add_language_target(
    customer_id: str,
    body: LanguageTargetRequest,
    svc: TargetingService = Depends(get_targeting_service),
):
    return svc.add_language_target(customer_id, body)


@router.post("/demographics", status_code=201)
def add_demographic_targets(
    customer_id: str,
    body: DemographicTargetRequest,
    svc: TargetingService = Depends(get_targeting_service),
):
    return svc.add_demographic_targets(customer_id, body)


@router.post("/device", status_code=201)
def set_device_bid_modifier(
    customer_id: str,
    body: DeviceTargetRequest,
    svc: TargetingService = Depends(get_targeting_service),
):
    return svc.set_device_bid_modifier(customer_id, body)


@router.post("/schedule", status_code=201)
def add_ad_schedule(
    customer_id: str,
    body: AdScheduleRequest,
    svc: TargetingService = Depends(get_targeting_service),
):
    return svc.add_ad_schedule(customer_id, body)


@router.post("/audience", status_code=201)
def add_audience_target(
    customer_id: str,
    body: AudienceTargetRequest,
    svc: TargetingService = Depends(get_targeting_service),
):
    return svc.add_audience_target(customer_id, body)
