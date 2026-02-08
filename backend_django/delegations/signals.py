"""
Signals for automatic user provisioning based on domain events.

This module implements event-driven user creation and role assignment:
- Delegato created/updated → ensure user + DELEGATE role
- SubDelega created/updated → ensure user + SUBDELEGATE role
- DesignazioneRDL created/updated/activated → ensure user + RDL role

Design principles:
- Idempotent: uses get_or_create to avoid duplicates
- Unique constraint: email is the unique identifier
- Audit: logs all provisioning actions
- Domain-driven: roles derive from domain entities, not manual assignment
- Update handling: tracks email changes, updates user links accordingly
"""
import logging
from django.db import IntegrityError, transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from core.models import User, RoleAssignment, AuditLog
from .models import Delegato, SubDelega, DesignazioneRDL

# Cache per tracciare i valori pre-save (email precedente)
_pre_save_cache = {}

logger = logging.getLogger(__name__)


def ensure_user_exists(email, defaults=None):
    """
    Ensure a user exists with the given email.

    Idempotent: returns existing user or creates new one.
    Handles race conditions with retry logic.

    Args:
        email: User's email (unique identifier)
        defaults: Dict of default values for new user

    Returns:
        tuple: (user, created) where created is True if user was just created
    """
    if not email:
        logger.warning("ensure_user_exists called with empty email")
        return None, False

    email = email.lower().strip()
    defaults = defaults or {}

    try:
        with transaction.atomic():
            user, created = User.objects.get_or_create(
                email=email,
                defaults=defaults
            )

            if created:
                logger.info(f"User created via provisioning: {email}")
            else:
                # Update display_name if not set and we have a better one
                if not user.display_name and defaults.get('display_name'):
                    user.display_name = defaults['display_name']
                    user.save(update_fields=['display_name'])

            return user, created

    except IntegrityError:
        # Race condition: another process created the user
        # Retry with get
        user = User.objects.filter(email=email).first()
        if user:
            logger.info(f"User found after IntegrityError (race condition): {email}")
            return user, False
        raise


def ensure_role_assigned(user, role, scope_type=None, scope_value=None, assigned_by_email=None):
    """
    Ensure a user has a specific role assigned.

    Idempotent: returns existing assignment or creates new one.

    Args:
        user: User instance
        role: Role string (from RoleAssignment.Role choices)
        scope_type: Optional scope type
        scope_value: Optional scope value
        assigned_by_email: Optional email of user who assigned the role

    Returns:
        tuple: (role_assignment, created)
    """
    if not user:
        return None, False

    try:
        with transaction.atomic():
            assignment, created = RoleAssignment.objects.get_or_create(
                user=user,
                role=role,
                defaults={
                    'scope_type': scope_type,
                    'scope_value': scope_value,
                    'assigned_by_email': assigned_by_email or '',
                    'is_active': True,
                }
            )

            if created:
                logger.info(f"Role {role} assigned to {user.email}")

            return assignment, created

    except IntegrityError:
        assignment = RoleAssignment.objects.filter(
            user=user,
            role=role
        ).first()
        return assignment, False


def ensure_group_exists(group_name):
    """
    Assicura che un gruppo esista.

    Se il gruppo non esiste, lo crea (vuoto, senza permessi).
    I permessi vengono assegnati ai gruppi manualmente dall'admin tramite migrations.

    Args:
        group_name: Nome del gruppo

    Returns:
        Group instance
    """
    from django.contrib.auth.models import Group

    # Get or create group
    group, created = Group.objects.get_or_create(name=group_name)

    if created:
        logger.info(f"Created group {group_name} (permissions managed by admin)")

    return group


