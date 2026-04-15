from fastapi import APIRouter, Depends, Query

from src.api.deps import get_rsa_service, verify_api_key
from src.models.ads import CreateRSARequest, UpdateRSARequest
from src.services.rsa_service import RSAService

router = APIRouter(
    prefix="/customers/{customer_id}/ads",
    tags=["Responsive Search Ads"],
    dependencies=[Depends(verify_api_key)],
)


@router.get("/")
def list_ads(
    customer_id: str,
    ad_group_id: str = Query(...),
    svc: RSAService = Depends(get_rsa_service),
):
    return svc.list(customer_id, ad_group_id)


@router.get("/{ad_id}")
def get_ad(
    customer_id: str,
    ad_id: str,
    ad_group_id: str = Query(...),
    svc: RSAService = Depends(get_rsa_service),
):
    return svc.get(customer_id, ad_group_id, ad_id)


@router.get("/{ad_id}/performance")
def get_ad_performance(
    customer_id: str,
    ad_id: str,
    ad_group_id: str = Query(...),
    date_range: str = Query("LAST_30_DAYS"),
    svc: RSAService = Depends(get_rsa_service),
):
    return svc.get_performance(customer_id, ad_group_id, date_range)


@router.post("/", status_code=201)
def create_rsa(
    customer_id: str,
    body: CreateRSARequest,
    svc: RSAService = Depends(get_rsa_service),
):
    return svc.create(customer_id, body)


@router.patch("/{ad_id}")
def update_rsa(
    customer_id: str,
    ad_id: str,
    ad_group_id: str = Query(...),
    body: UpdateRSARequest = ...,
    svc: RSAService = Depends(get_rsa_service),
):
    return svc.update(customer_id, ad_group_id, ad_id, body)


@router.delete("/{ad_id}")
def remove_ad(
    customer_id: str,
    ad_id: str,
    ad_group_id: str = Query(...),
    svc: RSAService = Depends(get_rsa_service),
):
    return svc.remove(customer_id, ad_group_id, ad_id)
