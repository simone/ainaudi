"""
User profile and conversation context builder.

Builds the structured context passed to the LLM on every call.
Extracted from the monolithic generate_ai_response.
"""
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def build_user_profile_context(user, session) -> tuple[str, list[dict]]:
    """
    Build user profile context string and sections list.

    Returns:
        (profile_text, user_sections_list)
    """
    from delegations.models import DesignazioneRDL, Delegato, SubDelega
    from elections.models import ConsultazioneElettorale
    from django.db.models import Q

    user_sections_list = []

    try:
        user_name = f"{user.first_name} {user.last_name}".strip() or user.email
        now = datetime.now()

        consultazione = ConsultazioneElettorale.objects.filter(is_attiva=True).first()

        # Determine user role
        user_role = "RDL"
        role_description = "Rappresentante di Lista"
        if consultazione:
            is_delegato = Delegato.objects.filter(
                consultazione=consultazione, email=user.email
            ).exists()
            is_subdelegato = SubDelega.objects.filter(
                delegato__consultazione=consultazione, email=user.email
            ).exists()
            if is_delegato:
                user_role = "DELEGATO"
                role_description = "Delegato di Lista (supervisiona RDL nel suo territorio)"
            elif is_subdelegato:
                user_role = "SUBDELEGATO"
                role_description = "Sub-Delegato (supervisiona RDL nel suo territorio)"

        profile_parts = [
            f"DATA E ORA: {now.strftime('%A %d %B %Y, ore %H:%M')}",
            f"PROFILO UTENTE: {user_name} ({user.email})",
            f"RUOLO: {role_description}",
        ]

        if consultazione:
            profile_parts.append(_build_consultazione_context(consultazione, now))
            user_sections_list = _build_sections_context(
                user, consultazione, user_role, profile_parts
            )
            _build_scrutinio_context(user_sections_list, consultazione, profile_parts)
        else:
            profile_parts.append("CONSULTAZIONE: Nessuna consultazione attiva al momento")

        # Existing incident in session
        existing_incident_id = (session.metadata or {}).get("incident_id")
        if existing_incident_id:
            _build_incident_context(existing_incident_id, profile_parts)

        return "\n".join(profile_parts), user_sections_list

    except Exception as e:
        logger.warning("Error building user context: %s", e, exc_info=True)
        return f"PROFILO UTENTE: {user.email}", []


def _build_consultazione_context(consultazione, now: datetime) -> str:
    today = now.date()
    data_inizio = consultazione.data_inizio
    data_fine = consultazione.data_fine

    if data_inizio and data_fine:
        if today < data_inizio:
            days_until = (data_inizio - today).days
            fase = f"PRIMA della consultazione. Mancano {days_until} giorni all'inizio."
        elif today > data_fine:
            days_since = (today - data_fine).days
            fase = f"DOPO la consultazione. Terminata da {days_since} giorni."
        else:
            fase = "IN CORSO. Siamo nel periodo della consultazione."
    else:
        fase = "Date non disponibili."

    tipi_elezione = consultazione.tipi_elezione.all()
    tipi_names = (
        ", ".join([
            t.get_tipo_display() if hasattr(t, "get_tipo_display") else str(t)
            for t in tipi_elezione[:5]
        ])
        if tipi_elezione
        else ""
    )

    info = (
        f"L'UNICA CONSULTAZIONE ATTIVA E': {consultazione.nome}"
        f"{' (' + tipi_names + ')' if tipi_names else ''}\n"
        f"  Si vota dal {data_inizio.strftime('%A %d %B %Y') if data_inizio else '?'} "
        f"al {data_fine.strftime('%A %d %B %Y') if data_fine else '?'}\n"
        f"  {fase}\n"
        f"  Qualsiasi domanda su scrutinio, seggi, voto, schede si riferisce a QUESTA consultazione."
    )
    if consultazione.descrizione:
        info += f"\n  Dettagli: {consultazione.descrizione[:300]}"
    return info


def _build_sections_context(user, consultazione, user_role: str, profile_parts: list) -> list[dict]:
    from delegations.models import DesignazioneRDL
    from django.db.models import Q

    user_sections_list = []
    designazioni = DesignazioneRDL.objects.filter(
        Q(effettivo_email=user.email) | Q(supplente_email=user.email),
        processo__consultazione=consultazione,
        is_attiva=True,
    ).select_related("sezione", "sezione__comune", "sezione__municipio")

    for des in designazioni:
        sez = des.sezione
        if sez:
            user_sections_list.append({
                "sezione_id": sez.id,
                "id": sez.numero,
                "numero": sez.numero,
                "comune": sez.comune.nome,
                "municipio": sez.municipio.nome if sez.municipio else None,
                "indirizzo": sez.indirizzo,
                "denominazione": sez.denominazione,
            })

    if user_sections_list:
        sections_text = "\n".join([
            f"  - Sezione {s['numero']} di {s['comune']}"
            f"{' (' + s['municipio'] + ')' if s['municipio'] else ''}"
            f"{' - ' + s['indirizzo'] if s['indirizzo'] else ''}"
            for s in user_sections_list
        ])
        if user_role == "RDL":
            profile_parts.append(
                f"LE TUE SEZIONI ASSEGNATE (ACCETTA SOLO QUESTE per segnalazioni):\n{sections_text}"
            )
        else:
            profile_parts.append(f"SEZIONI ASSEGNATE COME RDL:\n{sections_text}")
    else:
        if user_role == "RDL":
            profile_parts.append("SEZIONI: Nessuna sezione ancora assegnata")
        else:
            profile_parts.append(
                "NOTA: Come delegato, puoi segnalare per qualsiasi sezione del tuo territorio"
            )

    return user_sections_list


