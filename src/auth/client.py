"""
Google Ads API client factory.

Supports all three authentication flows:
  - OAuth2 refresh token  (client_id / client_secret / refresh_token in YAML)
  - Service account       (json_key_file_path in YAML)
  - Application default   (use_application_default_credentials: true in YAML)
"""

import os
from functools import lru_cache

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException


API_VERSION: str = os.getenv("GOOGLE_ADS_API_VERSION", "v20")


@lru_cache(maxsize=1)
def get_client(yaml_path: str | None = None) -> GoogleAdsClient:
    """Return a cached GoogleAdsClient instance.

    Args:
        yaml_path: Explicit path to google-ads.yaml.
                   Falls back to GOOGLE_ADS_YAML_PATH env var, then ~/google-ads.yaml.
    """
    path = (
        yaml_path
        or os.getenv("GOOGLE_ADS_YAML_PATH")
        or os.path.expanduser("~/google-ads.yaml")
    )
    return GoogleAdsClient.load_from_storage(path=path, version=API_VERSION)


def get_client_from_env() -> GoogleAdsClient:
    """Build a GoogleAdsClient from environment variables directly (no YAML file).

    Required env vars:
        GOOGLE_ADS_DEVELOPER_TOKEN
        GOOGLE_ADS_CLIENT_ID
        GOOGLE_ADS_CLIENT_SECRET
        GOOGLE_ADS_REFRESH_TOKEN
    Optional:
        GOOGLE_ADS_LOGIN_CUSTOMER_ID
    """
    credentials = {
        "developer_token": os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"],
        "client_id": os.environ["GOOGLE_ADS_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_ADS_CLIENT_SECRET"],
        "refresh_token": os.environ["GOOGLE_ADS_REFRESH_TOKEN"],
        "use_proto_plus": True,
    }
    login_cid = os.getenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID")
    if login_cid:
        credentials["login_customer_id"] = login_cid
    return GoogleAdsClient.load_from_dict(credentials, version=API_VERSION)


def normalize_customer_id(customer_id: str) -> str:
    """Strip dashes from a customer ID so the API always receives digits only."""
    return customer_id.replace("-", "")


def resource_name_to_id(resource_name: str) -> str:
    """Extract the trailing numeric ID from an API resource name.

    Example: 'customers/123/campaigns/456' → '456'
    """
    return resource_name.split("/")[-1]
