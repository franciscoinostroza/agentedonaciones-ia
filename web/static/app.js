/* ─── Tabs ──────────────────────────────────────────────────── */
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(s => s.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
    if (btn.dataset.tab === 'historial')  loadHistorial();
    if (btn.dataset.tab === 'mis-emails') loadRefs();
    if (btn.dataset.tab === 'guardadas')  loadGuardadasTab();
  });
});

/* ─── Zona chips ────────────────────────────────────────────── */
let zonaSeleccionada = 'GBA / Conurbano Bonaerense';
document.querySelectorAll('.zona-chip').forEach(chip => {
  chip.addEventListener('click', () => {
    document.querySelectorAll('.zona-chip').forEach(c => c.classList.remove('active'));
    chip.classList.add('active');
    zonaSeleccionada = chip.dataset.zona;
  });
});

/* ─── Estado global ─────────────────────────────────────────── */
let _resultados     = [];
let _guardadas      = [];
let _todasGuardadas = [];
let _necesidad      = '';
let _zona           = '';

/* ─── Buscar ────────────────────────────────────────────────── */
const necInput  = document.getElementById('necesidad-input');
const btnBuscar = document.getElementById('btn-buscar');
const statusEl  = document.getElementById('search-status');
const resultadosDiv = document.getElementById('resultados');

btnBuscar.addEventListener('click', buscar);
necInput.addEventListener('keydown', e => { if (e.key === 'Enter') buscar(); });

async function buscar() {
  const necesidad = necInput.value.trim();
  if (!necesidad) return;

  btnBuscar.disabled = true;
  resultadosDiv.innerHTML = '';
  document.getElementById('guardadas-section').classList.add('hidden');
  showStatus('loading', '<span class="spinner"></span>Buscando <strong>' + esc(necesidad) + '</strong>...');

  try {
    const res = await fetch('/api/buscar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ necesidad, zona: zonaSeleccionada }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Error');

    _resultados = data.resultados || [];
    _guardadas  = data.guardadasPrevias || [];
    _necesidad  = necesidad;
    _zona       = data.zona || zonaSeleccionada;

    hideStatus();
    renderResultados(_resultados);
    renderGuardadas(_guardadas);

    // Si hay IA disponible, buscar en segundo plano
    if (data.ia_pendiente) {
      showStatus('loading', '<span class="spinner"></span> La IA esta buscando mas empresas en la web...');
      buscarIABackground(necesidad);
    }
  } catch (err) {
    showStatus('error', err.message);
  } finally {
    btnBuscar.disabled = false;
  }
}

async function buscarIABackground(necesidad) {
  try {
    const res = await fetch('/api/buscar-ia', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ necesidad }),
    });
    const data = await res.json();
    if (data.empresas && data.empresas.length > 0) {
      // Evitar duplicados con lo que ya tenemos
      const nombresExistentes = new Set(_resultados.map(r => r.nombre.toLowerCase()));
      const nuevas = data.empresas.filter(e => !nombresExistentes.has((e.nombre || '').toLowerCase()));
      _resultados = _resultados.concat(nuevas);
      // Reordenar por match
      _resultados.sort((a, b) => (b.match_score || 0) - (a.match_score || 0));
      renderResultados(_resultados);
      showStatus('', 'IA encontro ' + nuevas.length + ' empresa(s) adicional(es).');
      setTimeout(hideStatus, 5000);
    } else {
      showStatus('', 'IA no encontro empresas adicionales.');
      setTimeout(hideStatus, 3000);
    }
  } catch (e) {
    showStatus('', 'Busqueda IA no disponible.');
    setTimeout(hideStatus, 3000);
  }
}

function showStatus(type, html) {
  statusEl.className = 'status ' + type;
  statusEl.innerHTML = html;
  statusEl.classList.remove('hidden');
}
function hideStatus() { statusEl.classList.add('hidden'); }

/* ─── Render resultados ─────────────────────────────────────── */
function renderResultados(empresas) {
  resultadosDiv.innerHTML = '';
  if (!empresas.length) {
    resultadosDiv.innerHTML = '<p class="empty-msg">No se encontraron empresas. Probá con otras palabras.</p>';
    return;
  }
  empresas.forEach((e, i) => {
    const card = document.createElement('div');
    card.className = 'empresa-card';
    card.innerHTML = cardHTML(e, 'r', i);
    resultadosDiv.appendChild(card);
  });
}

