from fastapi import APIRouter, Depends

from src.api.deps import get_keyword_service, verify_api_key
from src.models.keywords import (
    CreateKeywordRequest,
    CreateNegativeKeywordRequest,
    UpdateKeywordBidRequest,
    SharedNegativeListRequest,
    BulkCreateKeywordsRequest,
)
from src.services.keyword_service import KeywordService

router = APIRouter(
    prefix="/customers/{customer_id}/keywords",
    tags=["Keywords"],
    dependencies=[Depends(verify_api_key)],
)


@router.post("/", status_code=201)
def add_keyword(
    customer_id: str,
    body: CreateKeywordRequest,
    svc: KeywordService = Depends(get_keyword_service),
):
    return svc.add(customer_id, body)


@router.post("/bulk", status_code=201)
def add_keywords_bulk(
    customer_id: str,
    body: BulkCreateKeywordsRequest,
    svc: KeywordService = Depends(get_keyword_service),
):
    return svc.add_bulk(customer_id, body)


@router.post("/negatives", status_code=201)
def add_negative_keyword(
    customer_id: str,
    body: CreateNegativeKeywordRequest,
    svc: KeywordService = Depends(get_keyword_service),
):
    return svc.add_negative(customer_id, body)


@router.post("/shared-negative-lists", status_code=201)
def create_shared_negative_list(
    customer_id: str,
    body: SharedNegativeListRequest,
    svc: KeywordService = Depends(get_keyword_service),
):
    return svc.create_shared_negative_list(customer_id, body)


@router.patch("/")
def update_keyword(
    customer_id: str,
    body: UpdateKeywordBidRequest,
    svc: KeywordService = Depends(get_keyword_service),
):
    return svc.update(customer_id, body)


@router.delete("/{ad_group_id}/{criterion_id}")
def remove_keyword(
    customer_id: str,
    ad_group_id: str,
    criterion_id: str,
    svc: KeywordService = Depends(get_keyword_service),
):
    return svc.remove(customer_id, ad_group_id, criterion_id)


@router.get("/quality-scores/{ad_group_id}")
def get_quality_scores(
    customer_id: str,
    ad_group_id: str,
    svc: KeywordService = Depends(get_keyword_service),
):
    return svc.get_quality_scores(customer_id, ad_group_id)