def _build_scrutinio_context(user_sections_list: list, consultazione, profile_parts: list):
    if not user_sections_list:
        return

    try:
        from data.models import DatiSezione, DatiScheda
        from elections.models import SchedaElettorale

        schede = list(
            SchedaElettorale.objects.filter(
                tipo_elezione__consultazione=consultazione
            ).order_by("ordine")
        )
        if schede:
            schede_names = ", ".join([s.nome for s in schede])
            profile_parts.append(f"SCHEDE NELLA CONSULTAZIONE: {schede_names}")

        sezione_ids = [s["sezione_id"] for s in user_sections_list if s.get("sezione_id")]
        if not sezione_ids:
            return

        dati_sezioni = {
            ds.sezione_id: ds
            for ds in DatiSezione.objects.filter(
                sezione_id__in=sezione_ids, consultazione=consultazione
            ).select_related("sezione")
        }

        scrutinio_lines = []
        for sec_info in user_sections_list:
            sez_id = sec_info.get("sezione_id")
            ds = dati_sezioni.get(sez_id)
            if not ds:
                scrutinio_lines.append(f"  Sez.{sec_info['numero']}: nessun dato inserito")
                continue

            parts = []
            if ds.elettori_maschi is not None or ds.elettori_femmine is not None:
                em = ds.elettori_maschi if ds.elettori_maschi is not None else "?"
                ef = ds.elettori_femmine if ds.elettori_femmine is not None else "?"
                parts.append(f"elettori M={em}/F={ef}")
            if ds.votanti_maschi is not None or ds.votanti_femmine is not None:
                vm = ds.votanti_maschi if ds.votanti_maschi is not None else "?"
                vf = ds.votanti_femmine if ds.votanti_femmine is not None else "?"
                parts.append(f"votanti M={vm}/F={vf}")

            schede_dati = {
                sd.scheda_id: sd for sd in DatiScheda.objects.filter(dati_sezione=ds)
            }
            schede_complete = 0
            schede_details = []
            for scheda in schede:
                sd = schede_dati.get(scheda.id)
                if sd and any([sd.schede_ricevute is not None, sd.voti]):
                    schede_complete += 1
                    voti_str = ""
                    if sd.voti and "si" in sd.voti:
                        voti_str = f" SI={sd.voti['si']}/NO={sd.voti.get('no', '?')}"
                    detail = (
                        f"ric={sd.schede_ricevute or '?'}/aut={sd.schede_autenticate or '?'}"
                        f"{voti_str}"
                    )
                    if sd.schede_bianche is not None:
                        detail += f" bia={sd.schede_bianche}"
                    if sd.schede_nulle is not None:
                        detail += f" nul={sd.schede_nulle}"
                    schede_details.append(f"    {scheda.nome}: {detail}")
                else:
                    schede_details.append(f"    {scheda.nome}: vuoto")

            if parts:
                summary = ", ".join(parts)
                summary += f" | schede: {schede_complete}/{len(schede)}"
            else:
                summary = "nessun dato inserito"

            scrutinio_lines.append(f"  Sez.{sec_info['numero']}: {summary}")
            scrutinio_lines.extend(schede_details)

        if scrutinio_lines:
            profile_parts.append(
                "DATI SCRUTINIO ATTUALI (usa save_scrutinio_data per aggiornare):\n"
                + "\n".join(scrutinio_lines)
            )
    except Exception as e:
        logger.warning("Error loading scrutinio context: %s", e, exc_info=True)


def _build_incident_context(incident_id: int, profile_parts: list):
    try:
        from incidents.models import IncidentReport

        incident = IncidentReport.objects.get(id=incident_id)
        profile_parts.append(
            f"SEGNALAZIONE GIA APERTA IN QUESTA SESSIONE (ID #{incident.id}):\n"
            f"  Titolo: {incident.title}\n"
            f"  Descrizione: {incident.description[:200]}\n"
            f"  Categoria: {incident.category}\n"
            f"  Gravita: {incident.severity}\n"
            f"  Sezione: {incident.sezione.numero if incident.sezione else 'Generale'}\n"
            f"  -> Per modificarla, usa update_incident_report. NON creare una nuova."
        )
    except Exception:
        pass