def assign_group_for_role(user, role):
    """
    Assegna il gruppo Django appropriato basato sul ruolo.

    Mapping ruolo → gruppo:
    - DELEGATE → Delegato
    - SUBDELEGATE → Subdelegato
    - RDL → RDL
    - KPI_VIEWER → Diretta

    Se il gruppo non esiste, lo crea (vuoto).
    I permessi sono gestiti dall'admin tramite migrations, non dai signals.
    I permessi vengono ereditati dal gruppo, non assegnati direttamente all'utente.

    Args:
        user: User instance
        role: Role string (da RoleAssignment.Role)
    """
    if not user or user.is_superuser:
        return

    # Mapping ruolo → nome gruppo
    role_to_group = {
        RoleAssignment.Role.DELEGATE: 'Delegato',
        RoleAssignment.Role.SUBDELEGATE: 'Subdelegato',
        RoleAssignment.Role.RDL: 'RDL',
        RoleAssignment.Role.KPI_VIEWER: 'Diretta',
    }

    group_name = role_to_group.get(role)
    if not group_name:
        logger.warning(f"No group mapping for role: {role}")
        return

    try:
        # Ensure group exists (without managing permissions)
        group = ensure_group_exists(group_name)

        # Add user to group (idempotente)
        user.groups.add(group)

        logger.info(f"Added {user.email} to group {group_name} for role {role}")

    except Exception as e:
        logger.error(f"Failed to assign group for {user.email}: {e}")


def log_provisioning_action(action, user, target_model, target_id, details=None):
    """Log a provisioning action to the audit log."""
    try:
        AuditLog.objects.create(
            user_email=user.email if user else '',
            action=action,
            target_model=target_model,
            target_id=str(target_id),
            details=details or {}
        )
    except Exception as e:
        logger.error(f"Failed to log provisioning action: {e}")


def get_pre_save_key(model_name, instance_pk):
    """Generate a cache key for pre_save data."""
    return f"{model_name}:{instance_pk}"


def cache_pre_save_email(model_name, instance):
    """Cache the current email before save (for update detection)."""
    if instance.pk:
        key = get_pre_save_key(model_name, instance.pk)
        try:
            old_instance = instance.__class__.objects.get(pk=instance.pk)
            _pre_save_cache[key] = {
                'email': getattr(old_instance, 'email', None),
            }
        except instance.__class__.DoesNotExist:
            pass


def get_cached_pre_save(model_name, instance_pk):
    """Retrieve cached pre_save data."""
    key = get_pre_save_key(model_name, instance_pk)
    return _pre_save_cache.pop(key, None)


def handle_email_change(instance, model_name, role, old_data, scope_type=None, scope_value=None):
    """
    Handle email change on an entity.

    When email changes:
    1. Create/get new user with new email
    2. Assign role to new user
    3. Optionally remove role from old user if no other entities linked
    """
    old_email = old_data.get('email') if old_data else None
    new_email = instance.email

    if not new_email:
        # Email cleared - nothing to provision
        logger.info(f"{model_name} {instance.pk}: email cleared")
        return None, False

    new_email = new_email.lower().strip()
    old_email = old_email.lower().strip() if old_email else None

    # No change
    if old_email == new_email:
        user = User.objects.filter(email=new_email).first()
        return user, False

    logger.info(f"{model_name} {instance.pk}: email changed from {old_email} to {new_email}")

    # Build user defaults
    defaults = {
        'display_name': getattr(instance, 'nome_completo', ''),
        'first_name': getattr(instance, 'nome', ''),
        'last_name': getattr(instance, 'cognome', ''),
    }
    if hasattr(instance, 'telefono') and instance.telefono:
        defaults['phone_number'] = instance.telefono

    # Ensure new user exists
    user, user_created = ensure_user_exists(new_email, defaults)

    if not user:
        logger.error(f"Failed to provision user for {model_name} {instance.pk}")
        return None, False

    # Assign role to new user
    ensure_role_assigned(
        user=user,
        role=role,
        scope_type=scope_type,
        scope_value=scope_value,
    )

    return user, user_created


def update_user_data(user, instance):
    """Update user data from instance if instance has newer/better data."""
    if not user:
        return

    changed = False

    # Update display_name if empty
    nome_completo = getattr(instance, 'nome_completo', None)
    if nome_completo and not user.display_name:
        user.display_name = nome_completo
        changed = True

    # Update phone if empty
    telefono = getattr(instance, 'telefono', None)
    if telefono and not user.phone_number:
        user.phone_number = telefono
        changed = True

    if changed:
        user.save()


# =============================================================================
# DELEGATO DI LISTA SIGNALS
# =============================================================================

@receiver(pre_save, sender=Delegato)
def delegato_pre_save(sender, instance, **kwargs):
    """Cache current email before save for change detection."""
    cache_pre_save_email('Delegato', instance)


