from app.adapters.base import ScaffoldAdapter


class TikTokAdapter(ScaffoldAdapter):
    platform = "tiktok"
    adapter_name = "TikTokAdapter"
    version = "v1-scaffold"
    capabilities = {"BROWSE", "LIKE", "PROFILE_VISIT"}
