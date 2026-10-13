"""Documento institucional generado íntegramente sin servicios externos."""
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.graphics.shapes import Drawing, Rect, String

NAVY = colors.HexColor('#142D45')
TEAL = colors.HexColor('#147D88')
MUTED = colors.HexColor('#536778')
PALE = colors.HexColor('#EDF4F7')
WIDTH = A4[0]-38*mm


def clean(value):
    return str(value if value is not None else 'Sin datos').replace('≥', '>=').replace('≤', '<=').replace('−', '-').replace('–', '-').replace('—', '-')


def date(value):
    return clean(value).replace('T', ' ')[:16] if value else 'Sin datos'


def pct(value):
    return f'{100*value:.1f}%' if value is not None else 'Historial insuficiente'


def render_report(report):
    buffer = BytesIO()
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='ReportTitle', fontName='Helvetica-Bold', fontSize=29,
                              leading=34, textColor=NAVY, spaceAfter=18))
    styles.add(ParagraphStyle(name='ReportSection', fontName='Helvetica-Bold', fontSize=17,
                              leading=22, textColor=NAVY, spaceBefore=12, spaceAfter=12, keepWithNext=True))
    styles.add(ParagraphStyle(name='ReportSub', fontName='Helvetica-Bold', fontSize=11,
                              leading=15, textColor=TEAL, spaceBefore=12, spaceAfter=7, keepWithNext=True))
    styles.add(ParagraphStyle(name='ReportBody', fontName='Helvetica', fontSize=9.5, leading=14,
                              textColor=NAVY, spaceAfter=9, splitLongWords=True))
    styles.add(ParagraphStyle(name='ReportSmall', parent=styles['ReportBody'], fontSize=8, leading=11, textColor=MUTED))
    styles.add(ParagraphStyle(name='ReportCell', parent=styles['ReportBody'], fontSize=8, leading=11, spaceAfter=0))
    styles.add(ParagraphStyle(name='ReportHead', parent=styles['ReportCell'], fontName='Helvetica-Bold', textColor=colors.white))
    story = []

    def p(text, style='ReportBody'):
        return Paragraph(escape(clean(text)), styles[style])

    def body(text, style='ReportBody'):
        story.append(p(text, style))

    def heading(text):
        body(text, 'ReportSection')

    def table(headers, rows, widths=None):
        data = [[p(h, 'ReportHead') for h in headers]]
        data.extend([[p(c, 'ReportCell') for c in row] for row in rows])
        obj = Table(data, colWidths=widths, repeatRows=1, hAlign='LEFT')
        obj.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), NAVY), ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, PALE]),
            ('LEFTPADDING', (0,0), (-1,-1), 8), ('RIGHTPADDING', (0,0), (-1,-1), 8),
            ('TOPPADDING', (0,0), (-1,-1), 8), ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ('LINEBELOW', (0,-1), (-1,-1), .5, colors.HexColor('#D5E0E7'))]))
        story.extend([obj, Spacer(1, 10)])

    def forecast_section(prediction, title):
        body(title, 'ReportSub')
        if not prediction['disponible']:
            body(prediction['motivo'])
            return
        body(f'Método: {prediction["modelo"]}. {prediction["objetivo"]}')
        training = prediction['entrenamiento']
        body(f'Periodo de entrenamiento UTC: {date(training["inicio"])} a {date(training["fin"])}. '
             f'{training["dias"]} días completos y {training["eventos"]} registros sobre el umbral. '
             f'Último registro hace {prediction["antiguedad_catalogo_dias"]} días.')
        table(['Día UTC', 'Probabilidad experimental de al menos un registro'],
              [[d['fecha'], pct(d['probabilidad_evento'])] for d in prediction['dias']], [WIDTH*.3, WIDTH*.7])
        body(prediction['seleccion'])
        body(prediction['motivo_seleccion'])
        v = prediction['validacion']
        if v['evaluado']:
            body(v['esquema'])
            table(['Candidato en prueba final', 'Brier candidato', 'Brier Poisson', 'Días evaluados'],
                  [[v['candidato_seleccionado'], v['brier_modelo'], v['brier_base_poisson'], v['dias_prueba']]],
                  [WIDTH*.4, WIDTH*.2, WIDTH*.2, WIDTH*.2])
            rows = []
            for name, score in v.get('candidatos', {}).items():
                for index, fold in enumerate(score['ventanas'], 1):
                    rows.append([name, index, date(fold['inicio_validacion'])[:10],
                                 f'{fold["brier"]:.5f}', f'{fold["brier_base"]:.5f}'])
            table(['Candidato', 'Ventana', 'Inicio de prueba', 'Brier', 'Base'], rows,
                  [WIDTH*.30, WIDTH*.13, WIDTH*.23, WIDTH*.17, WIDTH*.17])
            body('Calibración observada en la prueba final', 'ReportSub')
            table(['Días agrupados', 'Probabilidad media estimada', 'Frecuencia realmente observada'],
                  [[b['dias'], pct(b['probabilidad_media']), pct(b['frecuencia_observada'])]
                   for b in v.get('calibracion', [])], [WIDTH*.24, WIDTH*.38, WIDTH*.38])
            body('Estas agrupaciones permiten revisar si las probabilidades se aproximan a la frecuencia registrada. '
                 'No prueban calibración futura; Brier tampoco equivale a porcentaje de exactitud.', 'ReportSmall')
        else:
            body(v['motivo'])
        body(prediction.get('explicacion_variables', ''), 'ReportSmall')
        if prediction.get('importancia_variables'):
            table(['Variable', 'Peso relativo global (no causal)'],
                  [[i['variable'], pct(i['peso_relativo'])] for i in prediction['importancia_variables']],
                  [WIDTH*.65, WIDTH*.35])
        else:
            body('La referencia Poisson depende del número de registros sobre el umbral y de los días de exposición; '
                 'no atribuye influencia a variables de un clasificador descartado.', 'ReportSmall')
        body(f'Días sin observación completa imputados para el clasificador: {prediction.get("dias_imputados", 0)}. '
             + prediction['extrapolacion'], 'ReportSmall')

    def page(canvas, doc):
        canvas.saveState()
        w, h = A4
        canvas.setFillColor(NAVY)
        canvas.rect(0, h-11*mm, w, 11*mm, fill=1, stroke=0)
        canvas.setFont('Helvetica-Bold', 8)
        canvas.setFillColor(colors.white)
        canvas.drawString(19*mm, h-7.3*mm, 'SISTEMA DE ANALISIS SISMICO | INFORME TECNICO REGIONAL')
        canvas.setStrokeColor(colors.HexColor('#D5E0E7'))
        canvas.line(19*mm, 16*mm, w-19*mm, 16*mm)
        canvas.setFillColor(MUTED)
        canvas.setFont('Helvetica', 7)
        canvas.drawString(19*mm, 11.5*mm, 'Informe experimental - No constituye una alerta ni una prediccion individual')
        canvas.drawRightString(w-19*mm, 11.5*mm, f'Pagina {doc.page}')
        canvas.restoreState()

    body('INFORME TECNICO / ACTIVIDAD REGISTRADA', 'ReportSub')
    body('Análisis sísmico\ny escenarios probabilísticos'.replace('\n', ' '), 'ReportTitle')
    body(f'Fecha de emisión: {date(report["generado"])} UTC | Modo de datos: {report["modo"]}', 'ReportSmall')
    stats = report['resumen']
    table(['Eventos analizados', 'Magnitud máxima observada', 'Zonas identificadas'],
          [[stats['eventos'], stats['magnitud_maxima'], report['analisis_territorial'].get('total_zonas', 0)]], [WIDTH/3]*3)
    heading('01 / Resumen ejecutivo')
    body(report['conclusion'])
    body('Alcance de la interpretación', 'ReportSub')
    body(report['descripcion_zona'] + ' Latitud: 5.4 a 8.4. Longitud: -74.7 a -72.0. '
         'Las fechas de tablas y periodos se expresan en UTC. Los eventos se cuentan según el catálogo suministrado; '
         'no se incorporan profundidades inferidas ni se calculan daños o intensidad futura.')
    heading('02 / Procedencia y calidad de los datos')
    rows = []
    for source in report['fuentes']:
        q = source.get('calidad')
        rows.append([source['nombre'], source['resumen']['eventos'],
            f'{date(source["resumen"]["inicio"])[:10]} a {date(source["resumen"]["fin"])[:10]}',
            f'{q["invalidas"]} inválidas; {q["fuera_de_zona"]} fuera; {q["duplicadas"]} duplicadas' if q else
            f'{source["estado"]}. Consulta: {date(source["consultado"])}'])
    table(['Fuente', 'Válidos', 'Cobertura UTC', 'Control / actualización'], rows,
          [WIDTH*.23, WIDTH*.12, WIDTH*.28, WIDTH*.37])
    body('Los archivos cargados desde la página se analizan sin incorporarlos permanentemente al rack. '
         'USGS y la fuente principal mantienen estimaciones separadas para evitar mezclar coberturas.', 'ReportSmall')

    story.append(PageBreak())
    heading('03 / Distribución territorial')
    territory = report['analisis_territorial']
    body('Zonas con más sismos registrados', 'ReportSub')
    body('Ordenadas por número de registros válidos. La probabilidad territorial corresponde a una referencia histórica '
         'para el horizonte solicitado y el umbral seleccionado; no constituye un ranking de peligro.', 'ReportSmall')
    table(['Zona', 'Registros / %', 'Mag. máx.', 'Últimos / previos 30 días', 'P. base horizonte'],
          [[z['ubicacion'], f'{z["eventos"]} / {z["porcentaje"]}%', z['magnitud_maxima'],
            f'{z["ultimos_30_dias"]} / {z["anteriores_30_dias"]}',
            pct(z['probabilidad_base_horizonte']) + (f' (95%: {pct(z["intervalo_probabilidad_base_95"][0])} '
                f'a {pct(z["intervalo_probabilidad_base_95"][1])})' if z['intervalo_probabilidad_base_95'] else '')]
           for z in territory['zonas']], [WIDTH*.29, WIDTH*.18, WIDTH*.13, WIDTH*.22, WIDTH*.18])
    if territory['zonas']:
        zones = territory['zonas'][:6]
        drawing = Drawing(WIDTH, len(zones)*24+24)
        peak = max(z['eventos'] for z in zones)
        for i, z in enumerate(zones):
            y = drawing.height-28-i*24
            label = clean(z['ubicacion'])
            if len(label) > 27:
                label = label[:24]+'...'
            drawing.add(String(0, y+3, label, fontName='Helvetica', fontSize=8, fillColor=NAVY))
            drawing.add(Rect(150, y, (WIDTH-190)*z['eventos']/peak, 13, fillColor=TEAL, strokeColor=None))
            drawing.add(String(WIDTH-32, y+3, str(z['eventos']), fontName='Helvetica-Bold', fontSize=8, fillColor=NAVY))
        story.append(drawing)
    for explanation in territory['explicaciones'][:3]:
        body(explanation)

    heading('04 / Escenarios para el horizonte solicitado')
    scenarios = territory['escenarios']
    if scenarios:
        body(f'Horizonte: {scenarios["horizonte_dias"]} días. Magnitud mínima: {scenarios["magnitud_minima"]}. '
             f'Número esperado de registros: {scenarios["eventos_esperados"]}.')
        table(['Escenario de registros sobre el umbral', 'Probabilidad base'],
              [[s['escenario'], pct(s['probabilidad'])] for s in scenarios['posibilidades']], [WIDTH*.75, WIDTH*.25])
        body(f'Categoría más probable: {scenarios["escenario_mas_probable"]}. '
             f'Conteo modal: {scenarios["conteo_mas_probable"]}. '
             f'Intervalo predictivo de conteos del 95% con tasa puntual: {scenarios["intervalo_conteo_predictivo_95"][0]} '
             f'a {scenarios["intervalo_conteo_predictivo_95"][1]}.')
        interval = scenarios['intervalo_probabilidad_al_menos_uno_95']
        body(f'Intervalo del 95% para la probabilidad base de al menos un registro: {pct(interval[0])} a {pct(interval[1])}. '
             'Este intervalo representa incertidumbre de tasa bajo Poisson y no es el intervalo de confianza del clasificador.')
        body(scenarios['modelo']+' '+scenarios['supuestos'], 'ReportSmall')
    else:
        body('El historial no permite producir escenarios cuantitativos con el mínimo de evidencia requerido.')
    body('Distribución histórica de magnitudes', 'ReportSub')
    table(['Intervalo de magnitud', 'Registros'],
          [[b['rango'], b['eventos']] for b in territory.get('magnitudes', [])], [WIDTH*.75, WIDTH*.25])
    for explanation in territory['explicaciones'][3:]:
        body(explanation)
    c = report['contraste']
    body('Contraste con el catálogo externo', 'ReportSub')
    if c['disponible']:
        body(f'Intervalo común UTC: {date(c["inicio"])} a {date(c["fin"])}. Magnitud mínima: {c["magnitud_minima"]}.')
        table(['Fuente principal', 'USGS', 'Coincidencias', 'Sólo principal', 'Sólo USGS'],
              [[c['eventos_locales'], c['eventos_web'], c['coincidencias_aproximadas'], c['solo_local'], c['solo_web']]], [WIDTH/5]*5)
        body(c['criterio']+' '+c['interpretacion'])
    else:
        body(c['motivo'])

    heading('05 / Modelo, evaluación y explicación')
    forecast_section(report['prediccion'], 'Estimación del catálogo principal')
    if report.get('prediccion_web'):
        forecast_section(report['prediccion_web'], 'Estimación independiente de USGS')
    heading('06 / Limitaciones y referencias')
    for warning in report['advertencias']:
        body(warning)
    body(report['prediccion']['limitacion'])
    references = report['referencias'] + [dict(nombre='Consulta USGS aplicada al informe', url=f['url'])
                                          for f in report['fuentes'] if f.get('url')]
    for ref in references:
        label = escape(clean(ref['nombre']))
        url = escape(ref['url'], {'"': '&quot;'})
        story.append(Paragraph(f'<link href="{url}" color="#147D88">{label}</link>', styles['ReportSmall']))
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=19*mm, leftMargin=19*mm,
                            topMargin=22*mm, bottomMargin=23*mm,
                            title='Informe técnico de actividad sísmica registrada',
                            author='Sistema de análisis sísmico regional')
    doc.build(story, onFirstPage=page, onLaterPages=page)
    return buffer.getvalue()
