"""Small, campaign-owned play preferences carried by the existing save/read path."""

DEFAULTS = {"focus": "mixed", "dialogue": "normal"}
VALUES = {"focus": {"mixed", "hunt-explore", "conquest"},
          "dialogue": {"normal", "minimal", "on-request"}}


def validate_preferences(value):
    from .engine import fail
    if (type(value) is not dict or not value or value.keys() - VALUES.keys() or
            any(type(item) is not str or item not in VALUES[key] for key, item in value.items())):
        fail(422, "invalid_campaign_preferences",
             "Use focus=mixed|hunt-explore|conquest and dialogue=normal|minimal|on-request")


def preferences(state):
    return {**DEFAULTS, **state.get("campaign_preferences", {})}


def apply_preferences(before, state, changes):
    if "campaign_preferences" in changes:
        patch = changes["campaign_preferences"]
        validate_preferences(patch)
        state["campaign_preferences"] = {**preferences(before), **patch}