function cardHTML(e, tipo, index) {
  const match = e.match_score || 0;
  const barra = '█'.repeat(Math.floor(match / 10)) + '░'.repeat(10 - Math.floor(match / 10));
  const matchHTML = match ? '<div class="match-bar"><span>' + barra + '</span> ' + match + '% match</div>' : '';
  const fuenteB = e.fuente ? '<span class="badge-fuente">' + esc(e.fuente) + '</span>' : '';
  const rseB = e.tiene_rse ? '<span class="badge-rse">RSE</span>' : '';
  const cats = [];
  if (e.categoria) cats.push('<span class="tag-nicho">' + esc(e.categoria) + '</span>');
  if (e.nicho) cats.push('<span class="tag-nicho">' + esc(e.nicho) + '</span>');
  const donanStr = e.donan || e.tipo_donacion || '';
  if (donanStr) {
    donanStr.split(', ').forEach(d => {
      if (d) cats.push('<span class="tag-zona">' + esc(d) + '</span>');
    });
  }
  const webBtn = e.sitio_web
    ? '<a class="empresa-web-btn" href="' + esc(e.sitio_web) + '" target="_blank" rel="noopener">&nearr; Visitar sitio</a>'
    : '';

  const infoRows = [];
  if (e.provincia) infoRows.push(
    '<div class="info-row"><span class="info-icon">&#x1F4CD;</span><span class="info-text">' + esc(e.provincia) + '</span></div>');
  if (e.email) infoRows.push(
    '<div class="info-row"><span class="info-icon">&#x2709;</span><span class="info-text email-link" onclick="window.location.href=\'mailto:' + esc(e.email) + '\'">' + esc(e.email) + '</span><button class="btn-icon copy-btn" data-copy="' + esc(e.email) + '" onclick="copiarDato(this)">&#x1F4CB; Copiar</button></div>');
  if (e.telefono) infoRows.push(
    '<div class="info-row"><span class="info-icon">&#x1F4DE;</span><span class="info-text">' + esc(e.telefono) + '</span><button class="btn-icon copy-btn" data-copy="' + esc(e.telefono) + '" onclick="copiarDato(this)">&#x1F4CB; Copiar</button></div>');

  return [
    '<div class="empresa-header">',
      '<div>',
        '<div class="empresa-nombre">' + esc(e.nombre) + fuenteB + '</div>',
        '<div class="empresa-meta">' + webBtn + '</div>',
        matchHTML,
      '</div>',
      '<div style="display:flex;gap:4px;align-items:center">' + rseB + '</div>',
    '</div>',
    '<div class="empresa-tags">' + cats.join('') + '</div>',
    infoRows.length ? '<div class="empresa-info">' + infoRows.join('') + '</div>' : '',
    e.notas ? '<div class="notas-box">' + esc(e.notas) + '</div>' : '',
    '<div class="empresa-body" id="body-' + tipo + '-' + index + '">',
      '<div class="email-placeholder">',
        '<button class="btn-primary btn-sm-btn" onclick="generarEmailCard(\'' + tipo + '\', ' + index + ')">Generar email</button>',
        tipo === 'r' ? '<button class="btn-primary btn-sm-btn btn-guardar" onclick="guardarEmpresa(' + index + ', this)">Guardar empresa</button>' : '',
      '</div>',
    '</div>',
  ].join('');
}

