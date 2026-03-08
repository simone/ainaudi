"""
Telegram update router and handlers.

Dispatches incoming Telegram updates to the appropriate handler
based on content type: commands, contact sharing, text messages.
"""
import logging

from . import telegram_client
from . import binding_service
from . import message_service

logger = logging.getLogger(__name__)

# Messages
MSG_ONBOARDING = (
    "Ciao, sono Ainaudino. Per iniziare devo riconoscerti.\n"
    "Premi il pulsante qui sotto per condividere il tuo numero di telefono."
)
MSG_ALREADY_BOUND = "Ciao {name}, sei gia collegato. Scrivimi e ti aiuto!"
MSG_RECOGNIZED = "Ciao {name}, ti ho riconosciuto. Da questo momento puoi parlare con Ainaudino direttamente da Telegram."
MSG_NOT_RECOGNIZED = "Il tuo numero non risulta abilitato all'uso di questo servizio."
MSG_UNSUPPORTED = "Per ora posso gestire solo messaggi testuali."
MSG_HELP = (
    "Sono Ainaudino, l'assistente AI di AInaudi.\n\n"
    "Scrivimi un messaggio e ti aiutero con:\n"
    "- Procedure elettorali\n"
    "- Inserimento dati scrutinio\n"
    "- Segnalazioni\n"
    "- Domande generali\n\n"
    "Comandi disponibili:\n"
    "/start - Avvia il bot\n"
    "/help - Mostra queste istruzioni\n"
    "/whoami - Mostra la tua identita\n"
    "/reset - Scollega il tuo account"
)
MSG_RESET_OK = "Account scollegato. Per ricollegarti, usa /start e condividi di nuovo il tuo numero."
MSG_RESET_NO_BINDING = "Non hai un account collegato. Usa /start per iniziare."
MSG_BACKEND_ERROR = "Ainaudino non riesce a rispondere in questo momento. Riprova tra qualche secondo!"
MSG_NOT_PRIVATE = "Posso funzionare solo in chat privata."


def handle_update(update: dict) -> None:
    """
    Main dispatcher for Telegram updates.
    Only processes 'message' updates in private chats.
    """
    message = update.get('message')
    if not message:
        logger.debug("Telegram update without message, skipping")
        return

    chat = message.get('chat', {})
    if chat.get('type') != 'private':
        chat_id = chat.get('id')
        if chat_id:
            telegram_client.send_message(chat_id, MSG_NOT_PRIVATE)
        return

    from_user = message.get('from', {})
    tg_user_id = from_user.get('id')
    chat_id = chat.get('id')

    if not tg_user_id or not chat_id:
        return

    # Contact shared
    if message.get('contact'):
        _handle_contact(tg_user_id, chat_id, message['contact'])
        return

    text = message.get('text', '').strip()

    # Commands
    if text.startswith('/'):
        command = text.split()[0].split('@')[0].lower()  # handle /cmd@botname
        _handle_command(command, tg_user_id, chat_id)
        return

    # Text message
    if text:
        _handle_text(tg_user_id, chat_id, text, message.get('message_id'))
        return

    # Unsupported content (photo, voice, sticker, etc.)
    telegram_client.send_message(chat_id, MSG_UNSUPPORTED)


def _handle_command(command: str, tg_user_id: int, chat_id: int) -> None:
    """Route bot commands."""
    if command == '/start':
        _cmd_start(tg_user_id, chat_id)
    elif command == '/help':
        _cmd_help(chat_id)
    elif command == '/whoami':
        _cmd_whoami(tg_user_id, chat_id)
    elif command == '/reset':
        _cmd_reset(tg_user_id, chat_id)
    else:
        telegram_client.send_message(chat_id, f"Comando sconosciuto. Usa /help per la lista comandi.")


def _cmd_start(tg_user_id: int, chat_id: int) -> None:
    """Handle /start — show onboarding or greet if already bound."""
    binding = binding_service.get_active_binding(tg_user_id)
    if binding:
        name = binding.user.get_full_name()
        telegram_client.remove_keyboard(chat_id, MSG_ALREADY_BOUND.format(name=name))
    else:
        telegram_client.send_contact_request_keyboard(chat_id, MSG_ONBOARDING)


