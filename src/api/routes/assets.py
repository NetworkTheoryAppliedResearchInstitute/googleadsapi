from fastapi import APIRouter, Depends

from src.api.deps import get_asset_service, verify_api_key
from src.models.assets import CreateAssetRequest, LinkAssetRequest, AssetLinkLevel
from src.services.asset_service import AssetService

router = APIRouter(
    prefix="/customers/{customer_id}/assets",
    tags=["Assets"],
    dependencies=[Depends(verify_api_key)],
)


@router.post("/", status_code=201)
def create_asset(
    customer_id: str,
    body: CreateAssetRequest,
    svc: AssetService = Depends(get_asset_service),
):
    """Create an asset (sitelink, callout, call, price, etc.)."""
    return svc.create(customer_id, body)


@router.post("/link", status_code=201)
def link_asset(
    customer_id: str,
    body: LinkAssetRequest,
    svc: AssetService = Depends(get_asset_service),
):
    """Link an existing asset to an account, campaign, or ad group."""
    return svc.link(customer_id, body)


@router.patch("/pause-link")
def pause_asset_link(
    customer_id: str,
    asset_link_resource_name: str,
    link_level: AssetLinkLevel,
    svc: AssetService = Depends(get_asset_service),
):
    """Pause an asset association. Assets are immutable — only associations can be paused."""
    return svc.pause_link(customer_id, asset_link_resource_name, link_level)
