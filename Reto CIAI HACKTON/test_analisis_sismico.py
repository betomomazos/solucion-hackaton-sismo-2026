"""Pruebas del modelo, la calidad del rack, el contraste y el respaldo."""
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd
import requests
from pypdf import PdfReader

import analisis_sismico as engine
from app import app

NOW = datetime(2026, 10, 13, 12, tzinfo=timezone.utc)


def event(date='2026-10-10T12:00:00Z', **kwargs):
    return dict(fecha=date, magnitud=4., latitud=6.8, longitud=-73.1,
                ubicacion='Los Santos', **kwargs)


class AnalysisTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        cache = patch.object(engine, 'CACHE', Path(self.temp.name) / 'cache.json')
        cache.start()
        self.addCleanup(cache.stop)
        self.client = app.test_client()

    def test_normalization_quality(self):
        valid = event()
        bad = dict(event(), magnitud='bad')
        outside = dict(event(), longitud=-81)
        future = event('2035-01-01')
        df, q = engine.normalize(pd.DataFrame([valid, valid, bad, outside, future]), 'test', NOW)
        self.assertEqual(len(df), 1)
        self.assertEqual(q, dict(filas=5, invalidas=2, fuera_de_zona=1, duplicadas=1, utilizadas=1))

    def test_sgc_time_is_colombia(self):
        raw = pd.DataFrame([dict(Fecha_Hora_Completa='11/2026/10 23:54:00',
                                Magnitud=3, Latitud=6.8, Longitud=-73.1)])
        df, _ = engine.normalize(raw, 'SGC', NOW)
        self.assertEqual(df.fecha.iloc[0].isoformat(), '2026-10-12T04:54:00+00:00')

    def test_invalid_schema(self):
        with self.assertRaises(ValueError):
            engine.normalize(pd.DataFrame([dict(foo=1)]), 'test', NOW)

    def test_network_failure_uses_local(self):
        with patch.object(engine.requests, 'get', side_effect=requests.ConnectionError):
            report = engine.build_report(online=True)
        self.assertEqual(report['modo'], 'solo_local')
        self.assertGreater(report['resumen']['eventos'], 0)
        self.assertFalse(report['contraste']['disponible'])
        json.dumps(report, allow_nan=False)

    def test_cache_survives_failure(self):
        df, _ = engine.normalize(pd.DataFrame([event()]), 'USGS', NOW)
        meta = dict(inicio='2026-09-01T00:00:00Z', fin=NOW.isoformat(),
                    consultado=NOW.isoformat(), url=engine.USGS)
        engine.save_cache(df, meta)
        with patch.object(engine.requests, 'get', side_effect=requests.Timeout):
            cached, status, warnings = engine.get_web(NOW, True)
        self.assertEqual(status['estado'], 'cache')
        self.assertEqual(len(cached), 1)
        self.assertTrue(warnings)

    def test_corrupt_cache_falls_back(self):
        engine.CACHE.write_text('{broken', encoding='utf-8')
        df, meta, _ = engine.get_web(NOW, False)
        self.assertIsNone(df)
        self.assertEqual(meta['estado'], 'solo_local')

    def test_explicit_offline_never_calls_network(self):
        with patch.object(engine.requests, 'get') as get:
            engine.build_report(online=False)
            get.assert_not_called()

    def test_bad_cache_dates_fall_back(self):
        engine.CACHE.write_text(json.dumps(dict(meta=dict(inicio='invalid', fin=NOW.isoformat(),
            consultado=NOW.isoformat(), url=engine.USGS), eventos=[])), encoding='utf-8')
        df, meta, _ = engine.get_web(NOW, False)
        self.assertIsNone(df)
        self.assertEqual(meta['estado'], 'solo_local')

    def test_successful_usgs_is_cached(self):
        payload = dict(type='FeatureCollection', features=[dict(id='us-test',
            properties=dict(time=1791633600000, mag=4, place='Test'),
            geometry=dict(coordinates=[-73.1, 6.8, 120]))])
        with patch.object(engine.requests, 'get') as get:
            get.return_value.json.return_value = payload
            get.return_value.url = engine.USGS
            df, meta, _ = engine.get_web(NOW, True)
        self.assertEqual(meta['estado'], 'en_linea')
        self.assertEqual(len(df), 1)
        self.assertTrue(engine.CACHE.exists())

    def test_comparison_one_to_one(self):
        a, _ = engine.normalize(pd.DataFrame([event('2026-10-09'), event('2026-10-10'),
                                             event('2026-10-10T00:00:30Z'), event('2026-10-11')]), 'local', NOW)
        b, _ = engine.normalize(pd.DataFrame([event('2026-10-10T00:00:10Z')]), 'web', NOW)
        meta = dict(inicio='2026-10-09T00:00:00Z', fin='2026-10-11T00:00:00Z')
        result = engine.comparison(a, b, meta, 3.5)
        self.assertEqual(result['coincidencias_aproximadas'], 1)
        self.assertEqual(result['solo_local'], 3)

    def test_no_temporal_overlap(self):
        a, _ = engine.normalize(pd.DataFrame([event('2010-01-01')]), 'local', NOW)
        b, _ = engine.normalize(pd.DataFrame([event()]), 'web', NOW)
        self.assertFalse(engine.comparison(a, b, dict(inicio='2026-09-01', fin=NOW.isoformat()), 3)['disponible'])

    def test_forecast_deterministic_and_temporal(self):
        df, _ = engine.normalize(engine.read_csv(engine.LOCAL.read_bytes()), 'local', NOW)
        a = engine.forecast(df, now=NOW)
        b = engine.forecast(df, now=NOW)
        self.assertEqual(a, b)
        self.assertEqual(len(a['dias']), 7)
        self.assertTrue(all(0 <= d['probabilidad_evento'] <= 1 for d in a['dias']))
        self.assertLess(pd.Timestamp(a['entrenamiento']['fin']), pd.Timestamp(NOW).floor('D'))
        self.assertNotIn('magnitud_esperada', a['dias'][0])
        self.assertTrue(a['validacion']['evaluado'])
        if a['modelo'] == 'Random Forest':
            self.assertTrue(a['validacion']['mejora_sobre_base'])

    def test_insufficient_history(self):
        df, _ = engine.normalize(pd.DataFrame([event()]), 'test', NOW)
        self.assertFalse(engine.forecast(df, now=NOW)['disponible'])

    def test_api_validates_inputs(self):
        for query in ('dias=0', 'dias=31', 'dias=abc', 'magnitud_minima=nan', 'magnitud_minima=11'):
            self.assertEqual(self.client.get('/api/analisis?web=false&'+query).status_code, 400)
        response = self.client.post('/api/analisis', data=dict(web='false',
            archivo=(BytesIO(b'foo,bar\n1,2'), 'wrong.csv')))
        self.assertEqual(response.status_code, 400)

    def test_uploaded_csv_report(self):
        raw = b'fecha,magnitud,latitud,longitud\n2026-10-10T12:00:00Z,4,6.8,-73.1\n'
        response = self.client.post('/api/analisis', data=dict(web='false',
            archivo=(BytesIO(raw), 'events.csv')))
        self.assertEqual(response.status_code, 200)
        report = response.get_json()
        self.assertEqual(report['resumen']['eventos'], 1)
        self.assertEqual(len(report['fuentes']), 2)
        self.assertFalse(report['prediccion']['disponible'])

    def test_size_limit(self):
        response = self.client.post('/api/analisis', data=b'x'*(5*1024*1024+1),
                                    content_type='multipart/form-data')
        self.assertEqual(response.status_code, 413)

    def test_existing_endpoints(self):
        for route in ('/', '/api/dashboard', '/api/zonas', '/api/priorizacion',
                      '/api/estadisticas', '/api/eventos', '/api/prediccion'):
            with self.subTest(route=route):
                self.assertEqual(self.client.get(route).status_code, 200)
        zones = self.client.get('/api/zonas').get_json()
        self.assertTrue(all(z['total_eventos'] >= z['eventos_criticos'] for z in zones))

    def test_expanding_validation_precedes_final_test(self):
        df, _ = engine.normalize(engine.read_csv(engine.LOCAL.read_bytes()), 'local', NOW)
        result = engine.forecast(df, now=NOW)
        v = result['validacion']
        self.assertEqual(len(v['candidatos']), 2)
        for candidate in v['candidatos'].values():
            self.assertEqual(len(candidate['ventanas']), 3)
            for fold in candidate['ventanas']:
                self.assertLess(pd.Timestamp(fold['fin_entrenamiento']), pd.Timestamp(fold['inicio_validacion']))
                self.assertLess(pd.Timestamp(fold['fin_validacion']), pd.Timestamp(v['inicio_prueba']))

    def test_territory_and_scenario_consistency(self):
        report = engine.build_report(online=False)
        t = report['analisis_territorial']
        self.assertEqual(t['zonas'][0]['ubicacion'], 'Los Santos')
        self.assertTrue(all(z['eventos'] >= t['zonas'][i+1]['eventos'] for i, z in enumerate(t['zonas'][:-1])))
        s = t['escenarios']
        self.assertAlmostEqual(sum(v['probabilidad'] for v in s['posibilidades']), 1., places=3)
        lo, hi = s['intervalo_probabilidad_al_menos_uno_95']
        self.assertTrue(0 <= lo <= hi <= 1)
        self.assertGreaterEqual(len(t['explicaciones']), 5)

    def test_short_history_has_no_zone_probability(self):
        df, _ = engine.normalize(pd.DataFrame([event()]), 'test', NOW)
        pred = engine.forecast(df, now=NOW)
        territory = engine.territorial_analysis(df, pred, 3.5, 7, NOW)
        self.assertIsNone(territory['zonas'][0]['probabilidad_base_horizonte'])
        self.assertIsNone(territory['escenarios'])

    def test_zero_events_interval_is_not_zero_certainty(self):
        lo, hi = engine.rate_interval(0, 100)
        self.assertEqual(lo, 0)
        self.assertGreater(hi, 0)

    def test_pdf_export_preserves_snapshot_without_network(self):
        raw = b'fecha,magnitud,latitud,longitud,ubicacion\n2026-10-10T12:00:00Z,4,6.8,-73.1,Zona de prueba\n'
        report = self.client.post('/api/analisis', data=dict(web='false',
            archivo=(BytesIO(raw), 'events.csv'))).get_json()
        with patch.object(engine.requests, 'get') as get:
            response = self.client.post('/api/informes/pdf', json={'token':report['export_token']})
            get.assert_not_called()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'application/pdf')
        self.assertTrue(response.data.startswith(b'%PDF-'))
        reader = PdfReader(BytesIO(response.data))
        text = '\n'.join(p.extract_text() for p in reader.pages)
        self.assertIn('Zona de prueba', text)
        self.assertIn('Historial insuficiente', text)
        self.assertIn('Resumen ejecutivo', text)
        self.assertIn('Limitaciones y referencias', text)

    def test_pdf_rejects_modified_missing_and_expired_tokens(self):
        from app import report_signer
        for payload in ({}, {'token':123}, {'token':'invalid'}):
            self.assertEqual(self.client.post('/api/informes/pdf', json=payload).status_code, 400)
        with patch('itsdangerous.timed.TimestampSigner.get_timestamp', return_value=1):
            expired = report_signer().dumps({'fake':'report'})
        self.assertEqual(self.client.post('/api/informes/pdf', json={'token':expired}).status_code, 400)

    def test_pdf_long_report_and_untrusted_location(self):
        from informe_pdf import render_report
        report = engine.build_report(online=False, days=30)
        report['analisis_territorial']['zonas'][0]['ubicacion'] = '<b>' + 'NombreLargo'*18 + '</b>'
        pdf = render_report(report)
        reader = PdfReader(BytesIO(pdf))
        text = '\n'.join(p.extract_text() for p in reader.pages)
        self.assertIn('<b>', text)
        self.assertGreater(len(reader.pages), 3)
        self.assertIn('Limitaciones y referencias', text)


if __name__ == '__main__':
    unittest.main()
