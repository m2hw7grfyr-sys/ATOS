from app.adapters.base import ScaffoldAdapter


class InstagramAdapter(ScaffoldAdapter):
    platform = "instagram"
    adapter_name = "InstagramAdapter"
    version = "v1-scaffold"
    capabilities = {"BROWSE", "LIKE", "PROFILE_VISIT"}
