"""
Tests for the Telegram Bot adapter.
"""
import json
from unittest.mock import patch, MagicMock

from django.test import TestCase, RequestFactory, override_settings
from django.test.client import Client as DjangoTestClient

from core.models import User
from ai_assistant.models import ChatSession
from .models import TelegramIdentityBinding, TelegramUpdateLog, ExternalChannelConversationLink
from . import binding_service
from . import handlers


def _make_update(update_id, tg_user_id=111, chat_id=111, text=None, contact=None):
    """Helper to build a Telegram update dict."""
    message = {
        'message_id': update_id,
        'from': {'id': tg_user_id, 'is_bot': False, 'first_name': 'Test'},
        'chat': {'id': chat_id, 'type': 'private'},
        'date': 1700000000,
    }
    if text:
        message['text'] = text
    if contact:
        message['contact'] = contact
    return {'update_id': update_id, 'message': message}


@override_settings(TELEGRAM_BOT_TOKEN='test-token', TELEGRAM_WEBHOOK_SECRET='')
class PhoneNormalizationTest(TestCase):
    def test_with_plus_prefix(self):
        self.assertEqual(binding_service.normalize_phone_number('+393471234567'), '+393471234567')

    def test_without_plus_prefix(self):
        self.assertEqual(binding_service.normalize_phone_number('393471234567'), '+393471234567')

    def test_bare_italian_number(self):
        self.assertEqual(binding_service.normalize_phone_number('3471234567'), '+393471234567')

    def test_with_spaces(self):
        self.assertEqual(binding_service.normalize_phone_number('+39 347 123 4567'), '+393471234567')

    def test_extract_national_number_with_country_code(self):
        self.assertEqual(binding_service._extract_national_number('393471234567'), '3471234567')

    def test_extract_national_number_without_country_code(self):
        self.assertEqual(binding_service._extract_national_number('3471234567'), '3471234567')

    def test_extract_national_number_non_italian(self):
        """Non-Italian number (e.g. +44) should be left as-is."""
        self.assertEqual(binding_service._extract_national_number('447911123456'), '447911123456')

    def test_extract_digits(self):
        self.assertEqual(binding_service._extract_digits('+39 347-123.4567'), '393471234567')
        self.assertEqual(binding_service._extract_digits('347/1234567'), '3471234567')


@override_settings(TELEGRAM_BOT_TOKEN='test-token', TELEGRAM_WEBHOOK_SECRET='')
class BindingServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            phone_number='+393471234567',
        )
        self.user.first_name = 'Mario'
        self.user.last_name = 'Rossi'
        self.user.save()

    def test_find_user_exact_match(self):
        found = binding_service.find_user_by_phone('+393471234567')
        self.assertEqual(found, self.user)

    def test_find_user_no_match(self):
        found = binding_service.find_user_by_phone('+393479999999')
        self.assertIsNone(found)

    def test_find_user_national_match(self):
        """Match by national number suffix."""
        found = binding_service.find_user_by_phone('+393471234567')
        self.assertEqual(found, self.user)

    def test_find_user_db_has_spaces(self):
        """DB stores '347 123 4567', Telegram sends '+393471234567'."""
        self.user.phone_number = '347 123 4567'
        self.user.save()
        found = binding_service.find_user_by_phone('+393471234567')
        self.assertEqual(found, self.user)

    def test_find_user_db_has_dashes(self):
        """DB stores '347-123-4567'."""
        self.user.phone_number = '347-123-4567'
        self.user.save()
        found = binding_service.find_user_by_phone('+393471234567')
        self.assertEqual(found, self.user)

    def test_find_user_db_has_spaces_with_prefix(self):
        """DB stores '+39 347 123 4567'."""
        self.user.phone_number = '+39 347 123 4567'
        self.user.save()
        found = binding_service.find_user_by_phone('+393471234567')
        self.assertEqual(found, self.user)

    def test_find_user_db_bare_no_country_code(self):
        """DB stores '3471234567' (no country code)."""
        self.user.phone_number = '3471234567'
        self.user.save()
        found = binding_service.find_user_by_phone('+393471234567')
        self.assertEqual(found, self.user)

    def test_find_user_db_has_country_no_plus(self):
        """DB stores '393471234567' (country code without +)."""
        self.user.phone_number = '393471234567'
        self.user.save()
        found = binding_service.find_user_by_phone('+393471234567')
        self.assertEqual(found, self.user)

    def test_find_user_db_has_slash(self):
        """DB stores '347/1234567'."""
        self.user.phone_number = '347/1234567'
        self.user.save()
        found = binding_service.find_user_by_phone('+393471234567')
        self.assertEqual(found, self.user)

    def test_find_user_db_has_dots(self):
        """DB stores '347.123.4567'."""
        self.user.phone_number = '347.123.4567'
        self.user.save()
        found = binding_service.find_user_by_phone('+393471234567')
        self.assertEqual(found, self.user)

    def test_create_and_get_binding(self):
        binding = binding_service.create_binding(111, 222, '+393471234567', self.user)
        self.assertEqual(binding.binding_status, 'ACTIVE')

        retrieved = binding_service.get_active_binding(111)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.user, self.user)

    def test_revoke_binding(self):
        binding_service.create_binding(111, 222, '+393471234567', self.user)
        revoked = binding_service.revoke_binding(111)
        self.assertTrue(revoked)

        retrieved = binding_service.get_active_binding(111)
        self.assertIsNone(retrieved)

    def test_create_binding_revokes_previous(self):
        binding_service.create_binding(111, 222, '+393471234567', self.user)
        binding_service.create_binding(111, 333, '+393471234567', self.user)

        # Only one ACTIVE binding
        active_count = TelegramIdentityBinding.objects.filter(
            telegram_user_id=111,
            binding_status='ACTIVE',
        ).count()
        self.assertEqual(active_count, 1)

    def test_unique_user_binding(self):
        """Two different TG users can't bind to the same internal user."""
        binding_service.create_binding(111, 222, '+393471234567', self.user)
        binding_service.create_binding(999, 888, '+393471234567', self.user)

        # First binding should be revoked
        active = TelegramIdentityBinding.objects.filter(
            binding_status='ACTIVE',
        )
        self.assertEqual(active.count(), 1)
        self.assertEqual(active.first().telegram_user_id, 999)


