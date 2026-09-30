from pathlib import Path
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest
from scenarios import SCENARIOS

APP = str(Path(__file__).resolve().parents[1] / 'app.py')


class AppTests(unittest.TestCase):
    def demo(self, name=None):
        app = AppTest.from_file(APP, default_timeout=15).run()
        self.assertFalse(app.exception)
        if name:
            app.selectbox(key='scenario').select(name).run()
        app.button(key='demo').click().run()
        self.assertFalse(app.exception)
        return app

    def test_three_offline_scenarios(self):
        with patch('integrations.explain', side_effect=AssertionError('network forbidden')), patch('integrations.save_sheet', side_effect=AssertionError('network forbidden')):
            for name in SCENARIOS:
                app = self.demo(name)
                self.assertEqual(len(app.metric), 4)
                self.assertTrue(any('pré-gerada' in el.value for el in app.info))
                self.assertTrue(any('Ainda não' in el.value for el in app.warning))
                self.assertTrue(app.get('download_button'))

    def test_simulator_and_report_survive_rerun(self):
        app = self.demo()
        before = app.session_state['analysis']['report']
        app.slider[1].set_value(12.0).run()
        self.assertEqual(app.metric[-1].value, 'R$ -2.000,00')
        self.assertEqual(app.session_state['analysis']['report'], before)

    def test_integrations_fail_without_losing_analysis(self):
        with patch.dict('os.environ', {'GROQ_API_KEY':'test', 'GOOGLE_SHEETS_ID':'test-sheet'}), patch('integrations.explain', side_effect=RuntimeError('SECRET_SENTINEL')), patch('integrations.save_sheet', side_effect=RuntimeError('SECRET_SENTINEL')):
            app = self.demo()
            app.secrets['gcp_service_account'] = {'client_email': 'fake'}
            report = app.session_state['analysis']['report']
            app.button(key='explain').click().run()
            self.assertFalse(app.exception)
            self.assertTrue(any('IA está indisponível' in e.value for e in app.warning))
            app.button(key='save').click().run()
            self.assertFalse(app.exception)
            self.assertTrue(any('Sua análise foi preservada' in e.value for e in app.warning))
            self.assertEqual(app.session_state['analysis']['report'], report)
            self.assertNotIn('SECRET_SENTINEL', str([e.value for e in app.warning]))
            self.assertEqual(len(app.metric), 4)

    def test_no_credentials_required_and_optional_action_is_clear(self):
        with patch('dotenv.load_dotenv'), patch.dict('os.environ', {'GROQ_API_KEY': '', 'GOOGLE_SHEETS_ID': ''}):
            app = AppTest.from_file(APP, default_timeout=15)
            app.secrets = {}
            app.run()
            app.button(key='demo').click().run()
            self.assertFalse(app.exception)
            app.button(key='explain').click().run()
            self.assertTrue(any('Configure GROQ_API_KEY' in e.value for e in app.info))
            self.assertEqual(len(app.metric), 4)

    def test_negative_delta_has_negative_sign(self):
        app = self.demo('Mais vendas, menos margem')
        app.selectbox(key='variant_Mais vendas, menos margem').select(1).run()
        self.assertTrue(app.metric[2].delta.startswith('-'))
        self.assertEqual(app.metric[2].value, 'R$ 3.000,00')

    def test_invalid_api_key_explains_hosting_fix_and_keeps_report(self):
        import httpx
        from groq import AuthenticationError
        error = AuthenticationError('SECRET_SENTINEL', response=httpx.Response(401, request=httpx.Request('POST', 'https://api.groq.com')), body=None)
        with patch.dict('os.environ', {'GROQ_API_KEY': 'fake'}), patch('integrations.explain', side_effect=error):
            app = self.demo()
            previous = app.session_state['analysis']['report']
            app.button(key='explain').click().run()
            self.assertFalse(app.exception)
            self.assertTrue(any('Secrets da hospedagem' in e.value for e in app.warning))
            self.assertNotIn('SECRET_SENTINEL', str([e.value for e in app.warning]))
            self.assertEqual(app.session_state['analysis']['report'], previous)
