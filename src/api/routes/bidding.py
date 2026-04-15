from fastapi import APIRouter, Depends

from src.api.deps import get_bidding_service, verify_api_key
from src.models.bidding import CreatePortfolioBiddingStrategyRequest
from src.services.bidding_service import BiddingService

router = APIRouter(
    prefix="/customers/{customer_id}/bidding-strategies",
    tags=["Bidding Strategies"],
    dependencies=[Depends(verify_api_key)],
)


@router.get("/")
def list_bidding_strategies(
    customer_id: str,
    svc: BiddingService = Depends(get_bidding_service),
):
    return svc.list(customer_id)


@router.post("/", status_code=201)
def create_portfolio_strategy(
    customer_id: str,
    body: CreatePortfolioBiddingStrategyRequest,
    svc: BiddingService = Depends(get_bidding_service),
):
    return svc.create(customer_id, body)


@router.delete("/{strategy_id}")
def remove_strategy(
    customer_id: str,
    strategy_id: str,
    svc: BiddingService = Depends(get_bidding_service),
):
    return svc.remove(customer_id, strategy_id)
