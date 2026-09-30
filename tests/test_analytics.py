from decimal import Decimal
import unittest

import pandas as pd

from analytics import DataError, assess, money, prepare, simulate, wilson
from scenarios import SCENARIOS, load_scenario


class CalculationsTest(unittest.TestCase):
    def test_currency_formats(self):
        for value in ['1234.56', 'R$ 1.234,56', '1234,56']:
            self.assertEqual(money(value), Decimal('1234.56'))
        for value in ['', 'abc', 'NaN', 'inf', '-1', '1.234', '12,345', '1,234.56']:
            with self.subTest(value=value), self.assertRaises(DataError):
                money(value)

    def test_scenarios_have_expected_financial_results(self):
        expected = [(6000, 9500), (6000, 3000), (24, 29)]
        for name, amounts in zip(SCENARIOS, expected):
            rows = prepare(load_scenario(name)[0])
            self.assertEqual(tuple(r['liquido'] for r in rows), amounts)
        rows = prepare(load_scenario('Mais vendas, menos margem')[0])
        self.assertEqual(rows[1]['margem'], .02)
        self.assertEqual(rows[1]['roi'], .25)

    def test_zero_cashback_has_undefined_roi(self):
        frame = load_scenario(next(iter(SCENARIOS)))[0]
        frame.loc[0, 'cashback'] = '0'
        self.assertIsNone(prepare(frame)[0]['roi'])

    def test_validation_and_no_summing(self):
        frame = load_scenario(next(iter(SCENARIOS)))[0]
        for column, value in [('comissao', ''), ('compradores', '10001'), ('usuarios', '0'), ('vendas', '0')]:
            bad = frame.copy()
            bad.loc[0, column] = value
            with self.subTest(column=column), self.assertRaises(DataError):
                prepare(bad)
        with self.assertRaises(DataError):
            prepare(pd.concat([frame, frame]))
        with self.assertRaises(DataError):
            prepare(frame.rename(columns={'comissao': 'receita'}))
        frame['id'] = ['999', '123']
        frame['taxa'] = ['0.2', '0.3']
        self.assertNotIn('id', prepare(frame)[0])
        self.assertNotIn('taxa', prepare(frame)[0])

    def test_uncertainty_does_not_force_a_winner(self):
        for name in SCENARIOS:
            outcome = assess(prepare(load_scenario(name)[0]))
            self.assertIn('Ainda não', outcome['status'])
        outcome = assess(prepare(load_scenario('Teste inconclusivo')[0]))
        self.assertIsNone(outcome['difference'])
        self.assertTrue(any('Amostra insuficiente' in n for n in outcome['notes']))
        low, high = wilson(50, 100)
        self.assertAlmostEqual(low, .40383153)
        self.assertAlmostEqual(high, .59616847)
        frame = load_scenario(next(iter(SCENARIOS)))[0]
        frame.loc[1, 'compradores'] = '1000'
        interval = assess(prepare(frame))['difference']
        self.assertLess(interval[0], 0)
        self.assertGreater(interval[1], 0)

    def test_missing_sample_data(self):
        frame = load_scenario(next(iter(SCENARIOS)))[0].drop(columns=['usuarios'])
        self.assertTrue(any('Faltam usuarios' in n for n in assess(prepare(frame))['notes']))

    def test_simulation_uses_constant_sales(self):
        self.assertEqual(simulate(100000, 10, 4), (10000, 4000, 6000))
        self.assertEqual(simulate(100000, 10, 12), (10000, 12000, -2000))
        self.assertEqual(simulate(0, 10, 4), (0, 0, 0))
        with self.assertRaises(DataError):
            simulate(100, 101, 4)
