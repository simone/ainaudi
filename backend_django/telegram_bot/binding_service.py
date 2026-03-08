"""
Telegram identity binding service.

Handles phone number normalization, user lookup, binding creation/revocation.
"""
import re
import logging
from django.utils import timezone

from core.models import User
from .models import TelegramIdentityBinding

logger = logging.getLogger(__name__)


def normalize_phone_number(raw: str) -> str:
    """
    Normalize a phone number to E.164 format.
    Telegram sends numbers with leading '+' and no spaces.
    Strips everything except digits and leading '+'.
    Adds '+' prefix if missing, adds '+39' for bare Italian numbers.
    """
    cleaned = re.sub(r'[^\d+]', '', raw)
    if not cleaned.startswith('+'):
        # Assume Italian number if no country code
        if cleaned.startswith('39') and len(cleaned) >= 11:
            cleaned = '+' + cleaned
        else:
            cleaned = '+39' + cleaned
    return cleaned


def _extract_digits(phone: str) -> str:
    """Extract only digit characters from a phone string."""
    return re.sub(r'\D', '', phone)


def _extract_national_number(digits: str) -> str:
    """
    Extract the national part of an Italian phone number (strip country code).
    Handles both '39...' and '0039...' prefixes.
    Italian mobile numbers are 10 digits (3xx xxx xxxx).
    """
    # Handle 0039 international prefix
    if digits.startswith('0039') and len(digits) >= 13:
        national = digits[4:]
        if national[0] in ('0', '3'):
            return national
    # Handle 39 country code
    if digits.startswith('39') and len(digits) >= 11:
        national = digits[2:]
        if national[0] in ('0', '3'):
            return national
    return digits


def find_user_by_phone(phone_normalized: str) -> User | None:
    """
    Find an internal user by normalized phone number.

    Robust matching: extracts digits from both the incoming number and
    each DB phone_number, then compares national numbers. This handles
    any DB format: spaces, dashes, dots, missing/present country code.
    """
    target_national = _extract_national_number(_extract_digits(phone_normalized))

    users_with_phone = User.objects.filter(
        phone_number__isnull=False, is_active=True,
    ).exclude(phone_number='')

    for user in users_with_phone.iterator():
        db_digits = _extract_digits(user.phone_number)
        if not db_digits:
            continue
        if _extract_national_number(db_digits) == target_national:
            return user

    return None


def get_active_binding(telegram_user_id: int) -> TelegramIdentityBinding | None:
    """Get the active binding for a Telegram user, if any."""
    return TelegramIdentityBinding.objects.filter(
        telegram_user_id=telegram_user_id,
        binding_status=TelegramIdentityBinding.BindingStatus.ACTIVE,
    ).select_related('user').first()


def create_binding(
    telegram_user_id: int,
    telegram_chat_id: int,
    phone_normalized: str,
    user: User,
) -> TelegramIdentityBinding:
    """
    Create an ACTIVE binding between Telegram and internal user.
    Revokes any existing active bindings for this telegram_user_id or user first.
    """
    now = timezone.now()

    # Revoke existing bindings
    TelegramIdentityBinding.objects.filter(
        telegram_user_id=telegram_user_id,
        binding_status=TelegramIdentityBinding.BindingStatus.ACTIVE,
    ).update(binding_status=TelegramIdentityBinding.BindingStatus.REVOKED, updated_at=now)

    TelegramIdentityBinding.objects.filter(
        user=user,
        binding_status=TelegramIdentityBinding.BindingStatus.ACTIVE,
    ).update(binding_status=TelegramIdentityBinding.BindingStatus.REVOKED, updated_at=now)

    binding = TelegramIdentityBinding.objects.create(
        telegram_user_id=telegram_user_id,
        telegram_chat_id=telegram_chat_id,
        phone_number_normalized=phone_normalized,
        user=user,
        binding_status=TelegramIdentityBinding.BindingStatus.ACTIVE,
        first_bound_at=now,
        last_seen_at=now,
    )

    logger.info(
        "Telegram binding created: tg_user=%s → user=%s phone=%s",
        telegram_user_id, user.email, phone_normalized,
    )
    return binding


def revoke_binding(telegram_user_id: int) -> bool:
    """Revoke all active bindings for a Telegram user. Returns True if any were revoked."""
    updated = TelegramIdentityBinding.objects.filter(
        telegram_user_id=telegram_user_id,
        binding_status=TelegramIdentityBinding.BindingStatus.ACTIVE,
    ).update(
        binding_status=TelegramIdentityBinding.BindingStatus.REVOKED,
        updated_at=timezone.now(),
    )
    if updated:
        logger.info("Telegram binding revoked for tg_user=%s", telegram_user_id)
    return updated > 0


def touch_binding(binding: TelegramIdentityBinding) -> None:
    """Update last_seen_at timestamp."""
    TelegramIdentityBinding.objects.filter(pk=binding.pk).update(
        last_seen_at=timezone.now()
    )