@receiver(post_save, sender=Delegato)
def provision_delegato_user(sender, instance, created, **kwargs):
    """
    When a Delegato is created or updated, ensure user exists and has DELEGATE role.

    Triggered on: Delegato creation or update
    Actions:
        1. On create: Create user if not exists (using email), link, assign role
        2. On update with email change: Unlink old user, create/link new user, assign role
        3. On update without email change: Update user data if needed
        4. Log action
    """
    old_data = get_cached_pre_save('Delegato', instance.pk) if not created else None

    if not instance.email:
        if created:
            logger.warning(f"Delegato {instance.id} created without email, skipping provisioning")
        return

    if created:
        # New entity - provision user
        defaults = {
            'display_name': instance.nome_completo,
            'first_name': instance.nome,
            'last_name': instance.cognome,
        }

        user, user_created = ensure_user_exists(instance.email, defaults)

        if not user:
            logger.error(f"Failed to provision user for Delegato {instance.id}")
            return

        # Assign DELEGATE role
        ensure_role_assigned(
            user=user,
            role=RoleAssignment.Role.DELEGATE,
            scope_type=RoleAssignment.ScopeType.GLOBAL,
        )

        # Assign group basato sul ruolo
        assign_group_for_role(user, RoleAssignment.Role.DELEGATE)

        # Log action
        log_provisioning_action(
            action=AuditLog.Action.CREATE,
            user=user,
            target_model='Delegato',
            target_id=instance.id,
            details={
                'provisioning': 'auto',
                'user_created': user_created,
                'carica': instance.carica if instance.carica else None,
            }
        )
    else:
        # Update - check for email change
        old_email = old_data.get('email') if old_data else None
        new_email = instance.email.lower().strip() if instance.email else None

        if old_email != new_email:
            # Email changed
            user, user_created = handle_email_change(
                instance=instance,
                model_name='Delegato',
                role=RoleAssignment.Role.DELEGATE,
                old_data=old_data,
                scope_type=RoleAssignment.ScopeType.GLOBAL,
            )

            if user:
                log_provisioning_action(
                    action=AuditLog.Action.UPDATE,
                    user=user,
                    target_model='Delegato',
                    target_id=instance.id,
                    details={
                        'provisioning': 'auto',
                        'email_changed': True,
                        'old_email': old_email,
                        'new_email': new_email,
                        'user_created': user_created,
                    }
                )
        else:
            # No email change - just update user data if needed
            user = User.objects.filter(email=instance.email).first()
            if user:
                update_user_data(user, instance)


# =============================================================================
# SUBDELEGA SIGNALS
# =============================================================================

@receiver(pre_save, sender=SubDelega)
def subdelega_pre_save(sender, instance, **kwargs):
    """Cache current email before save for change detection."""
    cache_pre_save_email('SubDelega', instance)


@receiver(post_save, sender=SubDelega)
def provision_subdelegato_user(sender, instance, created, **kwargs):
    """
    When a SubDelega is created or updated, ensure user exists and has SUBDELEGATE role.

    Triggered on: SubDelega creation or update
    Actions:
        1. On create: Create user if not exists (using email), link, assign role
        2. On update with email change: Unlink old user, create/link new user, assign role
        3. On update without email change: Update user data if needed
        4. Log action
    """
    old_data = get_cached_pre_save('SubDelega', instance.pk) if not created else None

    if not instance.email:
        if created:
            logger.warning(f"SubDelega {instance.id} created without email, skipping provisioning")
        return

    if created:
        # New entity - provision user
        defaults = {
            'display_name': instance.nome_completo,
            'first_name': instance.nome,
            'last_name': instance.cognome,
            'phone_number': instance.telefono,
        }

        user, user_created = ensure_user_exists(instance.email, defaults)

        if not user:
            logger.error(f"Failed to provision user for SubDelega {instance.id}")
            return

        # Assign SUBDELEGATE role
        ensure_role_assigned(
            user=user,
            role=RoleAssignment.Role.SUBDELEGATE,
        )

        # Assign group basato sul ruolo
        assign_group_for_role(user, RoleAssignment.Role.SUBDELEGATE)

        # Log action
        log_provisioning_action(
            action=AuditLog.Action.CREATE,
            user=user,
            target_model='SubDelega',
            target_id=instance.id,
            details={
                'provisioning': 'auto',
                'user_created': user_created,
                'delegato': str(instance.delegato),
            }
        )
    else:
        # Update - check for email change
        old_email = old_data.get('email') if old_data else None
        new_email = instance.email.lower().strip() if instance.email else None

        if old_email != new_email:
            # Email changed
            user, user_created = handle_email_change(
                instance=instance,
                model_name='SubDelega',
                role=RoleAssignment.Role.SUBDELEGATE,
                old_data=old_data,
            )

            if user:
                log_provisioning_action(
                    action=AuditLog.Action.UPDATE,
                    user=user,
                    target_model='SubDelega',
                    target_id=instance.id,
                    details={
                        'provisioning': 'auto',
                        'email_changed': True,
                        'old_email': old_email,
                        'new_email': new_email,
                        'user_created': user_created,
                        'delegato': str(instance.delegato),
                    }
                )
        else:
            # No email change - just update user data if needed
            user = User.objects.filter(email=instance.email).first()
            if user:
                update_user_data(user, instance)


