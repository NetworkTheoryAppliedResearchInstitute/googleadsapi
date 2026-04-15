"""BatchJobService wrapper — async bulk operations for campaign-scale builds.

Handles up to 1,000,000 operations per job with automatic retries.
Use for:
  - Building entire campaign structures (budget → campaign → ad groups → ads → keywords)
  - Bulk keyword uploads (hundreds to thousands)
  - Any sequence of related mutations that can tolerate async execution
"""

from __future__ import annotations

import time
from typing import Any

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
from google.api_core.exceptions import GoogleAPICallError

from src.auth.client import normalize_customer_id, resource_name_to_id
from src.utils.error_handling import handle_google_ads_exception

MAX_OPS_PER_REQUEST = 10_000
POLL_INTERVAL_SECONDS = 5
MAX_POLL_ATTEMPTS = 60  # 5 min max wait


class BatchService:
    def __init__(self, client: GoogleAdsClient) -> None:
        self.client = client
        self.svc = client.get_service("BatchJobService")

    def create_job(self, customer_id: str) -> str:
        """Create a new batch job and return its resource name."""
        customer_id = normalize_customer_id(customer_id)
        op = self.client.get_type("BatchJobOperation")
        # proto-plus oneof: must explicitly assign an empty BatchJob to the
        # create field — reading op.create returns a copy, not a reference.
        op.create = self.client.get_type("BatchJob")
        resp = self.svc.mutate_batch_job(customer_id=customer_id, operation=op)
        return resp.result.resource_name

    def add_operations(
        self,
        batch_job_resource_name: str,
        operations: list,
        sequence_token: str | None = None,
    ) -> str | None:
        """Add operations to a batch job in chunks of MAX_OPS_PER_REQUEST.

        Returns the last sequence_token (needed if job has >10,000 operations).
        """
        last_token = sequence_token
        for i in range(0, len(operations), MAX_OPS_PER_REQUEST):
            chunk = operations[i : i + MAX_OPS_PER_REQUEST]
            resp = self.svc.add_batch_job_operations(
                resource_name=batch_job_resource_name,
                mutate_operations=chunk,
                sequence_token=last_token,
            )
            last_token = resp.next_sequence_token or last_token
        return last_token

    def run_job(self, batch_job_resource_name: str) -> None:
        """Kick off async execution of the batch job."""
        self.svc.run_batch_job(resource_name=batch_job_resource_name)

    def _query_batch_job_status(self, customer_id: str, batch_job_resource_name: str):
        """Query batch job status via GoogleAdsService (get_batch_job removed in v20+)."""
        ga_svc = self.client.get_service("GoogleAdsService")
        query = f"""
            SELECT
                batch_job.status,
                batch_job.metadata.operation_count,
                batch_job.metadata.executed_operation_count
            FROM batch_job
            WHERE batch_job.resource_name = '{batch_job_resource_name}'
        """
        response = ga_svc.search(customer_id=normalize_customer_id(customer_id), query=query)
        for row in response:
            return row.batch_job
        return None

    def wait_for_completion(self, batch_job_resource_name: str, customer_id: str = "") -> dict:
        """Poll until the batch job completes or fails. Returns final status."""
        # Extract customer_id from resource name if not provided
        # Format: customers/{customer_id}/batchJobs/{job_id}
        if not customer_id:
            customer_id = batch_job_resource_name.split("/")[1]

        for attempt in range(MAX_POLL_ATTEMPTS):
            time.sleep(POLL_INTERVAL_SECONDS)
            batch_job = self._query_batch_job_status(customer_id, batch_job_resource_name)
            if batch_job is None:
                continue
            status = batch_job.status.name
            if status in ("DONE", "FAILED", "CANCELING", "CANCELED"):
                return {
                    "status": status,
                    "total_operations": batch_job.metadata.operation_count,
                    "executed_operations": batch_job.metadata.executed_operation_count,
                    "batch_job_resource_name": batch_job_resource_name,
                }
        return {
            "status": "TIMEOUT",
            "batch_job_resource_name": batch_job_resource_name,
        }

    def get_results(
        self,
        batch_job_resource_name: str,
        page_size: int = 1_000,
    ) -> list[dict]:
        """Retrieve the results of a completed batch job (up to 1,000 per page)."""
        results = []
        page_size = min(page_size, 1_000)
        for result in self.svc.list_batch_job_results(
            resource_name=batch_job_resource_name,
            page_size=page_size,
        ):
            entry: dict[str, Any] = {
                "operation_index": result.operation_index,
            }
            if result.mutate_operation_response:
                entry["response"] = str(result.mutate_operation_response)
            if result.status.message:
                entry["error"] = result.status.message
                entry["error_code"] = result.status.code
            results.append(entry)
        return results

    def submit_operations(
        self,
        customer_id: str,
        operations: list,
        wait: bool = True,
    ) -> dict:
        """One-shot: create job → add operations → run → optionally wait.

        This is the primary entry point for callers who have pre-built operations.

        Returns a dict with job metadata and, if wait=True, final status.
        """
        customer_id = normalize_customer_id(customer_id)
        job_rn = self.create_job(customer_id)
        self.add_operations(job_rn, operations)
        self.run_job(job_rn)

        result = {
            "batch_job_resource_name": job_rn,
            "batch_job_id": resource_name_to_id(job_rn),
            "operation_count": len(operations),
        }
        if wait:
            result.update(self.wait_for_completion(job_rn, customer_id=customer_id))
        return result

    # ── Campaign structure builder ────────────────────────────────────────────

    def build_campaign_structure(
        self,
        customer_id: str,
        config: dict,
        ad_grants_account: bool = False,
    ) -> dict:
        """Build an entire campaign structure using sequential direct mutate calls.

        Uses direct service calls (not BatchJob) to avoid temporary-ID
        restrictions that apply at lower developer token access levels.
        Each step returns a real resource name used by the next step.
        """
        customer_id = normalize_customer_id(customer_id)
        ops_count = 0

        # ── 1. Campaign budget ────────────────────────────────────────────────
        budget_svc = self.client.get_service("CampaignBudgetService")
        budget_op = self.client.get_type("CampaignBudgetOperation")
        b = budget_op.create
        b.name = f"{config['name']} Budget"
        b.amount_micros = config.get("daily_budget_micros", 10_000_000)
        b.explicitly_shared = False
        b.delivery_method = self.client.enums.BudgetDeliveryMethodEnum.STANDARD
        budget_resp = budget_svc.mutate_campaign_budgets(
            customer_id=customer_id, operations=[budget_op]
        )
        budget_rn = budget_resp.results[0].resource_name
        ops_count += 1

        # ── 2. Campaign ───────────────────────────────────────────────────────
        campaign_svc = self.client.get_service("CampaignService")
        campaign_op = self.client.get_type("CampaignOperation")
        c = campaign_op.create
        c.name = config["name"]
        c.campaign_budget = budget_rn
        c.status = self.client.enums.CampaignStatusEnum.PAUSED
        c.advertising_channel_type = self.client.enums.AdvertisingChannelTypeEnum[
            config.get("campaign_type", "SEARCH")
        ]
        ns_cfg = config.get("network_settings", {})
        c.network_settings.target_google_search = ns_cfg.get("target_google_search", True)
        c.network_settings.target_search_network = ns_cfg.get("target_search_network", False)
        c.network_settings.target_content_network = ns_cfg.get("target_content_network", False)
        c.contains_eu_political_advertising = self.client.enums.EuPoliticalAdvertisingStatusEnum.DOES_NOT_CONTAIN_EU_POLITICAL_ADVERTISING

        bst = config.get("bidding_strategy_type", "MANUAL_CPC")
        if bst == "MANUAL_CPC":
            c.manual_cpc.enhanced_cpc_enabled = False
        elif bst == "MAXIMIZE_CLICKS":
            c.maximize_clicks = self.client.get_type("MaximizeClicks")
        elif bst == "MAXIMIZE_CONVERSIONS":
            c.maximize_conversions = self.client.get_type("MaximizeConversions")
        elif bst == "TARGET_CPA":
            c.target_cpa.target_cpa_micros = config.get("target_cpa_micros", 5_000_000)
        elif bst == "TARGET_ROAS":
            c.target_roas.target_roas = config.get("target_roas", 2.0)

        campaign_resp = campaign_svc.mutate_campaigns(
            customer_id=customer_id, operations=[campaign_op]
        )
        campaign_rn = campaign_resp.results[0].resource_name
        ops_count += 1

        # ── 3. Geo + language criteria ────────────────────────────────────────
        criterion_svc = self.client.get_service("CampaignCriterionService")
        criterion_ops = []

        for geo_id in config.get("geo_target_constant_ids", []):
            op = self.client.get_type("CampaignCriterionOperation")
            op.create.campaign = campaign_rn
            op.create.location.geo_target_constant = f"geoTargetConstants/{geo_id}"
            criterion_ops.append(op)

        for lang_id in config.get("language_constant_ids", []):
            op = self.client.get_type("CampaignCriterionOperation")
            op.create.campaign = campaign_rn
            op.create.language.language_constant = f"languageConstants/{lang_id}"
            criterion_ops.append(op)

        if criterion_ops:
            criterion_svc.mutate_campaign_criteria(
                customer_id=customer_id, operations=criterion_ops
            )
            ops_count += len(criterion_ops)

        # ── 4. Ad groups, keywords, RSAs ──────────────────────────────────────
        ag_svc = self.client.get_service("AdGroupService")
        kw_svc = self.client.get_service("AdGroupCriterionService")
        ad_svc = self.client.get_service("AdGroupAdService")

        for ag_cfg in config.get("ad_groups", []):
            # Ad group
            ag_op = self.client.get_type("AdGroupOperation")
            ag = ag_op.create
            ag.name = ag_cfg["name"]
            ag.campaign = campaign_rn
            ag.status = self.client.enums.AdGroupStatusEnum.ENABLED
            ag.type_ = self.client.enums.AdGroupTypeEnum[
                ag_cfg.get("ad_group_type", "SEARCH_STANDARD")
            ]
            cpc = ag_cfg.get("cpc_bid_micros")
            if cpc:
                ag.cpc_bid_micros = min(cpc, 2_000_000) if ad_grants_account else cpc

            ag_resp = ag_svc.mutate_ad_groups(
                customer_id=customer_id, operations=[ag_op]
            )
            ag_rn = ag_resp.results[0].resource_name
            ops_count += 1

            # Keywords (batch up to 1000 per call)
            kw_ops = []
            for kw_cfg in ag_cfg.get("keywords", []):
                op = self.client.get_type("AdGroupCriterionOperation")
                kw = op.create
                kw.ad_group = ag_rn
                kw.status = self.client.enums.AdGroupCriterionStatusEnum.ENABLED
                kw.keyword.text = kw_cfg["text"]
                kw.keyword.match_type = self.client.enums.KeywordMatchTypeEnum[
                    kw_cfg.get("match_type", "PHRASE")
                ]
                bid = kw_cfg.get("cpc_bid_micros")
                if bid:
                    kw.cpc_bid_micros = min(bid, 2_000_000) if ad_grants_account else bid
                kw_ops.append(op)

            for i in range(0, len(kw_ops), 1000):
                kw_svc.mutate_ad_group_criteria(
                    customer_id=customer_id, operations=kw_ops[i : i + 1000]
                )
                ops_count += len(kw_ops[i : i + 1000])

            # RSAs
            for ad_cfg in ag_cfg.get("ads", []):
                ad_op = self.client.get_type("AdGroupAdOperation")
                aga = ad_op.create
                aga.ad_group = ag_rn
                aga.status = self.client.enums.AdGroupAdStatusEnum.PAUSED

                for hl in ad_cfg.get("headlines", []):
                    asset = self.client.get_type("AdTextAsset")
                    asset.text = hl["text"] if isinstance(hl, dict) else hl
                    if isinstance(hl, dict) and hl.get("pinned_field"):
                        asset.pinned_field = self.client.enums.ServedAssetFieldTypeEnum[
                            hl["pinned_field"]
                        ]
                    aga.ad.responsive_search_ad.headlines.append(asset)

                for desc in ad_cfg.get("descriptions", []):
                    asset = self.client.get_type("AdTextAsset")
                    asset.text = desc["text"] if isinstance(desc, dict) else desc
                    aga.ad.responsive_search_ad.descriptions.append(asset)

                for url in ad_cfg.get("final_urls", []):
                    aga.ad.final_urls.append(url)

                path1 = ad_cfg.get("path1")
                path2 = ad_cfg.get("path2")
                if path1:
                    aga.ad.responsive_search_ad.path1 = path1
                if path2:
                    aga.ad.responsive_search_ad.path2 = path2

                ad_svc.mutate_ad_group_ads(
                    customer_id=customer_id, operations=[ad_op]
                )
                ops_count += 1

        return {
            "status": "DONE",
            "campaign_resource_name": campaign_rn,
            "budget_resource_name": budget_rn,
            "total_operations": ops_count,
            "executed_operations": ops_count,
        }
