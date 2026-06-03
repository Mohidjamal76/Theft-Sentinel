import logging
import re

from django.db import IntegrityError
from rest_framework import serializers

from apps.accounts.validation import normalize_cnic

from .models import Branch, CnicRegistry, SuperAdminProfile

logger = logging.getLogger(__name__)

CNIC_DUPLICATE_MESSAGE = "This CNIC is already registered in the system."


def cnic_key(value) -> str:
    """Return the 13-digit comparison key for a CNIC value."""
    normalized = normalize_cnic(value)
    return re.sub(r"[\s-]+", "", normalized)


def branch_owner(branch_id) -> tuple[str, str]:
    return ("BRANCH_ADMIN", str(branch_id))


def partner_owner(profile_id, index) -> tuple[str, str]:
    return ("SUPER_ADMIN_PARTNER", f"{profile_id}:{index}")


def _owner_allowed(owner_type: str, owner_id: str, allowed_owners) -> bool:
    if not allowed_owners:
        return False
    return (str(owner_type), str(owner_id)) in {
        (str(item[0]), str(item[1])) for item in allowed_owners
    }


def _iter_stored_cnic_owners():
    for branch in Branch.objects.all().only("id", "admin_cnic"):
        if getattr(branch, "admin_cnic", None):
            try:
                yield cnic_key(branch.admin_cnic), branch_owner(branch.id)
            except serializers.ValidationError:
                logger.warning("Skipping invalid stored branch CNIC for branch %s", branch.id)

    for profile in SuperAdminProfile.objects.all().only("id", "partners"):
        for idx, partner in enumerate(profile.partners or []):
            cnic = (partner or {}).get("cnic")
            if cnic:
                try:
                    yield cnic_key(cnic), partner_owner(profile.id, idx)
                except serializers.ValidationError:
                    logger.warning("Skipping invalid stored partner CNIC for profile %s", profile.id)


def validate_unique_cnic(value, allowed_owners=None) -> str:
    """
    Normalize a CNIC and verify that no other CNIC-bearing entity uses it.

    The registry gives a database-level unique index for new writes; the direct
    scan catches pre-existing rows that may not have been backfilled because
    they were duplicates in legacy data.
    """
    normalized = normalize_cnic(value)
    key = cnic_key(normalized)

    registry_matches = CnicRegistry.objects.filter(cnic=key)
    for match in registry_matches:
        if not _owner_allowed(match.owner_type, match.owner_id, allowed_owners):
            raise serializers.ValidationError(CNIC_DUPLICATE_MESSAGE)

    for stored_key, owner in _iter_stored_cnic_owners():
        if stored_key == key and not _owner_allowed(owner[0], owner[1], allowed_owners):
            raise serializers.ValidationError(CNIC_DUPLICATE_MESSAGE)

    return normalized


def validate_unique_cnic_list(values, allowed_owners=None) -> list[str]:
    normalized_values = [normalize_cnic(value) for value in values]
    seen = set()
    for value in normalized_values:
        key = cnic_key(value)
        if key in seen:
            raise serializers.ValidationError(CNIC_DUPLICATE_MESSAGE)
        seen.add(key)
        validate_unique_cnic(value, allowed_owners=allowed_owners)
    return normalized_values


def _replace_owner_registration(owner_type: str, owner_id: str, cnic_value: str) -> None:
    key = cnic_key(cnic_value)
    CnicRegistry.objects.filter(owner_type=owner_type, owner_id=owner_id).exclude(cnic=key).delete()
    try:
        CnicRegistry.objects.update_or_create(
            cnic=key,
            defaults={"owner_type": owner_type, "owner_id": owner_id},
        )
    except IntegrityError:
        logger.exception("CNIC registry conflict for %s:%s", owner_type, owner_id)
        raise serializers.ValidationError(CNIC_DUPLICATE_MESSAGE)


def sync_branch_admin_cnic(branch: Branch) -> None:
    if not branch or not getattr(branch, "admin_cnic", None):
        return
    owner_type, owner_id = branch_owner(branch.id)
    _replace_owner_registration(owner_type, owner_id, branch.admin_cnic)


def unregister_branch_admin_cnic(branch: Branch) -> None:
    if not branch:
        return
    owner_type, owner_id = branch_owner(branch.id)
    CnicRegistry.objects.filter(owner_type=owner_type, owner_id=owner_id).delete()


def sync_super_admin_partner_cnics(profile: SuperAdminProfile) -> None:
    if not profile:
        return

    owner_prefix = f"{profile.id}:"
    for row in CnicRegistry.objects.filter(owner_type="SUPER_ADMIN_PARTNER"):
        if str(row.owner_id).startswith(owner_prefix):
            row.delete()

    for idx, partner in enumerate(profile.partners or []):
        cnic = (partner or {}).get("cnic")
        if not cnic:
            continue
        owner_type, owner_id = partner_owner(profile.id, idx)
        _replace_owner_registration(owner_type, owner_id, cnic)