# =============================================================================
# DESIGNAZIONE RDL SIGNALS (SNAPSHOT FIELDS: campi diretti)
# =============================================================================

@receiver(post_save, sender=DesignazioneRDL)
def provision_rdl_users(sender, instance, created, **kwargs):
    """
    When a DesignazioneRDL is created or updated, ensure users exist for both effettivo and supplente.

    SNAPSHOT MODEL:
    - DesignazioneRDL now has direct fields (effettivo_email, supplente_email, etc.)
    - Provision user per effettivo (if email present)
    - Provision user per supplente (if email present)

    Triggered on: DesignazioneRDL creation or update
    Actions:
        1. Check effettivo_email and supplente_email
        2. For each email: Create user if not exists, assign RDL role
        3. Log action

    Note: This is separate from RdlRegistration approval flow.
    DesignazioneRDL is the formal designation (immutable snapshot).
    """
    # Get scope value for RDL role (sezione)
    scope_value = str(instance.sezione.numero) if instance.sezione else None

    # Provision effettivo RDL
    if instance.effettivo_email:
        defaults = {
            'display_name': f"{instance.effettivo_cognome} {instance.effettivo_nome}",
            'first_name': instance.effettivo_nome,
            'last_name': instance.effettivo_cognome,
            'phone_number': instance.effettivo_telefono or '',
        }

        user, user_created = ensure_user_exists(instance.effettivo_email, defaults)

        if user:
            # Assign RDL role with section scope
            ensure_role_assigned(
                user=user,
                role=RoleAssignment.Role.RDL,
                scope_type=RoleAssignment.ScopeType.SEZIONE,
                scope_value=scope_value,
            )

            # Assign group basato sul ruolo
            assign_group_for_role(user, RoleAssignment.Role.RDL)

            # Log action
            log_provisioning_action(
                action=AuditLog.Action.CREATE if created else AuditLog.Action.UPDATE,
                user=user,
                target_model='DesignazioneRDL',
                target_id=instance.id,
                details={
                    'provisioning': 'auto',
                    'user_created': user_created,
                    'sezione': str(instance.sezione),
                    'ruolo': 'EFFETTIVO',
                }
            )
        else:
            logger.error(f"Failed to provision user for effettivo RDL in DesignazioneRDL {instance.id}")

    # Provision supplente RDL
    if instance.supplente_email:
        defaults = {
            'display_name': f"{instance.supplente_cognome} {instance.supplente_nome}",
            'first_name': instance.supplente_nome,
            'last_name': instance.supplente_cognome,
            'phone_number': instance.supplente_telefono or '',
        }

        user, user_created = ensure_user_exists(instance.supplente_email, defaults)

        if user:
            # Assign RDL role with section scope
            ensure_role_assigned(
                user=user,
                role=RoleAssignment.Role.RDL,
                scope_type=RoleAssignment.ScopeType.SEZIONE,
                scope_value=scope_value,
            )

            # Assign group basato sul ruolo
            assign_group_for_role(user, RoleAssignment.Role.RDL)

            # Log action
            log_provisioning_action(
                action=AuditLog.Action.CREATE if created else AuditLog.Action.UPDATE,
                user=user,
                target_model='DesignazioneRDL',
                target_id=instance.id,
                details={
                    'provisioning': 'auto',
                    'user_created': user_created,
                    'sezione': str(instance.sezione),
                    'ruolo': 'SUPPLENTE',
                }
            )
        else:
            logger.error(f"Failed to provision user for supplente RDL in DesignazioneRDL {instance.id}")