def _cmd_help(chat_id: int) -> None:
    telegram_client.send_message(chat_id, MSG_HELP)


def _cmd_whoami(tg_user_id: int, chat_id: int) -> None:
    """Show the user's identity in the internal system."""
    binding = binding_service.get_active_binding(tg_user_id)
    if not binding:
        telegram_client.send_contact_request_keyboard(chat_id, MSG_ONBOARDING)
        return

    user = binding.user
    roles = list(
        user.role_assignments.filter(is_active=True).values_list('role', flat=True)
    )
    info = (
        f"*Identita collegata:*\n"
        f"Nome: {user.get_full_name()}\n"
        f"Email: {user.email}\n"
        f"Ruoli: {', '.join(roles) if roles else 'Nessun ruolo assegnato'}\n"
        f"Collegato dal: {binding.first_bound_at.strftime('%d/%m/%Y %H:%M') if binding.first_bound_at else '?'}"
    )
    telegram_client.send_message(chat_id, info)


def _cmd_reset(tg_user_id: int, chat_id: int) -> None:
    """Revoke binding and clear conversation link."""
    binding = binding_service.get_active_binding(tg_user_id)
    if binding:
        message_service.reset_conversation(binding)
        binding_service.revoke_binding(tg_user_id)
        telegram_client.send_message(chat_id, MSG_RESET_OK)
    else:
        telegram_client.send_message(chat_id, MSG_RESET_NO_BINDING)


def _handle_contact(tg_user_id: int, chat_id: int, contact: dict) -> None:
    """
    Handle shared contact for identity binding.
    Only accepts contacts where the sharing user is the contact owner.
    """
    contact_user_id = contact.get('user_id')
    if contact_user_id != tg_user_id:
        # Someone shared another person's contact — reject
        telegram_client.send_message(
            chat_id, "Devi condividere il *tuo* numero di telefono, non quello di qualcun altro."
        )
        return

    phone_raw = contact.get('phone_number', '')
    if not phone_raw:
        telegram_client.send_message(chat_id, "Non ho ricevuto un numero di telefono valido.")
        return

    phone = binding_service.normalize_phone_number(phone_raw)
    user = binding_service.find_user_by_phone(phone)

    if not user:
        logger.info(
            "Telegram binding denied: tg_user=%s phone=%s — no matching user",
            tg_user_id, phone,
        )
        telegram_client.remove_keyboard(chat_id, MSG_NOT_RECOGNIZED)
        return

    # Create binding
    binding = binding_service.create_binding(tg_user_id, chat_id, phone, user)
    name = user.get_full_name()
    telegram_client.remove_keyboard(chat_id, MSG_RECOGNIZED.format(name=name))

    logger.info(
        "Telegram binding successful: tg_user=%s → user=%s (%s)",
        tg_user_id, user.email, name,
    )


def _handle_text(tg_user_id: int, chat_id: int, text: str, message_id: int | None) -> None:
    """Forward text message to the AI backend."""
    binding = binding_service.get_active_binding(tg_user_id)

    if not binding:
        # Not bound — trigger onboarding
        telegram_client.send_contact_request_keyboard(chat_id, MSG_ONBOARDING)
        return

    # Update last seen
    binding_service.touch_binding(binding)

    # Forward to AI backend
    try:
        reply = message_service.forward_message_to_backend(binding, text, message_id)
        # Telegram has a 4096 char limit per message
        if len(reply) > 4096:
            for i in range(0, len(reply), 4096):
                telegram_client.send_message(chat_id, reply[i:i + 4096])
        else:
            telegram_client.send_message(chat_id, reply)
    except Exception as e:
        logger.error(
            "Failed to forward message to backend: tg_user=%s error=%s",
            tg_user_id, e,
            exc_info=True,
        )
        telegram_client.send_message(chat_id, MSG_BACKEND_ERROR)
