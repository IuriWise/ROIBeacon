import unittest
from unittest.mock import MagicMock, patch

from integrations import explain, save_sheet


class IntegrationTests(unittest.TestCase):
    def test_sheet_uses_raw_and_only_spreadsheet_scope(self):
        with patch('integrations.Credentials') as credentials, patch('integrations.gspread') as spread:
            save_sheet('sheet-id', {'client_email': 'fake'}, '=FORMULA()', 'report')
            self.assertEqual(credentials.from_service_account_info.call_args.kwargs['scopes'], ['https://www.googleapis.com/auth/spreadsheets'])
            spread.authorize.return_value.open_by_key.assert_called_once_with('sheet-id')
            self.assertEqual(spread.authorize.return_value.open_by_key.return_value.sheet1.append_row.call_args.kwargs['value_input_option'], 'RAW')

    def test_ai_receives_calculated_data_not_credentials(self):
        response = MagicMock()
        response.choices[0].message.content = 'Explicação'
        with patch('integrations.Groq') as groq:
            groq.return_value.chat.completions.create.return_value = response
            self.assertEqual(explain('TEST_SECRET', [{'liquido': 6000}], {'status': 'Inconclusivo'}, 'Explique'), 'Explicação')
            call = groq.return_value.chat.completions.create.call_args.kwargs
            self.assertEqual(call['model'], 'openai/gpt-oss-120b')
            self.assertIn('6000', str(call['messages']))
            self.assertNotIn('TEST_SECRET', str(call['messages']))

    def test_safe_diagnostics_for_groq(self):
        import httpx
        from groq import AuthenticationError, RateLimitError, APIConnectionError
        from integrations import failure_message
        request = httpx.Request('POST', 'https://api.groq.com')
        for cls, status, expected in [(AuthenticationError, 401, 'GROQ_API_KEY'), (RateLimitError, 429, 'Limite de uso')]:
            error = cls('SECRET_SENTINEL', response=httpx.Response(status, request=request), body={'secret': 'SECRET_SENTINEL'})
            message = failure_message('groq', error)
            self.assertIn(expected, message)
            self.assertNotIn('SECRET_SENTINEL', message)
        self.assertIn('conectar', failure_message('groq', APIConnectionError(request=request)))

    def test_safe_diagnostics_for_google(self):
        from integrations import failure_message
        from google.auth.exceptions import RefreshError
        from gspread.exceptions import SpreadsheetNotFound
        for error, expected in [(PermissionError('SECRET_SENTINEL'), 'permissão de editor'), (RefreshError('SECRET_SENTINEL'), 'gcp_service_account'), (SpreadsheetNotFound('SECRET_SENTINEL'), 'GOOGLE_SHEETS_ID')]:
            message = failure_message('sheets', error)
            self.assertIn(expected, message)
            self.assertNotIn('SECRET_SENTINEL', message)
