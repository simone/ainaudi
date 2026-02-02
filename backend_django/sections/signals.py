"""
Signals for sections app - RDL registration provisioning.

Handles user provisioning when:
1. RdlRegistration status changes to APPROVED
2. Email changes on an already approved RdlRegistration

Note: The approve() method on RdlRegistration already handles initial approval,
but this signal ensures consistency even if status is changed directly or email is updated.
"""
import logging
from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from core.models import User, RoleAssignment, AuditLog
from .models import RdlRegistration

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=RdlRegistration)
def track_rdl_registration_changes(sender, instance, **kwargs):
    """
    Track status and email changes for comparison in post_save.
    """
    if instance.pk:
        try:
            old_instance = RdlRegistration.objects.get(pk=instance.pk)
            instance._old_status = old_instance.status
            instance._old_email = old_instance.email
            instance._old_user_id = old_instance.user_id
        except RdlRegistration.DoesNotExist:
            instance._old_status = None
            instance._old_email = None
            instance._old_user_id = None
    else:
        instance._old_status = None
        instance._old_email = None
        instance._old_user_id = None


def ensure_user_and_role(instance, user_created_flag=None):
    """
    Ensure user exists and has RDL role for approved registration.
    Returns (user, user_created)
    """
    if not instance.email:
        logger.warning(f"RdlRegistration {instance.id} has no email")
        return None, False

    defaults = {
        'display_name': instance.full_name,
        'first_name': instance.nome,
        'last_name': instance.cognome,
        'phone_number': instance.telefono,
    }

    user, user_created = User.objects.get_or_create(
        email=instance.email.lower().strip(),
        defaults=defaults
    )

    # Link user to registration if not already linked
    if instance.user_id != user.id:
        instance.user = user
        instance.save(update_fields=['user'])

    # Assign RDL role
    RoleAssignment.objects.get_or_create(
        user=user,
        role=RoleAssignment.Role.RDL,
        defaults={
            'assigned_by': instance.approved_by,
            'is_active': True,
        }
    )

    return user, user_created


@receiver(post_save, sender=RdlRegistration)
def provision_rdl_on_approval(sender, instance, created, **kwargs):
    """
    When RdlRegistration status changes to APPROVED or email changes on approved registration,
    ensure user is provisioned.
    """
    old_status = getattr(instance, '_old_status', None)
    old_email = getattr(instance, '_old_email', None)

    # Check if status changed to APPROVED
    is_newly_approved = (
        instance.status == RdlRegistration.Status.APPROVED and
        (created or old_status != RdlRegistration.Status.APPROVED)
    )

    # Check if email changed on already approved registration
    new_email = instance.email.lower().strip() if instance.email else None
    old_email_normalized = old_email.lower().strip() if old_email else None
    email_changed = (
        instance.status == RdlRegistration.Status.APPROVED and
        not created and
        old_status == RdlRegistration.Status.APPROVED and
        new_email != old_email_normalized
    )

    if is_newly_approved:
        # New approval - provision user
        try:
            with transaction.atomic():
                user, user_created = ensure_user_and_role(instance)

                if user:
                    AuditLog.objects.create(
                        user=user,
                        action=AuditLog.Action.CREATE,
                        target_model='RdlRegistration',
                        target_id=str(instance.id),
                        details={
                            'provisioning': 'signal',
                            'trigger': 'approval',
                            'user_created': user_created,
                            'comune': str(instance.comune) if instance.comune else None,
                        }
                    )
                    logger.info(f"User provisioned via signal for RdlRegistration {instance.id}: {user.email}")

        except Exception as e:
            logger.error(f"Failed to provision user for RdlRegistration {instance.id}: {e}")

    elif email_changed:
        # Email changed on approved registration - update user link
        try:
            with transaction.atomic():
                logger.info(f"RdlRegistration {instance.id}: email changed from {old_email} to {instance.email}")

                user, user_created = ensure_user_and_role(instance)

                if user:
                    AuditLog.objects.create(
                        user=user,
                        action=AuditLog.Action.UPDATE,
                        target_model='RdlRegistration',
                        target_id=str(instance.id),
                        details={
                            'provisioning': 'signal',
                            'trigger': 'email_change',
                            'old_email': old_email,
                            'new_email': instance.email,
                            'user_created': user_created,
                        }
                    )
                    logger.info(f"User updated via signal for RdlRegistration {instance.id}: {user.email}")

        except Exception as e:
            logger.error(f"Failed to update user for RdlRegistration {instance.id}: {e}")
