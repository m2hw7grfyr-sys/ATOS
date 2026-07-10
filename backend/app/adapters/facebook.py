from app.adapters.base import ScaffoldAdapter


class FacebookAdapter(ScaffoldAdapter):
    platform = "facebook"
    adapter_name = "FacebookAdapter"
    version = "v1-scaffold"
    capabilities = {"BROWSE", "LIKE", "PROFILE_VISIT"}
