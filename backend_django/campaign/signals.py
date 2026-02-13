"""
Signals for campaign app.

Geocodes RdlRegistration on save (idempotent):
- New record: always geocode
- Update: re-geocode only if address fields changed
- Partial update (update_fields) that doesn't touch address: skip entirely

After geocoding, computes sezioni_vicine (top 10 nearest sections in the
same comune).
"""
import logging

from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils import timezone

logger = logging.getLogger(__name__)

_TOP_SEZIONI = 10


@receiver(pre_save, sender='campaign.RdlRegistration')
def _capture_old_address(sender, instance, **kwargs):
    """Stash the old address on the instance before save."""
    from territory.geocoding import build_rdl_address

    if instance.pk:
        try:
            old = sender.objects.get(pk=instance.pk)
            instance._old_geocode_address = build_rdl_address(old)
        except sender.DoesNotExist:
            instance._old_geocode_address = None
    else:
        instance._old_geocode_address = None


@receiver(post_save, sender='campaign.RdlRegistration')
def geocode_rdl_on_save(sender, instance, created, update_fields, **kwargs):
    """
    Geocode an RDL after save, then compute sezioni_vicine.

    Skips if:
    - update_fields doesn't touch address fields (e.g. status-only update)
    - Already geocoded and address hasn't changed
    """
    from territory.geocoding import build_rdl_address, geocode_address

    # Partial update that doesn't touch address fields → skip
    if update_fields is not None:
        address_fields = {'indirizzo_residenza', 'comune_residenza',
                          'indirizzo_domicilio', 'comune_domicilio', 'fuorisede'}
        if not address_fields & set(update_fields):
            return

    new_address = build_rdl_address(instance)
    if not new_address or new_address.strip(', ') in ('Italia', ''):
        return

    old_address = getattr(instance, '_old_geocode_address', None)

    # Idempotent: skip geocoding if already geocoded and address unchanged
    already_geocoded = not created and instance.latitudine is not None
    address_changed = old_address != new_address

    if already_geocoded and not address_changed:
        # Address unchanged: skip geocoding, but refresh sezioni_vicine if empty
        if not instance.sezioni_vicine:
            sezioni_vicine = _find_sezioni_vicine(
                instance.comune_id,
                float(instance.latitudine),
                float(instance.longitudine),
            )
            if sezioni_vicine:
                sender.objects.filter(pk=instance.pk).update(
                    sezioni_vicine=sezioni_vicine,
                )
                logger.info(
                    "RDL %s: refreshed sezioni_vicine (%d plessi)",
                    instance.pk, len(sezioni_vicine),
                )
        return

    if already_geocoded and address_changed:
        logger.info(
            "RDL %s address changed: '%s' -> '%s', re-geocoding",
            instance.pk, old_address, new_address,
        )

    result = geocode_address(new_address)
    if result is None:
        logger.warning("Geocode failed for RDL %s: %s", instance.pk, new_address)
        return

    lat, lon, place_id, location_type = result

    # Compute nearby sections
    sezioni_vicine = _find_sezioni_vicine(instance.comune_id, lat, lon)

    # Save via queryset.update() to avoid re-triggering signals
    sender.objects.filter(pk=instance.pk).update(
        latitudine=lat,
        longitudine=lon,
        geocoded_at=timezone.now(),
        geocode_source='google',
        geocode_quality=location_type,
        geocode_place_id=place_id,
        sezioni_vicine=sezioni_vicine,
    )
    logger.info(
        "Geocoded RDL %s (%s %s): %s -> %s, %s (%s) - %d sezioni vicine",
        instance.pk, instance.cognome, instance.nome,
        new_address, lat, lon, location_type, len(sezioni_vicine),
    )


def _find_sezioni_vicine(comune_id, lat, lon):
    """
    Return the top N nearest plessi (grouped by address) in the same comune.

    Sections sharing the same address are grouped into a single entry.
    Distance is computed once per unique address (using the first section's coords).

    Returns list of dicts sorted by distance ascending:
    [
        {
            "indirizzo": "VIA CAMPANIA, 63",
            "distanza_km": 0.34,
            "sezioni": [18, 19, 20, 21, 2182]
        },
        ...
    ]
    """
    from collections import defaultdict

    from territory.geocoding import haversine_km
    from territory.models import SezioneElettorale

    sezioni = SezioneElettorale.objects.filter(
        comune_id=comune_id,
        latitudine__isnull=False,
        longitudine__isnull=False,
    ).only('id', 'numero', 'indirizzo', 'latitudine', 'longitudine')

    # Group by address → {indirizzo: [(numero, lat, lon), ...]}
    by_address = defaultdict(list)
    for s in sezioni:
        key = (s.indirizzo or '').strip().upper()
        by_address[key].append(s)

    # Compute distance per unique address (use first section's coords)
    plessi = []
    for key, group in by_address.items():
        ref = group[0]
        dist = haversine_km(lat, lon, float(ref.latitudine), float(ref.longitudine))
        plessi.append((dist, key, group))

    plessi.sort(key=lambda x: x[0])

    return [
        {
            'indirizzo': group[0].indirizzo or '',
            'distanza_km': round(dist, 2),
            'sezioni': sorted(s.numero for s in group),
        }
        for dist, key, group in plessi[:_TOP_SEZIONI]
    ]
