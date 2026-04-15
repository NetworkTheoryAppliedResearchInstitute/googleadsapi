from fastapi import APIRouter, Depends

from src.api.deps import get_campaign_service, verify_api_key
from src.models.campaigns import CreateCampaignRequest, UpdateCampaignRequest
from src.services.campaign_service import CampaignService

router = APIRouter(
    prefix="/customers/{customer_id}/campaigns",
    tags=["Campaigns"],
    dependencies=[Depends(verify_api_key)],
)


@router.get("/")
def list_campaigns(
    customer_id: str,
    svc: CampaignService = Depends(get_campaign_service),
):
    return svc.list(customer_id)


@router.get("/{campaign_id}")
def get_campaign(
    customer_id: str,
    campaign_id: str,
    svc: CampaignService = Depends(get_campaign_service),
):
    return svc.get(customer_id, campaign_id)


@router.post("/", status_code=201)
def create_campaign(
    customer_id: str,
    body: CreateCampaignRequest,
    svc: CampaignService = Depends(get_campaign_service),
):
    return svc.create(customer_id, body)


@router.patch("/{campaign_id}")
def update_campaign(
    customer_id: str,
    campaign_id: str,
    body: UpdateCampaignRequest,
    svc: CampaignService = Depends(get_campaign_service),
):
    return svc.update(customer_id, campaign_id, body)


@router.delete("/{campaign_id}")
def remove_campaign(
    customer_id: str,
    campaign_id: str,
    svc: CampaignService = Depends(get_campaign_service),
):
    return svc.remove(customer_id, campaign_id)
