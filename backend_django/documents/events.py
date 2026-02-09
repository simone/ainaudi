"""
DEPRECATED - Event publisher for PDF generation using Redis Pub/Sub.

**Status**: OBSOLETO - Non più utilizzato

Questo modulo pubblicava eventi Redis per il worker PDF asincrono.
La generazione PDF è ora sincrona in delegations/views_processo.py.

Data deprecazione: Febbraio 2026
"""
import logging

logger = logging.getLogger(__name__)


def get_redis_client():
    """DEPRECATED - Redis client for PDF worker."""
    raise NotImplementedError(
        "Redis PDF events are deprecated. "
        "Use delegations.views_processo for synchronous PDF generation."
    )


def publish_preview_pdf_and_email(*args, **kwargs):
    """DEPRECATED - Use views_processo.genera_individuale() instead."""
    raise NotImplementedError(
        "Async PDF generation is deprecated. "
        "Use ProcessoDesignazione.genera_individuale() for synchronous generation."
    )


def publish_confirm_freeze(*args, **kwargs):
    """DEPRECATED - No longer needed."""
    raise NotImplementedError(
        "Freeze confirmation events are deprecated. "
        "Use ProcessoDesignazione.approva() instead."
    )
