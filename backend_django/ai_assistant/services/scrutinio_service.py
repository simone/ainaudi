"""
Scrutinio data persistence service.

All DB writes for election section data go through here.
"""
import logging
import re
from typing import Optional

from .audit_service import AuditService

logger = logging.getLogger(__name__)


def _resolve_sezione(sezione_numero_raw, user_sections_list=None):
    """Resolve sezione from user-provided number string."""
    from territory.models import SezioneElettorale

    sezione = None
    sezione_numero = str(sezione_numero_raw or "").strip().replace(".", "").replace(" ", "")
    sezione_not_found = False
    if sezione_numero:
        try:
            numero_int = int(sezione_numero)
            if user_sections_list:
                for s in user_sections_list:
                    if s.get("numero") == numero_int and s.get("sezione_id"):
                        sezione = SezioneElettorale.objects.filter(
                            id=s["sezione_id"], is_attiva=True
                        ).first()
                        if sezione:
                            return sezione, sezione_numero, False

            sezione = SezioneElettorale.objects.filter(
                numero=numero_int, is_attiva=True
            ).first()
            if not sezione:
                sezione_not_found = True
        except (ValueError, TypeError):
            sezione_not_found = True
    return sezione, sezione_numero, sezione_not_found


def _parse_int(value):
    if value is None:
        return None
    try:
        return int(float(str(value)))
    except (ValueError, TypeError):
        return None


def _match_scheda(scheda_nome, schede_qs):
    """Find the best matching SchedaElettorale from a queryset."""
    if not scheda_nome:
        if schede_qs.count() == 1:
            return schede_qs.first(), None
        return None, None

    nome_lower = scheda_nome.lower().strip()
    schede_list = list(schede_qs)

    for s in schede_list:
        if s.nome.lower() == nome_lower:
            return s, None

    for s in schede_list:
        if nome_lower in s.nome.lower() or s.nome.lower() in nome_lower:
            return s, None

    numbers = re.findall(r"\d+", scheda_nome)
    if numbers:
        target_num = numbers[-1]
        for s in schede_list:
            scheda_nums = re.findall(r"\d+", s.nome)
            if scheda_nums and scheda_nums[-1] == target_num:
                return s, None

    nomi_disponibili = ", ".join([s.nome for s in schede_list])
    return None, f"Scheda '{scheda_nome}' non trovata. Schede disponibili: {nomi_disponibili}"


