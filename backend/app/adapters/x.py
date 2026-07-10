from app.adapters.base import ScaffoldAdapter


class XAdapter(ScaffoldAdapter):
    platform = "x"
    adapter_name = "XAdapter"
    version = "v1-scaffold"
    capabilities = {"BROWSE", "LIKE", "PROFILE_VISIT"}
