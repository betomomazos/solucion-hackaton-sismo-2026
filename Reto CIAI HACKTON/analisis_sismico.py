"""Análisis reproducible local, contraste USGS y pronóstico experimental.

No predice fecha, epicentro ni magnitud de un sismo individual.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from io import BytesIO
import json
import math
import os
import tempfile

import numpy as np
import pandas as pd
import requests
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import brier_score_loss
from sklearn.model_selection import TimeSeriesSplit
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from scipy.stats import chi2, poisson

BASE = Path(__file__).resolve().parent
LOCAL = BASE / 'info_registros' / 'dataset_sismos_bucaramanga.csv'
CACHE = BASE / 'data' / 'usgs_cache.json'
USGS = 'https://earthquake.usgs.gov/fdsnws/event/1/query'
# Ventana de estudio explícita; no equivale al límite administrativo de Santander.
BOUNDS = dict(minlatitude=5.4, maxlatitude=8.4, minlongitude=-74.7, maxlongitude=-72.0)
LIMITACION = ('Estimación experimental de actividad registrada, no predicción de sismos '
              'individuales ni alerta temprana. El catálogo de reportes puede ser incompleto '
              'y los días sin registros no demuestran ausencia de sismos. No usar para ordenar evacuaciones.')


def now_utc():
    return datetime.now(timezone.utc)


def read_csv(raw):
    for encoding in ('utf-8-sig', 'latin-1'):
        try:
            return pd.read_csv(BytesIO(raw), encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError('No se pudo leer el CSV.')


def normalize(raw, source, now=None):
    """Acepta CSV original SGC o esquema fecha/magnitud/latitud/longitud.

    Fechas SGC DD/AAAA/MM: hora Colombia. Fechas ISO sin zona: UTC.
    No incorpora profundidades inferidas de los archivos derivados.
    """
    now = now or now_utc()
    df = raw.rename(columns={'Fecha_Hora_Completa': 'fecha', 'Magnitud': 'magnitud',
                             'Latitud': 'latitud', 'Longitud': 'longitud',
                             'Municipio_Epicentral': 'ubicacion', 'ID_Sismo': 'id'}).copy()
    required = {'fecha', 'magnitud', 'latitud', 'longitud'}
    if not required.issubset(df.columns):
        raise ValueError('CSV requiere fecha, magnitud, latitud y longitud (o columnas originales SGC).')
    if df.columns.duplicated().any():
        raise ValueError('El CSV contiene columnas duplicadas o nombres equivalentes.')
    total = len(df)
    sgc = 'Fecha_Hora_Completa' in raw.columns
    if sgc:
        dates = pd.to_datetime(df['fecha'], format='%d/%Y/%m %H:%M:%S', errors='coerce')
        df['fecha'] = dates.dt.tz_localize(timezone(timedelta(hours=-5))).dt.tz_convert('UTC')
    else:
        df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce', utc=True, format='mixed')
    for name in ('magnitud', 'latitud', 'longitud'):
        df[name] = pd.to_numeric(df[name], errors='coerce')
    valid = (df['fecha'].notna() & (df['fecha'] <= now) & df['magnitud'].between(-2, 10)
             & df['latitud'].between(-90, 90) & df['longitud'].between(-180, 180))
    invalid = int((~valid).sum())
    df = df[valid].copy()
    inside = (df.latitud.between(BOUNDS['minlatitude'], BOUNDS['maxlatitude'])
              & df.longitud.between(BOUNDS['minlongitude'], BOUNDS['maxlongitude']))
    outside = int((~inside).sum())
    df = df[inside].copy()
    if 'ubicacion' not in df:
        df['ubicacion'] = 'Zona de estudio'
    df['ubicacion'] = df.ubicacion.fillna('Sin ubicación').astype(str).str.slice(0, 180)
    if 'id' not in df:
        df['id'] = ''
    df['id'] = df['id'].fillna('').astype(str)
    before = len(df)
    df = df.drop_duplicates(['fecha', 'latitud', 'longitud', 'magnitud'])
    has_id = df['id'].ne('')
    df = pd.concat([df[~has_id], df[has_id].drop_duplicates('id')])
    df['fuente'] = source
    columns = ['id', 'fecha', 'magnitud', 'latitud', 'longitud', 'ubicacion', 'fuente']
    return df[columns].sort_values('fecha'), dict(filas=total, invalidas=invalid,
        fuera_de_zona=outside, duplicadas=before-len(df), utilizadas=len(df))


def fetch_web(now):
    start = now - timedelta(days=90)
    params = dict(BOUNDS, format='geojson', starttime=start.isoformat(),
                  endtime=now.isoformat(), orderby='time-asc', limit=20000, eventtype='earthquake')
    response = requests.get(USGS, params=params, timeout=(3, 10))
    response.raise_for_status()
    payload = response.json()
    if payload.get('type') != 'FeatureCollection' or not isinstance(payload.get('features'), list):
        raise ValueError('Respuesta USGS inválida.')
    if len(payload['features']) >= 20000:
        raise ValueError('Consulta USGS truncada; no se usará como catálogo completo.')
    rows = []
    for item in payload['features']:
        props = item['properties']
        coords = item['geometry']['coordinates']
        rows.append(dict(id=item['id'], fecha=pd.to_datetime(props['time'], unit='ms', utc=True),
                         magnitud=props['mag'], latitud=coords[1], longitud=coords[0],
                         ubicacion=props.get('place') or 'USGS'))
    df, quality = normalize(pd.DataFrame(rows, columns=[
        'id', 'fecha', 'magnitud', 'latitud', 'longitud', 'ubicacion']), 'USGS', now)
    if quality['invalidas'] or quality['fuera_de_zona'] or quality['duplicadas']:
        raise ValueError('USGS devolvió registros inconsistentes; se conserva el respaldo.')
    return df, dict(consultado=now.isoformat(), inicio=start.isoformat(), fin=now.isoformat(),
                   url=response.url, calidad=quality)


def save_cache(df, meta):
    CACHE.parent.mkdir(exist_ok=True)
    rows = df.assign(fecha=df.fecha.astype(str)).to_dict('records')
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=CACHE.parent,
                                     delete=False, suffix='.tmp') as handle:
        path = handle.name
        json.dump(dict(meta=meta, eventos=rows), handle, ensure_ascii=False, allow_nan=False)
    try:
        os.replace(path, CACHE)
    finally:
        if os.path.exists(path):
            os.unlink(path)


def get_web(now, enabled):
    warnings = []
    if enabled:
        try:
            df, meta = fetch_web(now)
            try:
                save_cache(df, meta)
            except OSError:
                warnings.append('No se pudo guardar el respaldo web en disco.')
            return df, dict(meta, estado='en_linea'), warnings
        except (requests.RequestException, ValueError, KeyError, TypeError, IndexError, OverflowError):
            warnings.append('La consulta USGS falló; se utiliza el rack local y el último respaldo válido.')
    try:
        payload = json.loads(CACHE.read_text(encoding='utf-8'))
        meta = payload['meta']
        if not all(key in meta for key in ('inicio', 'fin', 'consultado', 'url')):
            raise ValueError('Caché sin procedencia.')
        start, end, fetched = [pd.to_datetime(meta[key], utc=True) for key in ('inicio', 'fin', 'consultado')]
        if (pd.isna(start) or pd.isna(end) or pd.isna(fetched)
                or start >= end or end > pd.Timestamp(now) or fetched > pd.Timestamp(now)):
            raise ValueError('Fechas de caché inválidas.')
        if not isinstance(meta['url'], str) or not meta['url'].startswith(USGS):
            raise ValueError('Procedencia de caché inválida.')
        df, quality = normalize(pd.DataFrame(payload['eventos'], columns=[
            'id', 'fecha', 'magnitud', 'latitud', 'longitud', 'ubicacion']), 'USGS (caché)', now)
        if quality['invalidas'] or quality['fuera_de_zona']:
            raise ValueError('Caché corrupta.')
        warnings.append('Los registros USGS son una copia guardada, no una consulta en vivo.')
        return df, dict(meta, estado='cache'), warnings
    except (OSError, ValueError, KeyError, TypeError, OverflowError):
        return None, dict(estado='solo_local'), warnings


def summary(df):
    if df.empty:
        return dict(eventos=0, inicio=None, fin=None, magnitud_media=None, magnitud_maxima=None, zonas=[])
    return dict(eventos=len(df), inicio=df.fecha.min().isoformat(), fin=df.fecha.max().isoformat(),
                magnitud_media=round(float(df.magnitud.mean()), 2),
                magnitud_maxima=float(df.magnitud.max()),
                zonas=[dict(ubicacion=str(k), eventos=int(v)) for k, v in df.ubicacion.value_counts().head(8).items()])


def comparison(local, web, meta, threshold):
    if web is None or local.empty:
        return dict(disponible=False, motivo='Sin dos catálogos con cobertura contrastable.')
    start = max(local.fecha.min(), pd.to_datetime(meta['inicio'], utc=True))
    end = min(local.fecha.max(), pd.to_datetime(meta['fin'], utc=True))
    if end <= start:
        return dict(disponible=False, motivo='Los catálogos no tienen un intervalo temporal común.')
    a = local[local.fecha.between(start, end) & (local.magnitud >= threshold)]
    b = web[web.fecha.between(start, end) & (web.magnitud >= threshold)]
    matched = set()
    for row in a.itertuples():
        candidates = b[(abs((b.fecha-row.fecha).dt.total_seconds()) <= 60)
                       & (abs(b.magnitud-row.magnitud) <= .3)]
        best, distance = None, float('inf')
        for other in candidates.itertuples():
            km = 6371 * 2 * math.asin(min(1, math.sqrt(
                math.sin(math.radians(other.latitud-row.latitud)/2)**2
                + math.cos(math.radians(row.latitud))*math.cos(math.radians(other.latitud))
                * math.sin(math.radians(other.longitud-row.longitud)/2)**2)))
            if other.Index not in matched and km <= 20 and km < distance:
                best, distance = other.Index, km
        if best is not None:
            matched.add(best)
    return dict(disponible=True, inicio=start.isoformat(), fin=end.isoformat(),
                magnitud_minima=threshold, eventos_locales=len(a), eventos_web=len(b),
                coincidencias_aproximadas=len(matched), solo_local=len(a)-len(matched),
                solo_web=len(b)-len(matched),
                criterio='Un evento por coincidencia; ±60 segundos, ≤20 km, ±0.3 de magnitud.',
                interpretacion='Diferencias de cobertura y detección no prueban que un catálogo sea falso. '
                'Se comparan la misma ventana geográfica, temporal y umbral de magnitud.')


def features(history):
    recent = float(np.mean(history[-7:]))
    month = float(np.mean(history[-30:]))
    quarter = float(np.mean(history[-90:]))
    return [history[-1], history[-7], recent, month, quarter, recent-month, month-quarter]


FEATURE_NAMES = ['Registro el día anterior', 'Registro hace siete días', 'Frecuencia de siete días',
                 'Frecuencia de treinta días', 'Frecuencia de noventa días',
                 'Cambio semanal frente al mensual', 'Cambio mensual frente al trimestral']


def candidate_model(name):
    if name == 'Random Forest':
        return RandomForestClassifier(n_estimators=120, max_depth=4, min_samples_leaf=15,
                                      random_state=42, n_jobs=1)
    return make_pipeline(StandardScaler(), LogisticRegression(C=.3, max_iter=500, random_state=42))


def rate_interval(count, exposure):
    """Intervalo exacto Poisson 95% de la tasa; incluye eventos no observados cuando count=0."""
    lower = float(chi2.ppf(.025, 2*count)/2/exposure) if count else 0.
    upper = float(chi2.ppf(.975, 2*(count+1))/2/exposure)
    return lower, upper


def forecast(df, threshold=3.5, days=7, now=None):
    now = now or now_utc()
    if df.empty:
        return dict(disponible=False, motivo='No hay datos válidos en la zona.', dias=[], limitacion=LIMITACION)
    # Sólo días completos; no convertir el día actual parcial en una observación negativa.
    end = min(df.fecha.max().floor('D'), pd.Timestamp(now).floor('D')-pd.Timedelta(days=1))
    start = max(df.fecha.min().ceil('D'), end-pd.Timedelta(days=3650))
    if (end-start).days < 60:
        return dict(disponible=False, motivo='Se requieren al menos 60 días completos de historial.', dias=[], limitacion=LIMITACION)
    dates = pd.date_range(start, end, freq='D')
    selected = df[(df.magnitud >= threshold) & (df.fecha >= start) & (df.fecha < end+pd.Timedelta(days=1))]
    counts = selected.groupby(selected.fecha.dt.floor('D')).size().reindex(dates, fill_value=0)
    binary = (counts.values > 0).astype(int)
    rate = float(counts.mean())
    probability = float(-np.expm1(-rate))
    model, selected_name = None, 'Base estadística Poisson'
    validation = dict(evaluado=False, motivo='Se requieren 365 días y al menos 20 ejemplos de cada clase.')
    importance = []
    if len(binary) >= 365 and binary.sum() >= 20 and (1-binary).sum() >= 20:
        x = np.array([features(binary[:i]) for i in range(90, len(binary))])
        y = binary[90:]
        split = int(len(y)*.8)
        scores = {}
        for name in ('Random Forest', 'Regresión logística'):
            folds = []
            for train_idx, valid_idx in TimeSeriesSplit(n_splits=3).split(x[:split]):
                if len(np.unique(y[train_idx])) < 2:
                    continue
                candidate = candidate_model(name)
                candidate.fit(x[train_idx], y[train_idx])
                probs = candidate.predict_proba(x[valid_idx])[:, 1]
                base = float(-np.expm1(-counts.iloc[:90+train_idx[-1]+1].mean()))
                folds.append(dict(brier=float(brier_score_loss(y[valid_idx], probs)),
                    brier_base=float(brier_score_loss(y[valid_idx], np.full(len(valid_idx), base))),
                    fin_entrenamiento=dates[90+train_idx[-1]].isoformat(),
                    inicio_validacion=dates[90+valid_idx[0]].isoformat(),
                    fin_validacion=dates[90+valid_idx[-1]].isoformat()))
            if len(folds) == 3:
                scores[name] = dict(brier_medio=float(np.mean([f['brier'] for f in folds])),
                    brier_base_medio=float(np.mean([f['brier_base'] for f in folds])), ventanas=folds)
        if scores and len(np.unique(y[:split])) == 2:
            best_name = min(scores, key=lambda name: scores[name]['brier_medio'])
            candidate = candidate_model(best_name)
            candidate.fit(x[:split], y[:split])
            probs = candidate.predict_proba(x[split:])[:, 1]
            baseline = float(-np.expm1(-counts.iloc[:90+split].mean()))
            score = float(brier_score_loss(y[split:], probs))
            base_score = float(brier_score_loss(y[split:], np.full(len(probs), baseline)))
            cv_pass = scores[best_name]['brier_medio'] < scores[best_name]['brier_base_medio']
            calibration = []
            for lo, hi in zip([0,.2,.4,.6,.8], [.2,.4,.6,.8,1.000001]):
                mask = (probs >= lo) & (probs < hi)
                if mask.any():
                    calibration.append(dict(dias=int(mask.sum()),
                        probabilidad_media=round(float(probs[mask].mean()), 4),
                        frecuencia_observada=round(float(y[split:][mask].mean()), 4)))
            validation = dict(evaluado=True,
                esquema='Selección en tres ventanas temporales del primer 80%; evaluación final en el 20% posterior.',
                candidatos=scores, candidato_seleccionado=best_name,
                dias_prueba=len(probs), brier_modelo=round(score, 6),
                brier_base_poisson=round(base_score, 6), mejora_sobre_base=score < base_score,
                mejora_en_validacion_cruzada=cv_pass,
                habilidad_brier=round(1-score/base_score, 4) if base_score else None,
                calibracion=calibration, inicio_prueba=dates[90+split].isoformat(), fin_prueba=end.isoformat())
            if score < base_score and cv_pass:
                candidate.fit(x, y)
                model, selected_name = candidate, best_name
                weights = candidate.feature_importances_ if best_name == 'Random Forest' else abs(candidate[-1].coef_[0])
                total_weight = float(np.sum(weights)) or 1.
                importance = sorted([dict(variable=n, peso_relativo=round(float(w/total_weight), 4))
                    for n, w in zip(FEATURE_NAMES, weights)], key=lambda v: -v['peso_relativo'])
    # Catálogo desactualizado: no extrapolar estado reciente desde el último evento hasta hoy.
    age = max(0, (pd.Timestamp(now)-df.fecha.max()).total_seconds()/86400)
    if age > 7:
        model = None
    if model is None:
        selected_name = 'Base estadística Poisson'
        importance = []
    if age > 7:
        selection_reason = 'El catálogo tiene más de siete días de antigüedad; se utiliza la frecuencia histórica y se descarta extrapolar actividad reciente.'
    elif not validation['evaluado']:
        selection_reason = 'La cantidad de historial o de ejemplos de cada clase no permite evaluar los clasificadores con tres ventanas temporales.'
    elif not validation['mejora_en_validacion_cruzada']:
        selection_reason = 'El candidato elegido no superó la referencia en el promedio de las tres ventanas de selección; se conserva Poisson aunque la prueba final aislada pueda ser favorable.'
    elif not validation['mejora_sobre_base']:
        selection_reason = 'El candidato superó la selección temporal, pero no la referencia en la prueba final; se conserva Poisson.'
    else:
        selection_reason = 'El candidato superó la referencia en la selección temporal y en la prueba final; se reajustó con el historial disponible.'
    history = list(binary.astype(float))
    # Días posteriores a la cobertura: imputación explícita con la referencia, no ceros observados.
    missing_days = max(0, (pd.Timestamp(now).floor('D')-end).days) if model else 0
    history.extend([probability]*missing_days)
    result = []
    for i in range(days):
        p = float(model.predict_proba([features(history)])[0, 1]) if model else probability
        result.append(dict(fecha=(now+timedelta(days=i+1)).date().isoformat(),
                           probabilidad_evento=round(p, 4), magnitud_minima=threshold))
        history.append(p)
    return dict(disponible=True, modelo=selected_name,
                objetivo=f'Al menos un evento registrado de magnitud ≥ {threshold} por día, en la zona de estudio.',
                magnitud_minima=threshold, dias=result, validacion=validation,
                variables=FEATURE_NAMES, importancia_variables=importance,
                motivo_seleccion=selection_reason,
                dias_imputados=missing_days,
                explicacion_variables='Las variables describen registros anteriores; su peso expresa asociación estadística y no una causa física.',
                tasa_diaria=rate,
                intervalo_tasa_poisson_95=list(rate_interval(int(counts.sum()), len(counts))),
                entrenamiento=dict(inicio=start.isoformat(), fin=end.isoformat(), dias=len(counts),
                                   eventos=len(selected), dias_con_evento=int(binary.sum())),
                antiguedad_catalogo_dias=round(age, 1), catalogo_desactualizado=age > 7,
                extrapolacion='A varios días se reutilizan probabilidades como entradas; no se ha validado ese horizonte.',
                seleccion='Se usa el mejor candidato entre Random Forest y regresión logística sólo si supera Poisson en el promedio de tres ventanas temporales y en la prueba final, con catálogo de hasta siete días de antigüedad.',
                limitacion=LIMITACION)


def territorial_analysis(df, prediction, threshold, days, now):
    if df.empty:
        return dict(zonas=[], explicaciones=['Sin datos válidos para el análisis territorial.'], escenarios=None)
    begin, end = df.fecha.min(), df.fecha.max()
    exposure = max(1, (end-begin).total_seconds()/86400)
    recent_start = pd.Timestamp(now)-pd.Timedelta(days=30)
    previous_start = recent_start-pd.Timedelta(days=30)
    ranking = []
    # Nombres municipales del catálogo original; si faltan, celdas aproximadas de 0.25 grados.
    work = df.copy()
    unknown = work.ubicacion.isin(['Sin ubicación', 'Zona de estudio', ''])
    work.loc[unknown, 'ubicacion'] = work[unknown].apply(
        lambda r: f'Celda {math.floor(r.latitud*4)/4:.2f}, {math.floor(r.longitud*4)/4:.2f}', axis=1)
    for name, group in work.groupby('ubicacion'):
        recent = int((group.fecha >= recent_start).sum())
        previous = int(group.fecha.between(previous_start, recent_start, inclusive='left').sum())
        eligible = int((group.magnitud >= threshold).sum())
        lower, upper = rate_interval(eligible, exposure)
        ranking.append(dict(ubicacion=name, eventos=len(group), porcentaje=round(100*len(group)/len(df), 1),
            magnitud_media=round(float(group.magnitud.mean()), 2), magnitud_maxima=float(group.magnitud.max()),
            eventos_umbral=eligible, ultimos_30_dias=recent, anteriores_30_dias=previous,
            cambio='Aumento de registros' if recent > previous else 'Disminución de registros' if recent < previous else 'Sin cambio en conteo',
            probabilidad_base_horizonte=round(max(0., float(-np.expm1(-eligible/exposure*days))), 4) if exposure >= 60 else None,
            intervalo_probabilidad_base_95=[round(float(-np.expm1(-r*days)), 4) for r in (lower, upper)] if exposure >= 60 else None,
            ultimo_evento=group.fecha.max().isoformat(), latitud=round(float(group.latitud.mean()), 4),
            longitud=round(float(group.longitud.mean()), 4)))
    ranking.sort(key=lambda z: (-z['eventos'], z['ubicacion']))
    top = ranking[0]
    explanations = [
        f'{top["ubicacion"]} concentra {top["eventos"]} de {len(df)} registros ({top["porcentaje"]}%). '
        'Este ranking describe frecuencia en el catálogo, no peligro para personas o edificaciones. '
        'Las zonas con menos registros también pueden experimentar eventos importantes.',
        'Los conteos de los últimos treinta días se comparan con los treinta días anteriores, ambos relativos a la fecha del informe. '
        'Un cambio puede responder a detección, cobertura o reportes; por sí solo no demuestra un precursor sísmico.',
        f'Las probabilidades territoriales usan el mismo periodo de exposición de {exposure:.0f} días para todas las zonas '
        f'y magnitud mínima {threshold}. Son referencias Poisson bajo tasa constante; no son predicciones municipales validadas. '
        'El intervalo del 95% refleja incertidumbre de conteo bajo ese supuesto y no corrige subregistro ni cambios físicos. '
        'Con menos de sesenta días de exposición no se asignan probabilidades territoriales.'
    ]
    bins = [(-2, 3, 'Menor que 3.0'), (3, 4, '3.0 a menos de 4.0'),
            (4, 5, '4.0 a menos de 5.0'), (5, 6, '5.0 a menos de 6.0'), (6, 10.01, '6.0 o mayor')]
    magnitudes = [dict(rango=label, eventos=int(df.magnitud.between(lo, hi, inclusive='left').sum()))
                  for lo, hi, label in bins]
    modal = max(magnitudes, key=lambda b: b['eventos'])
    explanations.append(f'El intervalo de magnitud más representado es {modal["rango"]}: {modal["eventos"]} registros. '
        f'El máximo observado es {df.magnitud.max():.1f}. Esta distribución describe el pasado; '
        'no permite asignar una magnitud al próximo sismo y el máximo histórico no es un límite futuro.')
    scenarios = None
    if prediction['disponible']:
        lam = prediction['tasa_diaria']*days
        lo, hi = prediction['intervalo_tasa_poisson_95']
        p0, p1 = math.exp(-lam), lam*math.exp(-lam)
        probs = [p0, p1, max(0., 1-p0-p1)]
        labels = ['Ningún registro sobre el umbral', 'Un registro sobre el umbral', 'Dos o más registros sobre el umbral']
        scenarios = dict(horizonte_dias=days, magnitud_minima=threshold, eventos_esperados=round(lam, 3),
            modelo='Referencia Poisson de tasa histórica constante; independiente del clasificador diario.',
            posibilidades=[dict(escenario=label, probabilidad=round(p, 4)) for label, p in zip(labels, probs)],
            escenario_mas_probable=labels[int(np.argmax(probs))],
            conteo_mas_probable=int(math.floor(lam)),
            intervalo_probabilidad_al_menos_uno_95=[round(float(-np.expm1(-r*days)), 4) for r in (lo, hi)],
            intervalo_conteo_predictivo_95=[int(poisson.ppf(.025, lam)), int(poisson.ppf(.975, lam))],
            supuestos='Tasa estable, eventos independientes y cobertura comparable. No modela réplicas ni fallas tectónicas. '
                      'Los intervalos no incluyen incertidumbre de cobertura y el intervalo de conteos usa una tasa puntual.')
        explanations.append(f'En {days} días, la referencia espera {lam:.2f} registros de magnitud al menos {threshold}. '
            f'Entre las categorías presentadas, la más probable es: {scenarios["escenario_mas_probable"].lower()}. '
            'Un valor esperado fraccionario es un promedio de escenarios, no una fracción de sismo. '
            'Ningún registro sobre el umbral puede coexistir con sismos menores o eventos no detectados.')
        v = prediction['validacion']
        if v['evaluado']:
            explanations.append(f'En la prueba final se obtuvo Brier {v["brier_modelo"]} para '
                f'{v.get("candidato_seleccionado", "el modelo")} y {v["brier_base_poisson"]} para Poisson. '
                f'El método usado es {prediction["modelo"]}. Brier mide el error cuadrático de las probabilidades '
                'frente a los registros observados: menor es mejor; no equivale a un porcentaje de exactitud. '
                'Una mejora histórica no garantiza rendimiento futuro ni valida todos los horizontes.')
    return dict(zonas=ranking[:10], total_zonas=len(ranking), explicaciones=explanations,
                magnitudes=magnitudes, escenarios=scenarios,
                cobertura=dict(inicio=begin.isoformat(), fin=end.isoformat(), dias=round(exposure, 1)))


def build_report(upload=None, online=True, threshold=3.5, days=7):
    now = now_utc()
    local, quality = normalize(read_csv(LOCAL.read_bytes()), 'Rack local SGC', now)
    supplied = None
    sources = [dict(nombre='Rack local SGC', archivo=LOCAL.name, calidad=quality, resumen=summary(local))]
    warnings = ['El archivo local contiene reportes de percepción; no garantiza un catálogo instrumental completo.',
                'Se excluyen epicentros fuera de la ventana geográfica, aunque el reporte provenga de Santander.',
                'No se usan las profundidades inferidas aleatoriamente de los archivos derivados.']
    if upload is not None:
        supplied, quality = normalize(read_csv(upload), 'CSV proporcionado', now)
        if supplied.empty:
            raise ValueError('El CSV no contiene eventos válidos dentro de la zona de estudio.')
        sources.append(dict(nombre='CSV proporcionado', calidad=quality, resumen=summary(supplied)))
    primary = supplied if supplied is not None else local
    web, status, web_warnings = get_web(now, online)
    warnings.extend(web_warnings)
    if web is not None:
        sources.append(dict(nombre='USGS', estado=status['estado'], resumen=summary(web),
                            url=status['url'], consultado=status['consultado'],
                            cobertura=dict(inicio=status['inicio'], fin=status['fin'])))
    contrast = comparison(primary, web, status, threshold)
    # No mezclar catálogos con distintas coberturas: producir estimaciones separadas.
    prediction = forecast(primary, threshold, days, now)
    web_prediction = None
    if web is not None and not web.empty:
        web_prediction = forecast(web, threshold, days, now)
    stats = summary(primary)
    territory = territorial_analysis(primary, prediction, threshold, days, now)
    conclusion = (f'Se analizaron {stats["eventos"]} eventos válidos del '
                  f'{"CSV proporcionado" if supplied is not None else "rack local"} en la zona de estudio. ')
    if stats['eventos']:
        conclusion += f'La magnitud máxima registrada es {stats["magnitud_maxima"]:.1f}. '
    if contrast['disponible']:
        conclusion += (f'En el intervalo común hay {contrast["eventos_locales"]} eventos de la fuente principal '
                       f'y {contrast["eventos_web"]} de USGS; {contrast["coincidencias_aproximadas"]} coincidencias aproximadas. ')
    else:
        conclusion += contrast['motivo'] + ' '
    if prediction.get('catalogo_desactualizado'):
        warnings.append('Catálogo principal desactualizado: las probabilidades reflejan frecuencia histórica, no actividad actual.')
    if prediction['disponible']:
        conclusion += f'El método seleccionado es {prediction["modelo"]}. '
    if territory['zonas']:
        top = territory['zonas'][0]
        conclusion += f'{top["ubicacion"]} concentra el mayor número de registros ({top["porcentaje"]}%). '
    if territory['escenarios']:
        conclusion += (f'Para {days} días, la categoría con mayor probabilidad según la referencia histórica es: '
                       f'{territory["escenarios"]["escenario_mas_probable"].lower()}. ')
    conclusion += LIMITACION
    return dict(generado=now.isoformat(), modo=status['estado'], zona=BOUNDS,
                descripcion_zona='Ventana regional alrededor de Santander; no es un límite administrativo.',
                fuentes=sources, resumen=stats, contraste=contrast, prediccion=prediction,
                analisis_territorial=territory,
                prediccion_web=web_prediction, advertencias=warnings, conclusion=conclusion,
                referencias=[dict(nombre='USGS: límites de la predicción',
                    url='https://www.usgs.gov/faqs/can-you-predict-earthquakes'),
                    dict(nombre='USGS: API del catálogo', url='https://earthquake.usgs.gov/fdsnws/event/1/'),
                    dict(nombre='Scikit-learn: validación con ventanas temporales',
                         url='https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html'),
                    dict(nombre='Scikit-learn: evaluación y calibración probabilística',
                         url='https://scikit-learn.org/stable/modules/calibration.html')])