/* ─── Guardar empresa ────────────────────────────────────────── */
async function guardarEmpresa(index, btn) {
  const empresa = _resultados[index];
  if (!empresa) return;

  const data = {
    nicho: _necesidad,
    zona: _zona,
    nombre: empresa.nombre,
    sitio_web: empresa.sitio_web || '',
    email: empresa.email || '',
    tiene_rse: empresa.tiene_rse ? 1 : 0,
    direccion: empresa.direccion || '',
    telefono: empresa.telefono || '',
    contacto_nombre: '',
    fuente: empresa.fuente || '',
    categoria: empresa.categoria || '',
    tipo_donacion: empresa.donan || '',
    notas: empresa.notas || '',
    match_score: empresa.match_score || 0,
  };

  try {
    const res = await fetch('/api/empresas-guardadas', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    const result = await res.json();
    if (res.ok) {
      empresa.guardadaId = result.id;
      btn.textContent = 'Guardada';
      btn.disabled = true;
      btn.classList.add('btn-guardada');
    }
  } catch (err) {
    btn.textContent = 'Error, reintentar';
    setTimeout(() => { btn.textContent = 'Guardar empresa'; }, 2000);
  }
}

/* ─── Generar email on demand ───────────────────────────────── */
async function generarEmailCard(tipo, index) {
  const bodyEl = document.getElementById('body-' + tipo + '-' + index);
  bodyEl.innerHTML = '<div class="status loading" style="margin:0"><span class="spinner"></span>Generando email...</div>';

  try {
    const empresa = getEmpresa(tipo, index);
    const res  = await fetch('/api/generar-email', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ empresa, necesidad: _necesidad, guardadaId: empresa.id || empresa.guardadaId }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Error');

    Object.assign(empresa, data);
    bodyEl.innerHTML = renderEmailArea(tipo, index, empresa);
  } catch (err) {
    bodyEl.innerHTML = '<div class="status error" style="margin:0">' + esc(err.message) + ' <button class="btn-sm btn-danger" style="margin-left:10px" onclick="generarEmailCard(\'' + tipo + '\', ' + index + ')">Reintentar</button></div>';
  }
}

function renderEmailArea(tipo, index, e) {
  const tid = 'cuerpo-' + tipo + '-' + index;
  return [
    '<div class="idea-box"><strong>Idea de referencia</strong><p>' + esc(e.idea_referencia) + '</p></div>',
    '<div class="email-section">',
      '<div class="asunto-row"><label>Asunto</label><button class="btn-icon" data-copy="' + esc(e.asunto) + '" onclick="copiarDato(this)">Cp</button></div>',
      '<div class="asunto-box">' + esc(e.asunto) + '</div>',
      '<label>Cuerpo del email</label>',
      '<textarea class="cuerpo-textarea" id="' + tid + '">' + esc(e.cuerpo) + '</textarea>',
    '</div>',
    '<div class="card-actions">',
      '<button class="btn-sm btn-copy" onclick="copiarEmailCard(\'' + tid + '\', this)">Copiar</button>',
      e.email ? '<button class="btn-sm btn-gmail" onclick="abrirMailto(\'' + tipo + '\', ' + index + ')">Gmail</button>' : '',
      '<button class="btn-sm btn-send" onclick="marcarEnviadoCard(\'' + tipo + '\', ' + index + ', this)">Enviado</button>',
    '</div>',
  ].join('');
}

/* ─── Copiar email ──────────────────────────────────────────── */
function copiarEmailCard(textareaId, btn) {
  const textarea = document.getElementById(textareaId);
  navigator.clipboard.writeText(textarea.value).then(() => {
    const orig = btn.textContent;
    btn.textContent = 'Copiado!';
    setTimeout(() => { btn.textContent = orig; }, 2000);
  });
}

/* ─── Marcar como enviado ───────────────────────────────────── */
async function marcarEnviadoCard(tipo, index, btn) {
  const empresa = getEmpresa(tipo, index);
  const textarea = document.getElementById('cuerpo-' + tipo + '-' + index);
  try {
    await fetch('/api/historial', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        empresa: empresa.nombre,
        nicho: _necesidad,
        sitio_web: empresa.sitio_web || '',
        email_empresa: empresa.email || '',
        asunto: empresa.asunto || '',
        cuerpo: textarea.value,
        idea_referencia: empresa.idea_referencia || '',
        estado: 'enviado',
      }),
    });
    btn.textContent = 'Guardado';
    btn.disabled = true;
  } catch (err) {
    alert('No se pudo guardar: ' + err.message);
  }
}

/* ─── Render guardadas ──────────────────────────────────────── */
function renderGuardadas(empresas) {
  const section = document.getElementById('guardadas-section');
  const grid    = document.getElementById('guardadas-grid');
  if (!empresas.length) { section.classList.add('hidden'); return; }

  document.getElementById('guardadas-nicho-label').textContent = _necesidad + ' - ' + _zona;
  document.getElementById('guardadas-count').textContent = empresas.length + ' empresa' + (empresas.length !== 1 ? 's' : '');

  grid.innerHTML = '';
  empresas.forEach(e => {
    const card = document.createElement('div');
    card.className = 'empresa-card guardada';
    card.id = 'guardada-card-' + e.id;
    // Usar cardHTML con la info completa
    card.innerHTML = cardHTML(e, 'g', e.id);
    // Reemplazar el boton "Generar email" por el contenido que corresponda
    const bodyEl = card.querySelector('.empresa-body');
    if (e.asunto) {
      bodyEl.innerHTML = renderEmailArea('g', e.id, e);
    }
    // Agregar boton eliminar al header
    const header = card.querySelector('.empresa-header');
    const delBtn = document.createElement('button');
    delBtn.className = 'btn-sm btn-danger';
    delBtn.textContent = 'Eliminar';
    delBtn.onclick = function() { eliminarGuardada(e.id); };
    header.appendChild(delBtn);
    grid.appendChild(card);
  });
  section.classList.remove('hidden');
}

async function eliminarGuardada(id) {
  if (!confirm('Eliminar esta empresa de guardadas?')) return;
  await fetch('/api/empresas-guardadas/' + id, { method: 'DELETE' });
  document.getElementById('guardada-card-' + id)?.remove();
}