@override_settings(TELEGRAM_BOT_TOKEN='test-token', TELEGRAM_WEBHOOK_SECRET='')
class HandlersTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            phone_number='+393471234567',
        )
        self.user.first_name = 'Mario'
        self.user.last_name = 'Rossi'
        self.user.save()

    @patch('telegram_bot.telegram_client.send_contact_request_keyboard')
    def test_start_unbound_user(self, mock_send):
        update = _make_update(1, text='/start')
        handlers.handle_update(update)
        mock_send.assert_called_once()
        args = mock_send.call_args
        self.assertIn('riconoscerti', args[0][1])

    @patch('telegram_bot.telegram_client.remove_keyboard')
    def test_start_bound_user(self, mock_send):
        binding_service.create_binding(111, 111, '+393471234567', self.user)
        update = _make_update(2, text='/start')
        handlers.handle_update(update)
        mock_send.assert_called_once()
        self.assertIn('collegato', mock_send.call_args[0][1])

    @patch('telegram_bot.telegram_client.send_message')
    def test_help_command(self, mock_send):
        update = _make_update(3, text='/help')
        handlers.handle_update(update)
        mock_send.assert_called_once()
        self.assertIn('Comandi disponibili', mock_send.call_args[0][1])

    @patch('telegram_bot.telegram_client.remove_keyboard')
    def test_contact_recognized(self, mock_send):
        contact = {
            'phone_number': '+393471234567',
            'first_name': 'Mario',
            'user_id': 111,
        }
        update = _make_update(4, contact=contact)
        handlers.handle_update(update)

        # Should create binding
        binding = binding_service.get_active_binding(111)
        self.assertIsNotNone(binding)
        self.assertEqual(binding.user, self.user)

        # Should send recognized message
        mock_send.assert_called_once()
        self.assertIn('riconosciuto', mock_send.call_args[0][1])

    @patch('telegram_bot.telegram_client.remove_keyboard')
    def test_contact_not_recognized(self, mock_send):
        contact = {
            'phone_number': '+393479999999',
            'first_name': 'Unknown',
            'user_id': 111,
        }
        update = _make_update(5, contact=contact)
        handlers.handle_update(update)

        binding = binding_service.get_active_binding(111)
        self.assertIsNone(binding)
        mock_send.assert_called_once()
        self.assertIn('non risulta abilitato', mock_send.call_args[0][1])

    @patch('telegram_bot.telegram_client.send_message')
    def test_contact_from_other_user_rejected(self, mock_send):
        """Contact shared by someone else should be rejected."""
        contact = {
            'phone_number': '+393471234567',
            'first_name': 'Mario',
            'user_id': 999,  # Different from tg_user_id=111
        }
        update = _make_update(6, contact=contact)
        handlers.handle_update(update)

        binding = binding_service.get_active_binding(111)
        self.assertIsNone(binding)
        self.assertIn('tuo', mock_send.call_args[0][1])

    @patch('telegram_bot.telegram_client.send_contact_request_keyboard')
    def test_text_without_binding_triggers_onboarding(self, mock_send):
        update = _make_update(7, text='Ciao')
        handlers.handle_update(update)
        mock_send.assert_called_once()

    @patch('telegram_bot.message_service.forward_message_to_backend', return_value='AI reply')
    @patch('telegram_bot.telegram_client.send_message')
    def test_text_with_binding_forwards_to_backend(self, mock_send, mock_forward):
        binding_service.create_binding(111, 111, '+393471234567', self.user)
        update = _make_update(8, text='Inserisci dati sezione 42')
        handlers.handle_update(update)

        mock_forward.assert_called_once()
        mock_send.assert_called_once_with(111, 'AI reply')

    @patch('telegram_bot.telegram_client.send_message')
    def test_unsupported_content(self, mock_send):
        update = _make_update(9)
        update['message']['photo'] = [{'file_id': 'abc'}]
        handlers.handle_update(update)
        mock_send.assert_called_once()
        self.assertIn('solo messaggi testuali', mock_send.call_args[0][1])

    @patch('telegram_bot.telegram_client.send_message')
    def test_reset_with_binding(self, mock_send):
        binding_service.create_binding(111, 111, '+393471234567', self.user)
        update = _make_update(10, text='/reset')
        handlers.handle_update(update)

        binding = binding_service.get_active_binding(111)
        self.assertIsNone(binding)
        self.assertIn('scollegato', mock_send.call_args[0][1])

    @patch('telegram_bot.telegram_client.send_message')
    def test_reset_without_binding(self, mock_send):
        update = _make_update(11, text='/reset')
        handlers.handle_update(update)
        self.assertIn('Non hai', mock_send.call_args[0][1])


