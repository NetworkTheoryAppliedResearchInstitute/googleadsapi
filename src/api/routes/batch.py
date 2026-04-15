"""Batch job routes — build entire campaign structures from JSON config."""

from fastapi import APIRouter, Depends, Query

from src.api.deps import get_batch_service, verify_api_key
from src.services.batch_service import BatchService

router = APIRouter(
    prefix="/customers/{customer_id}/batch",
    tags=["Batch Operations"],
    dependencies=[Depends(verify_api_key)],
)


@router.post("/build-campaign", status_code=202)
def build_campaign_from_config(
    customer_id: str,
    config: dict,
    ad_grants_account: bool = Query(False),
    svc: BatchService = Depends(get_batch_service),
):
    """Build a complete campaign structure (budget→campaign→ad groups→ads→keywords)
    from a JSON config in a single batch job.

    Example config body:
    ```json
    {
        "name": "My Campaign",
        "daily_budget_micros": 10000000,
        "bidding_strategy_type": "MANUAL_CPC",
        "geo_target_constant_ids": [1014221],
        "language_constant_ids": [1000],
        "ad_groups": [
            {
                "name": "Ad Group 1",
                "cpc_bid_micros": 1000000,
                "keywords": [
                    {"text": "donate online", "match_type": "PHRASE"}
                ],
                "ads": [
                    {
                        "headlines": [
                            {"text": "Donate Today"},
                            {"text": "Support Our Mission"},
                            {"text": "Make a Difference"}
                        ],
                        "descriptions": [
                            {"text": "Your donation helps communities in need."},
                            {"text": "100% of funds go directly to programs."}
                        ],
                        "final_urls": ["https://example.org/donate"]
                    }
                ]
            }
        ]
    }
    ```
    """
    return svc.build_campaign_structure(customer_id, config, ad_grants_account)


@router.get("/jobs/{batch_job_id}/status")
def get_batch_job_status(
    customer_id: str,
    batch_job_id: str,
    svc: BatchService = Depends(get_batch_service),
):
    """Poll status of an async batch job."""
    batch_job_rn = f"customers/{customer_id}/batchJobs/{batch_job_id}"
    ga_service = svc.client.get_service("GoogleAdsService")
    # Use the service directly to get job status without blocking
    batch_job = svc.svc.get_batch_job(resource_name=batch_job_rn)
    return {
        "status": batch_job.status.name,
        "operation_count": batch_job.metadata.operation_count,
        "executed_operation_count": batch_job.metadata.executed_operation_count,
        "resource_name": batch_job_rn,
    }


@router.get("/jobs/{batch_job_id}/results")
def get_batch_job_results(
    customer_id: str,
    batch_job_id: str,
    page_size: int = Query(100, le=1000),
    svc: BatchService = Depends(get_batch_service),
):
    """Retrieve results of a completed batch job."""
    batch_job_rn = f"customers/{customer_id}/batchJobs/{batch_job_id}"
    return svc.get_results(batch_job_rn, page_size=page_size)