/* ─── Tab Guardadas ─────────────────────────────────────────── */
async function loadGuardadasTab() {
  _todasGuardadas = await fetch('/api/empresas-guardadas').then(r => r.json());
  renderGuardadasTab(_todasGuardadas);

  document.getElementById('guardadas-tab-filtro').oninput = function () {
    const q = this.value.toLowerCase();
    renderGuardadasTab(_todasGuardadas.filter(e =>
      (e.nombre || '').toLowerCase().includes(q) ||
      (e.nicho  || '').toLowerCase().includes(q) ||
      (e.zona   || '').toLowerCase().includes(q)
    ));
  };
}

function renderGuardadasTab(empresas) {
  const grid  = document.getElementById('guardadas-tab-grid');
  const vacio = document.getElementById('guardadas-tab-vacio');
  const stats = document.getElementById('guardadas-tab-stats');
  const total  = _todasGuardadas.length;
  const nichos = [...new Set(_todasGuardadas.map(e => e.nicho).filter(Boolean))].length;
  stats.innerHTML = '<span class="stat-chip">' + total + ' empresa' + (total !== 1 ? 's' : '') + '</span><span class="stat-chip">' + nichos + ' rubro' + (nichos !== 1 ? 's' : '') + '</span>';

  if (!empresas.length) { grid.innerHTML = ''; vacio.classList.remove('hidden'); return; }
  vacio.classList.add('hidden');
  grid.innerHTML = '';

  empresas.forEach(e => {
    const card = document.createElement('div');
    card.className = 'empresa-card guardada';
    card.id = 'tab-card-' + e.id;
    card.innerHTML = cardHTML(e, 't', e.id);
    const bodyEl = card.querySelector('.empresa-body');
    if (e.asunto) {
      bodyEl.innerHTML = renderEmailArea('t', e.id, e);
    }
    const header = card.querySelector('.empresa-header');
    const delBtn = document.createElement('button');
    delBtn.className = 'btn-sm btn-danger';
    delBtn.textContent = 'Eliminar';
    delBtn.onclick = function() { eliminarGuardadaTab(e.id); };
    header.appendChild(delBtn);
    grid.appendChild(card);
  });
}

async function eliminarGuardadaTab(id) {
  if (!confirm('Eliminar esta empresa de guardadas?')) return;
  await fetch('/api/empresas-guardadas/' + id, { method: 'DELETE' });
  _todasGuardadas = _todasGuardadas.filter(e => e.id !== id);
  document.getElementById('tab-card-' + id)?.remove();
  renderGuardadasTab(_todasGuardadas);
}

/* ─── Historial ─────────────────────────────────────────────── */
let historialData = [];

async function loadHistorial() {
  historialData = await fetch('/api/historial').then(r => r.json());
  renderHistorial(historialData);
  renderStats(historialData);
}

function renderStats(data) {
  const statsEl = document.getElementById('historial-stats');
  const total  = data.length;
  const nichos = [...new Set(data.map(r => r.nicho).filter(Boolean))].length;
  statsEl.innerHTML = '<span class="stat-chip">' + total + ' contacto' + (total !== 1 ? 's' : '') + '</span><span class="stat-chip">' + nichos + ' rubro' + (nichos !== 1 ? 's' : '') + '</span>';
}

function renderHistorial(data) {
  const tbody = document.getElementById('historial-body');
  const vacio = document.getElementById('historial-vacio');
  if (!data.length) { tbody.innerHTML = ''; vacio.classList.remove('hidden'); return; }
  vacio.classList.add('hidden');
  tbody.innerHTML = data.map(r => [
    '<tr>',
      '<td><strong>' + esc(r.empresa) + '</strong></td>',
      '<td>' + esc(r.nicho || '-') + '</td>',
      '<td>' + (r.email_empresa ? '<a href="mailto:' + esc(r.email_empresa) + '">' + esc(r.email_empresa) + '</a>' : '-') + '</td>',
      '<td>' + formatFecha(r.fecha) + '</td>',
      '<td><select class="badge-estado badge-' + (r.estado || 'enviado') + '" onchange="cambiarEstado(' + r.id + ', this.value, this)">',
        '<option value="enviado" ' + (r.estado === 'enviado' ? 'selected' : '') + '>Enviado</option>',
        '<option value="pendiente" ' + (r.estado === 'pendiente' ? 'selected' : '') + '>Pendiente</option>',
        '<option value="sin-resp" ' + (r.estado === 'sin-resp' ? 'selected' : '') + '>Sin respuesta</option>',
      '</select></td>',
      '<td style="display:flex;gap:6px">',
        '<button class="btn-sm btn-view" onclick="verDetalle(' + r.id + ')">Ver</button>',
        '<button class="btn-sm btn-danger" onclick="eliminarHistorial(' + r.id + ')">X</button>',
      '</td>',
    '</tr>',
  ].join('')).join('');
}