class ScrutinioService:
    """Handles all scrutinio data persistence operations."""

    @staticmethod
    def get_status(args: dict, user, user_sections_list: Optional[list] = None) -> dict:
        """Retrieve current scrutinio status for a section."""
        from elections.models import ConsultazioneElettorale, SchedaElettorale
        from data.models import DatiSezione, DatiScheda
        from delegations.permissions import can_enter_section_data

        sezione, sezione_numero, not_found = _resolve_sezione(
            args.get("sezione_numero", ""), user_sections_list
        )
        if not sezione:
            if not_found:
                return {"message": f"Sezione {sezione_numero} non trovata.", "data": None}
            return {"message": "Numero sezione non specificato.", "data": None}

        consultazione = ConsultazioneElettorale.objects.filter(is_attiva=True).first()
        if not consultazione:
            return {"message": "Nessuna consultazione attiva.", "data": None}

        if not can_enter_section_data(user, sezione, consultazione.id):
            return {
                "message": f"Non hai i permessi per accedere alla sezione {sezione.numero}.",
                "data": None,
            }

        dati_sezione, _ = DatiSezione.objects.get_or_create(
            sezione=sezione,
            consultazione=consultazione,
            defaults={"inserito_da_email": user.email},
        )

        loc = f"Sezione {sezione.numero} ({sezione.comune.nome}"
        if sezione.indirizzo:
            loc += f", {sezione.indirizzo}"
        if sezione.denominazione:
            loc += f" - {sezione.denominazione}"
        loc += ")"

        lines = [f"**Stato scrutinio -- {loc}**\n"]

        lines.append("**Dati Seggio:**")
        seggio_fields = [
            ("Elettori maschi", dati_sezione.elettori_maschi),
            ("Elettori femmine", dati_sezione.elettori_femmine),
            ("Votanti maschi", dati_sezione.votanti_maschi),
            ("Votanti femmine", dati_sezione.votanti_femmine),
        ]
        for label, val in seggio_fields:
            lines.append(f"  {label}: {val if val is not None else chr(8212)}")

        if dati_sezione.totale_elettori is not None:
            lines.append(f"  _Totale elettori: {dati_sezione.totale_elettori}_")
        if dati_sezione.affluenza_percentuale is not None:
            lines.append(f"  _Affluenza: {dati_sezione.affluenza_percentuale}%_")

        schede = SchedaElettorale.objects.filter(
            tipo_elezione__consultazione=consultazione
        ).order_by("ordine")

        for scheda in schede:
            try:
                ds = DatiScheda.objects.get(dati_sezione=dati_sezione, scheda=scheda)
                has_data = any([
                    ds.schede_ricevute is not None,
                    ds.schede_autenticate is not None,
                    ds.voti,
                    ds.schede_bianche is not None,
                ])
                if has_data:
                    lines.append(f"\n**{scheda.nome}:**")
                    if ds.schede_ricevute is not None:
                        lines.append(f"  Schede ricevute: {ds.schede_ricevute}")
                    if ds.schede_autenticate is not None:
                        lines.append(f"  Schede autenticate: {ds.schede_autenticate}")
                    if ds.voti:
                        if "si" in ds.voti:
                            lines.append(
                                f"  Voti SI: {ds.voti['si']} | NO: {ds.voti.get('no', chr(8212))}"
                            )
                        else:
                            lines.append(f"  Voti: {ds.voti}")
                    for lbl, field in [
                        ("Bianche", ds.schede_bianche),
                        ("Nulle", ds.schede_nulle),
                        ("Contestate", ds.schede_contestate),
                    ]:
                        if field is not None:
                            lines.append(f"  {lbl}: {field}")
                else:
                    lines.append(f"\n**{scheda.nome}:** nessun dato")
            except DatiScheda.DoesNotExist:
                lines.append(f"\n**{scheda.nome}:** nessun dato")

        if dati_sezione.updated_by_email:
            ts = (
                dati_sezione.updated_at.strftime("%d/%m/%Y %H:%M")
                if dati_sezione.updated_at
                else chr(8212)
            )
            lines.append(f"\n_Ultimo aggiornamento: {dati_sezione.updated_by_email}, {ts}_")

        lines.append("\nDimmi quali dati vuoi inserire o aggiornare.")
        return {"message": "\n".join(lines), "data": {"sezione_id": sezione.id}}

    @staticmethod
    def save_data(
        args: dict,
        session,
        user,
        ip_address: str,
        user_sections_list: Optional[list] = None,
    ) -> dict:
        """Save scrutinio data with partial update and audit trail."""
        from django.db import transaction
        from django.db.models import F
        from django.utils import timezone
        from elections.models import ConsultazioneElettorale, SchedaElettorale
        from data.models import DatiSezione, DatiScheda, SectionDataHistory
        from delegations.permissions import can_enter_section_data

        logger.info("save_scrutinio_data called with args: %s", args)

        sezione, sezione_numero, not_found = _resolve_sezione(
            args.get("sezione_numero", ""), user_sections_list
        )
        if not sezione:
            if not_found:
                return {"message": f"Sezione {sezione_numero} non trovata nel sistema.", "data": None}
            return {"message": "Numero sezione non specificato.", "data": None}

        consultazione = ConsultazioneElettorale.objects.filter(is_attiva=True).first()
        if not consultazione:
            return {"message": "Nessuna consultazione attiva.", "data": None}

        if not can_enter_section_data(user, sezione, consultazione.id):
            return {
                "message": f"Non hai i permessi per inserire dati nella sezione {sezione.numero}.",
                "data": None,
            }

        changes = []

        try:
            with transaction.atomic():
                dati_sezione, created = DatiSezione.objects.get_or_create(
                    sezione=sezione,
                    consultazione=consultazione,
                    defaults={
                        "inserito_da_email": user.email,
                        "inserito_at": timezone.now(),
                    },
                )
                if not created:
                    dati_sezione = DatiSezione.objects.select_for_update().get(
                        pk=dati_sezione.pk
                    )

                # Update DatiSezione (turnout) fields
                seggio_fields = {
                    "elettori_maschi": "Elettori maschi",
                    "elettori_femmine": "Elettori femmine",
                    "votanti_maschi": "Votanti maschi",
                    "votanti_femmine": "Votanti femmine",
                }
                seggio_changed = False
                for field_name, label in seggio_fields.items():
                    if field_name in args and args[field_name] is not None:
                        new_val = _parse_int(args[field_name])
                        if new_val is not None:
                            old_val = getattr(dati_sezione, field_name)
                            if old_val != new_val:
                                changes.append((label, old_val, new_val, None))
                                SectionDataHistory.objects.create(
                                    dati_sezione=dati_sezione,
                                    campo=field_name,
                                    valore_precedente=(
                                        str(old_val) if old_val is not None else None
                                    ),
                                    valore_nuovo=str(new_val),
                                    modificato_da_email=user.email,
                                    ip_address=ip_address,
                                )
                                setattr(dati_sezione, field_name, new_val)
                                seggio_changed = True

                if seggio_changed:
                    dati_sezione.version = F("version") + 1
                    dati_sezione.updated_by_email = user.email
                    dati_sezione.inserito_da_email = (
                        dati_sezione.inserito_da_email or user.email
                    )
                    dati_sezione.inserito_at = dati_sezione.inserito_at or timezone.now()
                    dati_sezione.save()
                    dati_sezione.refresh_from_db()

                # Update DatiScheda (ballot-specific) fields
                scheda_field_names = [
                    "schede_ricevute", "schede_autenticate", "schede_bianche",
                    "schede_nulle", "schede_contestate", "voti_si", "voti_no",
                ]
                has_scheda_data = any(
                    field in args and args[field] is not None
                    for field in scheda_field_names
                )

                if has_scheda_data:
                    schede_qs = SchedaElettorale.objects.filter(
                        tipo_elezione__consultazione=consultazione
                    ).order_by("ordine")

                    matched_scheda, match_error = _match_scheda(
                        args.get("scheda_nome"), schede_qs
                    )
                    if match_error:
                        return {"message": match_error, "data": None}
                    if not matched_scheda:
                        nomi = ", ".join([s.nome for s in schede_qs])
                        return {
                            "message": f"Quale scheda vuoi aggiornare? Schede disponibili: {nomi}",
                            "data": None,
                        }

                    dati_scheda, _ = DatiScheda.objects.get_or_create(
                        dati_sezione=dati_sezione, scheda=matched_scheda
                    )
                    dati_scheda = DatiScheda.objects.select_for_update().get(
                        pk=dati_scheda.pk
                    )

                    scheda_fields = {
                        "schede_ricevute": "Schede ricevute",
                        "schede_autenticate": "Schede autenticate",
                        "schede_bianche": "Schede bianche",
                        "schede_nulle": "Schede nulle",
                        "schede_contestate": "Schede contestate",
                    }
                    scheda_changed = False
                    for field_name, label in scheda_fields.items():
                        if field_name in args and args[field_name] is not None:
                            new_val = _parse_int(args[field_name])
                            if new_val is not None:
                                old_val = getattr(dati_scheda, field_name)
                                if old_val != new_val:
                                    changes.append(
                                        (f"{label} ({matched_scheda.nome})", old_val, new_val, dati_scheda)
                                    )
                                    SectionDataHistory.objects.create(
                                        dati_sezione=dati_sezione,
                                        dati_scheda=dati_scheda,
                                        campo=field_name,
                                        valore_precedente=(
                                            str(old_val) if old_val is not None else None
                                        ),
                                        valore_nuovo=str(new_val),
                                        modificato_da_email=user.email,
                                        ip_address=ip_address,
                                    )
                                    setattr(dati_scheda, field_name, new_val)
                                    scheda_changed = True

                    # Handle voti (SI/NO for referendum)
                    voti_si = _parse_int(args.get("voti_si"))
                    voti_no = _parse_int(args.get("voti_no"))
                    if voti_si is not None or voti_no is not None:
                        old_voti = dati_scheda.voti or {}
                        new_voti = dict(old_voti)
                        if voti_si is not None:
                            old_si = old_voti.get("si")
                            new_voti["si"] = voti_si
                            if old_si != voti_si:
                                changes.append(
                                    (f"Voti SI ({matched_scheda.nome})", old_si, voti_si, dati_scheda)
                                )
                                scheda_changed = True
                        if voti_no is not None:
                            old_no = old_voti.get("no")
                            new_voti["no"] = voti_no
                            if old_no != voti_no:
                                changes.append(
                                    (f"Voti NO ({matched_scheda.nome})", old_no, voti_no, dati_scheda)
                                )
                                scheda_changed = True
                        if scheda_changed:
                            dati_scheda.voti = new_voti
                            SectionDataHistory.objects.create(
                                dati_sezione=dati_sezione,
                                dati_scheda=dati_scheda,
                                campo="voti",
                                valore_precedente=str(old_voti) if old_voti else None,
                                valore_nuovo=str(new_voti),
                                modificato_da_email=user.email,
                                ip_address=ip_address,
                            )

                    if scheda_changed:
                        dati_scheda.validate_data()
                        dati_scheda.version = F("version") + 1
                        dati_scheda.updated_by_email = user.email
                        dati_scheda.inserito_at = dati_scheda.inserito_at or timezone.now()
                        dati_scheda.save()

                # Invalidate cache
                if changes:
                    ConsultazioneElettorale.objects.filter(id=consultazione.id).update(
                        data_version=timezone.now()
                    )

        except Exception as e:
            logger.error("Error in save_scrutinio_data: %s", e, exc_info=True)
            return {"message": f"Errore nel salvataggio: {str(e)}", "data": None}

        if not changes:
            return {
                "message": "Nessun dato da aggiornare (i valori sono gli stessi).",
                "data": None,
            }

        loc = f"Sezione {sezione.numero} ({sezione.comune.nome})"
        lines = [f"**Dati salvati per {loc}:**\n"]
        for campo, old_val, new_val, _ in changes:
            old_str = str(old_val) if old_val is not None else chr(8212)
            lines.append(f"  {campo}: {old_str} -> **{new_val}**")

        AuditService.log_scrutinio(user, "SCRUTINIO_UPDATE", sezione.id, {
            "source": "ai_chat",
            "session_id": session.id,
            "sezione_id": sezione.id,
            "sezione_numero": sezione.numero,
            "changes": [
                {
                    "campo": c[0],
                    "old": str(c[1]) if c[1] is not None else None,
                    "new": str(c[2]),
                }
                for c in changes
            ],
        })

        logger.info(
            "Scrutinio data saved for sezione %s by %s: %d changes via AI chat",
            sezione.numero, user.email, len(changes),
        )

        return {
            "message": "\n".join(lines),
            "data": {"sezione_id": sezione.id, "changes": len(changes)},
        }

    @staticmethod
    def build_preview(args: dict, reason: str, user_sections_list: Optional[list] = None) -> dict:
        """Build a preview of what would be saved without persisting."""
        sezione, sezione_numero, _ = _resolve_sezione(
            args.get("sezione_numero", ""), user_sections_list
        )

        loc = (
            f"Sezione {sezione.numero} ({sezione.comune.nome})"
            if sezione
            else f"Sezione {sezione_numero}"
            if sezione_numero
            else "Sezione non specificata"
        )

        lines = [f"**ANTEPRIMA** (non salvata):\n"]
        lines.append(f"**{loc}**\n")

        seggio_fields = {
            "elettori_maschi": "Elettori maschi",
            "elettori_femmine": "Elettori femmine",
            "votanti_maschi": "Votanti maschi",
            "votanti_femmine": "Votanti femmine",
        }
        for field_name, label in seggio_fields.items():
            val = _parse_int(args.get(field_name))
            if val is not None:
                lines.append(f"  {label}: **{val}**")

        scheda_fields = {
            "schede_ricevute": "Schede ricevute",
            "schede_autenticate": "Schede autenticate",
            "schede_bianche": "Schede bianche",
            "schede_nulle": "Schede nulle",
            "schede_contestate": "Schede contestate",
            "voti_si": "Voti SI",
            "voti_no": "Voti NO",
        }
        scheda_nome = args.get("scheda_nome")
        has_scheda = False
        for field_name, label in scheda_fields.items():
            val = _parse_int(args.get(field_name))
            if val is not None:
                if not has_scheda and scheda_nome:
                    lines.append(f"\n**{scheda_nome}:**")
                    has_scheda = True
                lines.append(f"  {label}: **{val}**")

        lines.append(f"\n_{reason}_")

        return {"message": "\n".join(lines), "data": None}
