/* Reportes disponibles también cuando los mapas y gráficos CDN no cargan. */
let ultimoInforme = null;
function textoNodo(tag, value, parent) {
    const node = document.createElement(tag);
    node.textContent = value;
    parent.appendChild(node);
    return node;
}
function tablaInforme(parent, headers, rows) {
    const table = document.createElement('table');
    const tr = document.createElement('tr');
    headers.forEach(h => textoNodo('th', h, tr));
    const head = document.createElement('thead'); head.appendChild(tr); table.appendChild(head);
    const body = document.createElement('tbody');
    rows.forEach(row => {
        const line = document.createElement('tr');
        row.forEach(value => textoNodo('td', value ?? 'Sin datos', line));
        body.appendChild(line);
    });
    table.appendChild(body); parent.appendChild(table);
}
async function generarInforme(event) {
    event.preventDefault();
    const button = document.getElementById('generar-informe');
    const status = document.getElementById('estado-informe');
    button.disabled = true;
    ultimoInforme = null;
    document.getElementById('descargar-informe').disabled = true;
    document.getElementById('descargar-pdf').disabled = true;
    document.getElementById('informe-contenido').replaceChildren();
    status.textContent = 'Analizando el rack y evaluando el modelo; la consulta web puede tardar unos segundos…';
    const form = new FormData(event.target);
    form.set('web', document.getElementById('consultar-web').checked ? 'true' : 'false');
    try {
        const response = await fetch('/api/analisis', {method: 'POST', body: form});
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'No se pudo generar el informe.');
        ultimoInforme = data;
        status.textContent = `Modo: ${data.modo} · Generado: ${new Date(data.generado).toLocaleString('es-CO')}`;
        const root = document.getElementById('informe-contenido'); root.replaceChildren();
        const cover = document.createElement('div'); cover.className = 'report-cover'; root.appendChild(cover);
        textoNodo('p', 'ANÁLISIS REGIONAL · INFORME TÉCNICO', cover).className = 'report-eyebrow';
        textoNodo('h2', 'Actividad sísmica registrada', cover);
        textoNodo('p', `Emitido ${new Date(data.generado).toLocaleString('es-CO')} · ${data.modo} · Horas de tablas en UTC`, cover);
        const metrics = document.createElement('div'); metrics.className = 'report-metrics'; root.appendChild(metrics);
        [[data.resumen.eventos, 'Registros válidos'], [data.analisis_territorial.total_zonas || 0, 'Zonas identificadas'],
            [data.resumen.magnitud_maxima ?? '—', 'Magnitud máxima histórica']].forEach(([value, label]) => {
                const card = document.createElement('div'); metrics.appendChild(card);
                textoNodo('strong', value, card); textoNodo('span', label, card);
            });
        textoNodo('h3', 'Conclusión basada en los datos', root);
        textoNodo('p', data.conclusion, root);
        textoNodo('p', data.descripcion_zona + ' Latitud 5.4–8.4; longitud −74.7–−72.0.', root);
        textoNodo('h3', 'Fuentes y calidad del rack', root);
        tablaInforme(root, ['Fuente', 'Eventos válidos', 'Inicio UTC', 'Último evento UTC', 'Calidad / actualización'],
            data.fuentes.map(f => [f.nombre, f.resumen.eventos, f.resumen.inicio, f.resumen.fin,
                f.calidad ? `${f.calidad.invalidas} inválidas, ${f.calidad.fuera_de_zona} fuera de zona, ${f.calidad.duplicadas} duplicadas` : `${f.estado}; consultado ${f.consultado}`]));
        data.fuentes.filter(f => f.url).forEach(f => {
            const p = document.createElement('p'); root.appendChild(p);
            const link = textoNodo('a', 'Ver consulta USGS y sus filtros', p);
            link.href = f.url; link.target = '_blank'; link.rel = 'noopener noreferrer';
        });
        textoNodo('h3', 'Contraste en el intervalo común', root);
        const c = data.contraste;
        if (c.disponible) {
            textoNodo('p', `${c.inicio} — ${c.fin}. Magnitud ≥ ${c.magnitud_minima}. ${c.criterio}`, root);
            tablaInforme(root, ['Fuente principal', 'USGS', 'Coincidencias', 'Sólo principal', 'Sólo USGS'],
                [[c.eventos_locales, c.eventos_web, c.coincidencias_aproximadas, c.solo_local, c.solo_web]]);
            textoNodo('p', c.interpretacion, root);
        } else textoNodo('p', c.motivo, root);
        mostrarTerritorio(data.analisis_territorial, root);
        mostrarPronostico(data.prediccion, 'Estimación del catálogo principal', root);
        if (data.prediccion_web) mostrarPronostico(data.prediccion_web, 'Estimación independiente de USGS', root);
        textoNodo('h3', 'Observaciones y límites', root);
        const list = document.createElement('ul'); root.appendChild(list);
        data.advertencias.forEach(w => textoNodo('li', w, list));
        data.referencias.forEach(f => {
            const p = document.createElement('p'); root.appendChild(p);
            const link = textoNodo('a', f.nombre, p); link.href = f.url;
            link.target = '_blank'; link.rel = 'noopener noreferrer';
        });
        document.getElementById('descargar-informe').disabled = false;
        document.getElementById('descargar-pdf').disabled = false;
    } catch (error) {
        status.textContent = `Error: ${error.message}`;
    } finally { button.disabled = false; }
}
function mostrarTerritorio(t, root) {
    textoNodo('h3', 'Zonas con mayor actividad registrada', root);
    textoNodo('p', 'El orden refleja registros del catálogo. La probabilidad por zona es una referencia Poisson para el horizonte y umbral elegidos; no mide daños ni peligro.', root);
    tablaInforme(root, ['Zona', 'Registros', '% del catálogo', 'Magnitud máxima', 'Últimos / previos 30 días', 'P. base en horizonte', 'Intervalo 95% de P. base'],
        t.zonas.map(z => [z.ubicacion, z.eventos, `${z.porcentaje}%`, z.magnitud_maxima,
            `${z.ultimos_30_dias} / ${z.anteriores_30_dias}`,
            z.probabilidad_base_horizonte === null ? 'Historial insuficiente' : `${(z.probabilidad_base_horizonte*100).toFixed(1)}%`,
            z.intervalo_probabilidad_base_95?.map(p => `${(p*100).toFixed(1)}%`).join(' a ') ?? 'Historial insuficiente']));
    textoNodo('h3', 'Escenarios más probables y su interpretación', root);
    const s = t.escenarios;
    if (s) {
        textoNodo('p', `Horizonte: ${s.horizonte_dias} días · Magnitud mínima: ${s.magnitud_minima} · Registros esperados: ${s.eventos_esperados}.`, root);
        tablaInforme(root, ['Escenario sobre el umbral', 'Probabilidad base'], s.posibilidades.map(v => [v.escenario, `${(v.probabilidad*100).toFixed(1)}%`]));
        textoNodo('p', `Categoría más probable: ${s.escenario_mas_probable}. Conteo modal: ${s.conteo_mas_probable}. Intervalo predictivo del 95% con tasa puntual: ${s.intervalo_conteo_predictivo_95.join(' a ')} registros.`, root);
        textoNodo('p', `Intervalo del 95% de la probabilidad base de al menos un registro: ${s.intervalo_probabilidad_al_menos_uno_95.map(p => `${(p*100).toFixed(1)}%`).join(' a ')}. No es un intervalo del clasificador.`, root);
        textoNodo('p', s.modelo + ' ' + s.supuestos, root);
    } else textoNodo('p', 'Historial insuficiente para cuantificar escenarios.', root);
    textoNodo('h3', 'Explicación ampliada de los resultados', root);
    t.explicaciones.forEach(text => textoNodo('p', text, root));
    if (t.magnitudes) {
        textoNodo('h3', 'Distribución histórica de magnitudes', root);
        tablaInforme(root, ['Intervalo de magnitud', 'Registros'], t.magnitudes.map(m => [m.rango, m.eventos]));
    }
}
function mostrarPronostico(p, title, root) {
    textoNodo('h3', title, root);
    if (!p.disponible) { textoNodo('p', p.motivo, root); return; }
    textoNodo('p', `${p.modelo}. ${p.objetivo} Último registro hace ${p.antiguedad_catalogo_dias} días.`, root);
    textoNodo('p', `Entrenamiento: ${p.entrenamiento.inicio} — ${p.entrenamiento.fin}; ${p.entrenamiento.eventos} eventos; ${p.entrenamiento.dias} días completos.`, root);
    const v = p.validacion;
    textoNodo('p', v.evaluado ? `${v.esquema}. Brier modelo: ${v.brier_modelo}; base: ${v.brier_base_poisson} (menor es mejor).` : v.motivo, root);
    textoNodo('p', p.seleccion + ' ' + p.extrapolacion, root);
    textoNodo('p', p.motivo_seleccion, root);
    if (v.candidatos) {
        tablaInforme(root, ['Modelo candidato', 'Brier medio en 3 ventanas', 'Brier medio de referencia'],
            Object.entries(v.candidatos).map(([name, score]) => [name, score.brier_medio.toFixed(6), score.brier_base_medio.toFixed(6)]));
        textoNodo('p', `Candidato evaluado en la prueba final: ${v.candidato_seleccionado}. La selección se realiza antes de esa prueba. Las ventanas validan predicciones a un día; no garantizan rendimiento futuro.`, root);
        tablaInforme(root, ['Días de prueba agrupados', 'Probabilidad media estimada', 'Frecuencia observada'],
            v.calibracion.map(b => [b.dias, `${(b.probabilidad_media*100).toFixed(1)}%`, `${(b.frecuencia_observada*100).toFixed(1)}%`]));
    }
    textoNodo('p', p.explicacion_variables + ` Días imputados sin observación completa: ${p.dias_imputados}.`, root);
    if (p.importancia_variables?.length) tablaInforme(root, ['Variable', 'Peso relativo global (no causal)'],
        p.importancia_variables.map(i => [i.variable, `${(i.peso_relativo*100).toFixed(1)}%`]));
    tablaInforme(root, ['Día UTC', 'Probabilidad experimental de ≥1 registro'],
        p.dias.map(d => [d.fecha, `${(d.probabilidad_evento*100).toFixed(1)}%`]));
    textoNodo('p', p.limitacion, root);
}
document.getElementById('form-informe').addEventListener('submit', generarInforme);
document.getElementById('descargar-informe').addEventListener('click', () => {
    if (!ultimoInforme) return;
    const {export_token, ...report} = ultimoInforme;
    const url = URL.createObjectURL(new Blob([JSON.stringify(report, null, 2)], {type:'application/json'}));
    const link = document.createElement('a'); link.href = url; link.download = 'informe-sismico.json'; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
});
document.getElementById('descargar-pdf').addEventListener('click', async () => {
    if (!ultimoInforme) return;
    const button = document.getElementById('descargar-pdf');
    const token = ultimoInforme.export_token;
    button.disabled = true; button.textContent = 'Preparando PDF…';
    try {
        const response = await fetch('/api/informes/pdf', {method:'POST',
            headers:{'Content-Type':'application/json'}, body:JSON.stringify({token})});
        if (!response.ok) {
            const error = await response.json(); throw new Error(error.error || 'No se pudo exportar.');
        }
        const url = URL.createObjectURL(await response.blob());
        const link = document.createElement('a'); link.href = url; link.download = 'informe-sismico.pdf'; link.click();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (error) {
        document.getElementById('estado-informe').textContent = error.message;
    } finally {
        button.disabled = !ultimoInforme; button.textContent = 'Exportar informe PDF';
    }
});
