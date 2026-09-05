"""Helpers for merging and writing arm.yaml from the Settings GUI."""
import re

SECRET_KEY_RE = re.compile(r"_KEY$|_API$|_PASSWORD$|MAKEMKV_PERMA_KEY|ARM_API_KEY")
SECRET_PLACEHOLDER = "********"

# Keys that should be treated as booleans when saving from the form
BOOL_KEYS = frozenset({
    "DISABLE_LOGIN",
    "ARM_CHECK_UDF",
    "GET_VIDEO_TITLE",
    "SKIP_TRANSCODE",
    "MANUAL_WAIT",
    "SET_MEDIA_PERMISSIONS",
    "SET_MEDIA_OWNER",
    "DELRAWFILES",
    "HASHEDKEYS",
    "MAINFEATURE",
    "USE_FFMPEG",
    "EMBY_REFRESH",
    "NOTIFY_RIP",
    "NOTIFY_TRANSCODE",
    "NOTIFY_JOBID",
    "UNIDENTIFIED_WAIT",
    "HB_HW_AUTO",
})

METADATA_KEYS = ("METADATA_PROVIDER", "OMDB_API_KEY", "TMDB_API_KEY")


def is_secret_key(key):
    return bool(SECRET_KEY_RE.search(key))


def coerce_bool_string(value):
    """Normalize form values to 'true'/'false' strings for yaml."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "false"
    text = str(value).strip().lower()
    if text in ("", "0", "no", "off", "false", "none"):
        return "false"
    if text in ("1", "yes", "on", "true"):
        return "true"
    return text


def display_value_for_form(key, value):
    """Value shown in the settings form (secrets masked)."""
    if is_secret_key(key) and value not in (None, "", False):
        return SECRET_PLACEHOLDER
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return ""
    return value


def merge_arm_config_from_form(current_config, form_data):
    """
    Merge POST form data onto a copy of the current arm_config.

    - Skips csrf_token
    - Empty secret fields keep the existing value
    - Placeholder secret fields keep the existing value
    - Bool keys are normalized to true/false strings for yaml writers
    """
    merged = dict(current_config)
    for key, value in form_data.items():
        if key == "csrf_token":
            continue
        if key not in merged and key not in BOOL_KEYS and not is_secret_key(key):
            # Allow new keys only if they look like ARM config keys
            if not re.match(r"^[A-Z][A-Z0-9_]+$", key):
                continue

        if isinstance(value, str):
            value = value.strip()

        if is_secret_key(key):
            if value in ("", SECRET_PLACEHOLDER):
                continue  # keep existing
            merged[key] = value
            continue

        if key in BOOL_KEYS or (
            key in merged and isinstance(merged.get(key), bool)
        ):
            merged[key] = coerce_bool_string(value)
            continue

        # Preserve ints when the current value is int and form is digits
        if key in merged and isinstance(merged.get(key), int):
            try:
                merged[key] = int(value)
                continue
            except (TypeError, ValueError):
                pass

        merged[key] = value

    return merged


def build_arm_cfg_from_dict(config_dict, comments, form_order=None):
    """
    Build arm.yaml text from a full config dict (already merged).

    form_order: optional key order (e.g. POST key order); remaining keys follow
    current dict insertion order.
    """
    from arm.config import config_utils

    arm_cfg = comments["ARM_CFG_GROUPS"]["BEGIN"] + "\n\n"
    keys = []
    if form_order:
        for key in form_order:
            if key != "csrf_token" and key in config_dict:
                keys.append(key)
    for key in config_dict:
        if key not in keys:
            keys.append(key)

    for key in keys:
        value = config_dict[key]
        arm_cfg += config_utils.arm_yaml_check_groups(comments, key)
        try:
            arm_cfg += "\n" + comments[str(key)] + "\n" if comments[str(key)] != "" else ""
        except KeyError:
            arm_cfg += "\n"

        if isinstance(value, bool):
            arm_cfg += f"{key}: {str(value).lower()}\n"
            continue
        if isinstance(value, int) and not isinstance(value, bool):
            arm_cfg += f"{key}: {value}\n"
            continue

        text = "" if value is None else str(value)
        if key in BOOL_KEYS:
            arm_cfg += config_utils.arm_yaml_test_bool(key, coerce_bool_string(text))
        else:
            arm_cfg += config_utils.arm_yaml_test_bool(key, text)

    return arm_cfg