@override_settings(TELEGRAM_BOT_TOKEN='test-token', TELEGRAM_WEBHOOK_SECRET='')
class WebhookViewTest(TestCase):
    def setUp(self):
        self.client = DjangoTestClient()

    @patch('telegram_bot.views.handle_update')
    def test_webhook_processes_valid_update(self, mock_handle):
        update = _make_update(100, text='/start')
        resp = self.client.post(
            '/api/telegram/webhook/',
            data=json.dumps(update),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        mock_handle.assert_called_once()

        # Check idempotency log
        self.assertTrue(TelegramUpdateLog.objects.filter(update_id=100).exists())

    @patch('telegram_bot.views.handle_update')
    def test_webhook_idempotent_duplicate(self, mock_handle):
        update = _make_update(200, text='test')
        # First call
        self.client.post(
            '/api/telegram/webhook/',
            data=json.dumps(update),
            content_type='application/json',
        )
        # Second call (duplicate)
        resp = self.client.post(
            '/api/telegram/webhook/',
            data=json.dumps(update),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        # handle_update called only once
        self.assertEqual(mock_handle.call_count, 1)

    def test_webhook_invalid_json(self):
        resp = self.client.post(
            '/api/telegram/webhook/',
            data='not json',
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)

    def test_webhook_missing_update_id(self):
        resp = self.client.post(
            '/api/telegram/webhook/',
            data=json.dumps({'message': {}}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)

    @override_settings(TELEGRAM_WEBHOOK_SECRET='my-secret')
    def test_webhook_secret_validation(self):
        update = _make_update(300, text='test')
        # Without secret
        resp = self.client.post(
            '/api/telegram/webhook/',
            data=json.dumps(update),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 403)

        # With correct secret
        resp = self.client.post(
            '/api/telegram/webhook/',
            data=json.dumps(update),
            content_type='application/json',
            HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN='my-secret',
        )
        self.assertEqual(resp.status_code, 200)


@override_settings(TELEGRAM_BOT_TOKEN='test-token', TELEGRAM_WEBHOOK_SECRET='')
class MessageServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            phone_number='+393471234567',
        )
        self.binding = binding_service.create_binding(111, 111, '+393471234567', self.user)

    def test_get_or_create_conversation(self):
        from . import message_service

        session = message_service.get_or_create_conversation(self.binding)
        self.assertIsNotNone(session)
        self.assertEqual(session.user_email, self.user.email)
        self.assertEqual(session.context, 'TELEGRAM')

        # Second call should return same session
        session2 = message_service.get_or_create_conversation(self.binding)
        self.assertEqual(session.id, session2.id)

    def test_reset_conversation(self):
        from . import message_service

        session = message_service.get_or_create_conversation(self.binding)
        message_service.reset_conversation(self.binding)

        # Should create a new session now
        session2 = message_service.get_or_create_conversation(self.binding)
        self.assertNotEqual(session.id, session2.id)

    @patch('telegram_bot.message_service.generate_ai_response')
    def test_forward_message(self, mock_generate):
        from . import message_service

        mock_generate.return_value = {
            'answer': 'Test AI reply',
            'sources': [],
            'retrieved_docs': 0,
            'function_result': None,
            'user_sections_list': [],
        }

        reply = message_service.forward_message_to_backend(self.binding, 'test message', 42)
        self.assertEqual(reply, 'Test AI reply')

        # Check messages were saved
        session = message_service.get_or_create_conversation(self.binding)
        messages = list(session.messages.order_by('created_at'))
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0].role, 'user')
        self.assertEqual(messages[0].content, 'test message')
        self.assertEqual(messages[1].role, 'assistant')
        self.assertEqual(messages[1].content, 'Test AI reply')


@override_settings(TELEGRAM_BOT_TOKEN='test-token', TELEGRAM_WEBHOOK_SECRET='')
class GroupChatRejectionTest(TestCase):
    """Test that group chats are rejected."""

    @patch('telegram_bot.telegram_client.send_message')
    def test_group_chat_rejected(self, mock_send):
        update = {
            'update_id': 500,
            'message': {
                'message_id': 500,
                'from': {'id': 111, 'is_bot': False, 'first_name': 'Test'},
                'chat': {'id': -12345, 'type': 'group'},
                'date': 1700000000,
                'text': '/start',
            },
        }
        handlers.handle_update(update)
        mock_send.assert_called_once()
        self.assertIn('privata', mock_send.call_args[0][1])