document.getElementById('historial-filtro').addEventListener('input', function () {
  const q = this.value.toLowerCase();
  renderHistorial(historialData.filter(r =>
    (r.empresa || '').toLowerCase().includes(q) || (r.nicho || '').toLowerCase().includes(q)
  ));
});

async function cambiarEstado(id, estado, select) {
  select.className = 'badge-estado badge-' + estado;
  await fetch('/api/historial/' + id, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ estado }) });
}

async function eliminarHistorial(id) {
  if (!confirm('Eliminar este contacto?')) return;
  await fetch('/api/historial/' + id, { method: 'DELETE' });
  loadHistorial();
}

function verDetalle(id) {
  const r = historialData.find(x => x.id === id);
  if (!r) return;
  document.getElementById('modal-empresa').textContent = r.empresa;
  document.getElementById('modal-asunto').textContent  = r.asunto || '-';
  document.getElementById('modal-cuerpo').textContent  = r.cuerpo || '-';
  document.getElementById('modal').classList.remove('hidden');
}

document.getElementById('modal-close').addEventListener('click', () => document.getElementById('modal').classList.add('hidden'));
document.getElementById('modal').addEventListener('click', e => { if (e.target === document.getElementById('modal')) document.getElementById('modal').classList.add('hidden'); });

function formatFecha(f) {
  if (!f) return '-';
  const d = new Date(f.replace(' ', 'T'));
  return isNaN(d) ? f : d.toLocaleDateString('es-AR', { day: '2-digit', month: '2-digit', year: 'numeric' });
}

/* ─── Emails de referencia ──────────────────────────────────── */
async function loadRefs() {
  const refs = await fetch('/api/emails-referencia').then(r => r.json());
  const lista = document.getElementById('lista-refs');
  lista.innerHTML = '';
  if (!refs.length) { lista.innerHTML = '<p class="empty-msg">Todavia no guardaste emails de referencia.</p>'; return; }
  refs.forEach(r => {
    const card = document.createElement('div');
    card.className = 'ref-card';
    card.innerHTML = [
      '<div class="ref-card-header">',
        '<span class="ref-titulo">' + esc(r.titulo || 'Sin titulo') + '</span>',
        '<div style="display:flex;align-items:center;gap:8px">',
          '<span class="ref-fecha">' + formatFecha(r.fecha) + '</span>',
          '<button class="btn-sm btn-danger" onclick="eliminarRef(' + r.id + ')">X</button>',
        '</div>',
      '</div>',
      '<pre class="ref-preview">' + esc(r.contenido) + '</pre>',
    ].join('');
    lista.appendChild(card);
  });
}

document.getElementById('btn-guardar-ref').addEventListener('click', async () => {
  const titulo = document.getElementById('ref-titulo').value.trim();
  const contenido = document.getElementById('ref-contenido').value.trim();
  if (!contenido) return alert('El contenido del email es obligatorio.');
  await fetch('/api/emails-referencia', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ titulo, contenido }),
  });
  document.getElementById('ref-titulo').value = '';
  document.getElementById('ref-contenido').value = '';
  loadRefs();
});

async function eliminarRef(id) {
  if (!confirm('Eliminar este email de referencia?')) return;
  await fetch('/api/emails-referencia/' + id, { method: 'DELETE' });
  loadRefs();
}

/* ─── Helpers ───────────────────────────────────────────────── */
function getEmpresa(tipo, index) {
  if (tipo === 'r') return _resultados[index];
  if (tipo === 'g') return _guardadas.find(e => e.id === index);
  if (tipo === 't') return _todasGuardadas.find(e => e.id === index);
  return null;
}

function copiarDato(btn) {
  navigator.clipboard.writeText(btn.dataset.copy || '').then(() => {
    const orig = btn.textContent;
    btn.textContent = 'OK';
    setTimeout(() => { btn.textContent = orig; }, 1500);
  });
}

function abrirMailto(tipo, index) {
  const e = getEmpresa(tipo, index);
  if (!e?.email) return;
  const body = document.getElementById('cuerpo-' + tipo + '-' + index)?.value || '';
  window.open('mailto:' + e.email + '?subject=' + encodeURIComponent(e.asunto || '') + '&body=' + encodeURIComponent(body));
}

function esc(str) {
  if (str == null) return '';
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
