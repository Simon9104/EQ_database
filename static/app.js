'use strict';

// ── API ─────────────────────────────────────────────────────────────────────
const API = {
  async _handle(r) {
    if (r.status === 401) { window.location.href = '/login'; return null; }
    return r.json();
  },
  async get(url) { return this._handle(await fetch(url)); },
  async post(url, data) {
    return this._handle(await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }));
  },
  async put(url, data) {
    return this._handle(await fetch(url, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }));
  },
  async del(url) { return this._handle(await fetch(url, { method: 'DELETE' })); },
};

// ── Utilities ────────────────────────────────────────────────────────────────
function fmt_eur(v) {
  if (v == null || v === '') return '—';
  return new Intl.NumberFormat('sk-SK', { style: 'currency', currency: 'EUR' }).format(v);
}
function fmt_date(v) {
  if (!v) return '—';
  const d = new Date(v);
  if (isNaN(d)) return v;
  return d.toLocaleDateString('sk-SK');
}
function esc(s) {
  if (s == null) return '';
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function statusBadge(s) {
  if (!s) return '';
  const map = {
    'Očakávaný': 'ocakavany', 'Prebiehajúci': 'prebiehajuci', 'Fakturovať': 'fakturovat',
    'Ukončený': 'ukonceny', 'Stornovaný': 'stornovany', 'Odložený': 'odlozeny',
    'grafika': 'grafika', 'výroba': 'vyroba', 'naceniť': 'nacenit',
    'hotovo': 'hotovo', 'fakturovať': 'fakturovat2', 'BD': 'bd',
  };
  const cls = map[s] || 'default';
  return `<span class="badge badge-${cls}">${esc(s)}</span>`;
}
function el(tag, attrs, ...children) {
  const e = document.createElement(tag);
  Object.entries(attrs || {}).forEach(([k, v]) => {
    if (k === 'class') e.className = v;
    else if (k === 'style') e.style.cssText = v;
    else if (k.startsWith('on')) e.addEventListener(k.slice(2), v);
    else e.setAttribute(k, v);
  });
  children.forEach(c => {
    if (typeof c === 'string') e.insertAdjacentHTML('beforeend', c);
    else if (c) e.appendChild(c);
  });
  return e;
}

// ── Toast ────────────────────────────────────────────────────────────────────
function showToast(msg, type = 'info') {
  const c = document.getElementById('toast-container');
  if (!c) return;
  const t = document.createElement('div');
  t.className = `toast toast-${type}`;
  t.textContent = msg;
  c.appendChild(t);
  setTimeout(() => t.remove(), 3000);
}

// ── State ────────────────────────────────────────────────────────────────────
const State = {
  view: 'dashboard',
  lookups: {},
  projects: { filters: {}, data: [] },
  items: { filters: {}, data: [] },
  invoices: { filters: {}, data: [] },
  customers: { filters: {}, data: [] },
  credits: { filters: {}, data: [] },
  imposition: { filters: {}, data: [] },
  firmy: { filters: {}, data: [] },
  editId: null,
  editType: null,
};

// ── App ──────────────────────────────────────────────────────────────────────
const App = {
  async init() {
    // Load current user from auth
    const me = await API.get('/api/auth/me');
    if (!me) return; // redirected to login
    State.currentUser = me;
    const cuEl = document.getElementById('current-user');
    if (cuEl) {
      cuEl.innerHTML = `<span style="cursor:pointer" title="Odhlásiť sa" onclick="App.logout()">👤 ${esc(me.plne_meno || me.username)}</span>`;
    }

    State.lookups = await API.get('/api/lookups');

    document.querySelectorAll('#sidebar nav a').forEach(a => {
      a.addEventListener('click', () => {
        document.querySelectorAll('#sidebar nav a').forEach(x => x.classList.remove('active'));
        a.classList.add('active');
        this.navigate(a.dataset.view);
      });
    });

    // Global search
    const gs = document.getElementById('global-search');
    if (gs) {
      gs.addEventListener('input', e => {
        const q = e.target.value.trim();
        if (q.length > 1) this.globalSearch(q);
      });
      gs.addEventListener('keydown', e => { if (e.key === 'Escape') { gs.value = ''; gs.blur(); } });
    }

    // Keyboard shortcuts
    document.addEventListener('keydown', e => {
      const tag = document.activeElement.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
      if (e.key === '/') { e.preventDefault(); gs?.focus(); }
      if (e.key === 'n') App.openAdd();
      if (e.key === 'Escape') { App.closeModal(); App.closeDetail(); }
    });

    this.navigate('dashboard');
  },

  navigate(view) {
    State.view = view;
    this.closeDetail();
    const titles = {
      dashboard: 'Dashboard', projects: 'Projekty', items: 'Položky', invoices: 'Faktúry',
      firmy: 'Firmy', customers: 'Zákazníci', credits: 'Bankové pohyby',
      imposition: 'Vyradovanie', iqk: 'IQK – Knižná kultúra', settings: 'Nastavenia',
    };
    document.getElementById('topbar-title').textContent = titles[view] || view;
    const noAdd = ['dashboard', 'settings'];
    document.getElementById('add-btn').style.display = noAdd.includes(view) ? 'none' : '';
    const showExport = ['projects', 'invoices'].includes(view);
    document.getElementById('export-btn').style.display = showExport ? '' : 'none';

    document.querySelectorAll('#sidebar nav a').forEach(a => {
      a.classList.toggle('active', a.dataset.view === view);
    });

    Views[view]?.render();
  },

  exportCurrent() {
    if (State.view === 'projects') window.open('/api/export/projects', '_blank');
    else if (State.view === 'invoices') window.open('/api/export/invoices', '_blank');
  },

  async globalSearch(q) {
    const [projs, invs] = await Promise.all([
      API.get(`/api/projects?search=${encodeURIComponent(q)}&limit=5`),
      API.get(`/api/invoices?search=${encodeURIComponent(q)}&limit=5`),
    ]);
    // Show results as quick suggestions below search bar (simple approach: navigate to view with filter)
    if (projs.length) { this.navigate('projects'); State.projects.filters.search = q; Views.projects.render(); }
    else if (invs.length) { this.navigate('invoices'); }
  },

  openAdd() { Views[State.view]?.openAdd?.(); },
  closeModal() {
    document.getElementById('modal-overlay').style.display = 'none';
    State.editId = null;
    State.editType = null;
  },
  openModal(title, bodyHtml, editId = null, showDelete = false) {
    document.getElementById('modal-title').textContent = title;
    document.getElementById('modal-body').innerHTML = bodyHtml;
    document.getElementById('modal-delete-btn').style.display = showDelete ? '' : 'none';
    State.editId = editId;
    State.editType = State.view;
    document.getElementById('modal-overlay').style.display = 'flex';
  },
  async saveRecord() { Views[State.view]?.save?.(); },
  async deleteRecord() { Views[State.view]?.delete?.(); },
  closeDetail() {
    document.getElementById('detail-panel').classList.remove('open');
  },
  openDetail(title, bodyHtml, editFn) {
    document.getElementById('detail-title').textContent = title;
    document.getElementById('detail-body').innerHTML = bodyHtml;
    document.getElementById('detail-edit-btn').onclick = editFn || (() => {});
    document.getElementById('detail-panel').classList.add('open');
  },

  async logout() {
    if (!confirm('Odhlásiť sa?')) return;
    await fetch('/api/auth/logout', { method: 'POST' });
    window.location.href = '/login';
  },
};

// ── Views ────────────────────────────────────────────────────────────────────
const Views = {};

// ─── DASHBOARD ───────────────────────────────────────────────────────────────
Views.dashboard = {
  async render() {
    const cont = document.getElementById('content');
    cont.innerHTML = '<div class="loading">Načítavam...</div>';
    let d;
    try { d = await API.get('/api/dashboard'); } catch(e) { cont.innerHTML = '<div class="empty">Chyba načítania dashboardu</div>'; return; }

    const stavMap = {};
    (d.projekty_podla_stavu || []).forEach(r => { stavMap[r.stav] = r.pocet; });
    const running = stavMap['Prebiehajúci'] || 0;
    const toInvoice = stavMap['Fakturovať'] || 0;

    cont.innerHTML = `
      <div class="kpi-grid">
        <div class="kpi-card">
          <div class="kpi-value">${d.projekty_celkom ?? 0}</div>
          <div class="kpi-label">Projektov celkom</div>
        </div>
        <div class="kpi-card kpi-warning">
          <div class="kpi-value">${running}</div>
          <div class="kpi-label">Prebiehajúce</div>
        </div>
        <div class="kpi-card kpi-success">
          <div class="kpi-value">${toInvoice}</div>
          <div class="kpi-label">Na fakturáciu</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-value">${fmt_eur(d.faktury_zostava)}</div>
          <div class="kpi-label">Nezaplatené faktúry</div>
        </div>
        <div class="kpi-card ${(d.faktury_po_splatnosti||0)>0?'kpi-danger':''}">
          <div class="kpi-value">${d.faktury_po_splatnosti ?? 0}</div>
          <div class="kpi-label">Po splatnosti</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-value">${d.faktury_celkom ?? 0}</div>
          <div class="kpi-label">Faktúr celkom</div>
        </div>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
        <div class="dashboard-section">
          <h3>Projekty podľa stavu</h3>
          ${(d.projekty_podla_stavu||[]).sort((a,b)=>b.pocet-a.pocet).map(r => `
            <div class="stav-row">
              <span>${statusBadge(r.stav)}</span>
              <span class="stav-count">${r.pocet}</span>
            </div>`).join('')}
        </div>
        <div class="dashboard-section">
          <h3>Rýchle akcie</h3>
          <div style="display:flex;flex-direction:column;gap:8px;margin-top:4px">
            <button class="btn btn-secondary" onclick="App.navigate('projects')">📁 Všetky projekty</button>
            <button class="btn btn-secondary" onclick="App.navigate('projects');State.projects.filters.stav='Prebiehajúci';Views.projects.render()">▶️ Prebiehajúce projekty</button>
            <button class="btn btn-secondary" onclick="App.navigate('projects');State.projects.filters.stav='Fakturovať';Views.projects.render()">🧾 Na fakturáciu</button>
            <button class="btn btn-secondary" onclick="App.navigate('invoices')">💰 Faktúry</button>
            <button class="btn btn-primary" onclick="App.navigate('projects');Views.projects.openAdd()">+ Nový projekt</button>
          </div>
        </div>
      </div>`;
  },
};

// ─── FIRMY ───────────────────────────────────────────────────────────────────
Views.firmy = {
  async render() {
    const cont = document.getElementById('content');
    cont.innerHTML = `
    <div class="filter-bar">
      <input type="search" id="f-firmy-search" placeholder="Hľadať firmu, email, IČO..." value="${esc(State.firmy.filters.search||'')}">
      <label class="checkbox-item"><input type="checkbox" id="f-firmy-odberatel" ${State.firmy.filters.odberatel?'checked':''}> Odberatelia</label>
      <label class="checkbox-item"><input type="checkbox" id="f-firmy-dodavatel" ${State.firmy.filters.dodavatel?'checked':''}> Dodávatelia</label>
      <button class="btn btn-secondary btn-sm" onclick="Views.firmy.clearFilters()">Zrušiť filtre</button>
    </div>
    <div id="firmy-table-wrap"><div class="loading">Načítavam...</div></div>`;
    document.getElementById('f-firmy-search')?.addEventListener('input', e => { State.firmy.filters.search = e.target.value; this.load(); });
    document.getElementById('f-firmy-odberatel')?.addEventListener('change', e => { State.firmy.filters.odberatel = e.target.checked || undefined; this.load(); });
    document.getElementById('f-firmy-dodavatel')?.addEventListener('change', e => { State.firmy.filters.dodavatel = e.target.checked || undefined; this.load(); });
    await this.load();
  },

  clearFilters() { State.firmy.filters = {}; this.render(); },

  async load() {
    const f = State.firmy.filters;
    const params = new URLSearchParams({ limit: 300 });
    if (f.search) params.set('search', f.search);
    if (f.odberatel) params.set('odberatel', 'true');
    if (f.dodavatel) params.set('dodavatel', 'true');
    const data = await API.get('/api/firmy?' + params);
    State.firmy.data = data;
    this.renderTable(data);
  },

  renderTable(data) {
    const wrap = document.getElementById('firmy-table-wrap');
    if (!wrap) return;
    if (!data.length) { wrap.innerHTML = '<div class="empty">Žiadne firmy</div>'; return; }
    wrap.innerHTML = `<div class="table-wrap"><table>
      <thead><tr><th>ID</th><th>Názov</th><th>IČO</th><th>IČ DPH</th><th>Telefón</th><th>Email</th><th>Mesto</th><th>Typ</th></tr></thead>
      <tbody>${data.map(f => `<tr onclick="Views.firmy.openDetail(${f.id})">
        <td class="mono">${f.id}</td>
        <td class="td-truncate" style="max-width:200px"><strong>${esc(f.nazov||'')}</strong>${f.skratka?` <span class="tag">${esc(f.skratka)}</span>`:''}</td>
        <td class="mono">${esc(f.ico||'')}</td>
        <td class="mono">${esc(f.ic_dph||'')}</td>
        <td>${esc(f.telefon||'')}</td>
        <td>${f.email?`<a href="mailto:${esc(f.email)}" onclick="event.stopPropagation()">${esc(f.email)}</a>`:''}</td>
        <td>${esc(f.mesto||'')}</td>
        <td>${f.odberatel?'<span class="badge badge-odberatel">Odb.</span>':''} ${f.dodavatel?'<span class="badge badge-dodavatel">Dod.</span>':''} ${f.agentura?'<span class="badge badge-agentura">Ag.</span>':''}</td>
      </tr>`).join('')}
      </tbody></table>
      <div class="pagination"><span>${data.length} firiem</span></div>
    </div>`;
  },

  async openDetail(id) {
    const f = await API.get('/api/firmy/' + id);
    if (!f) return;
    const kontakty = await API.get('/api/firmy/' + id + '/kontakty');
    const kontHtml = kontakty.length ? `<div class="table-wrap"><table>
      <thead><tr><th>Meno</th><th>Funkcia</th><th>Mobil</th><th>Email</th></tr></thead>
      <tbody>${kontakty.map(k => `<tr>
        <td>${esc((k.priezvisko||'')+' '+(k.meno||''))}</td>
        <td>${esc(k.funkcia||'')}</td>
        <td>${esc(k.mobil1||'')}</td>
        <td>${k.email?`<a href="mailto:${esc(k.email)}">${esc(k.email)}</a>`:''}</td>
      </tr>`).join('')}</tbody></table></div>` : '<div class="empty" style="padding:10px">Žiadne kontakty</div>';

    const body = `
      <div class="tabs">
        <span class="tab active" onclick="switchTab(this,'fd-basic')">Základné</span>
        <span class="tab" onclick="switchTab(this,'fd-fakturacia')">Fakturácia</span>
        <span class="tab" onclick="switchTab(this,'fd-kontakty')">Kontakty (${kontakty.length})</span>
      </div>
      <div id="fd-basic">
        <div class="detail-grid">
          ${dfield('ID', f.id)} ${dfield('Skratka', f.skratka)}
          ${dfield('Názov', f.nazov, 'full')}
          ${dfield('Adresa', f.adresa, 'full')}
          ${dfield('PSČ', f.psc)} ${dfield('Mesto', f.mesto)}
          ${dfield('Štát', f.stat)} ${dfield('Webová stránka', f.webova_stranka)}
          ${dfield('Telefón', f.telefon)} ${dfield('Email', f.email)}
          ${dfield('Fax', f.fax)}
        </div>
        <div class="detail-section"><h4>Nastavenia</h4>
          <div class="checkbox-row">
            ${pflag('Odberateľ', f.odberatel)} ${pflag('Dodávateľ', f.dodavatel)}
            ${pflag('Agentúra', f.agentura)} ${pflag('Platca DPH', f.platca_dph)}
          </div>
        </div>
        ${f.poznamka ? `<div class="detail-section"><h4>Poznámka</h4><p style="font-size:13px">${esc(f.poznamka)}</p></div>` : ''}
      </div>
      <div id="fd-fakturacia" style="display:none">
        <div class="detail-grid">
          ${dfield('IČO', f.ico)} ${dfield('IČ DPH', f.ic_dph)}
          ${dfield('DIČ', f.dic)} ${dfield('Číslo účtu', f.cislo_uctu)}
        </div>
      </div>
      <div id="fd-kontakty" style="display:none">${kontHtml}
        <button class="btn btn-primary btn-sm" style="margin-top:10px" onclick="Views.firmy.openAddKontakt(${f.id})">+ Pridať kontakt</button>
      </div>`;
    App.openDetail(f.nazov || 'Firma', body, () => this.openEdit(f.id));
  },

  openAdd() { this.openForm(null); },
  async openEdit(id) { const f = await API.get('/api/firmy/' + id); if (f) this.openForm(f); },

  openForm(f) {
    const v = k => esc(f?.[k] ?? '');
    const chk = k => f?.[k] ? 'checked' : '';
    const body = `
    <div class="tabs">
      <span class="tab active" onclick="switchTab(this,'ff-basic')">Základné</span>
      <span class="tab" onclick="switchTab(this,'ff-fakturacia')">Fakturácia</span>
      <span class="tab" onclick="switchTab(this,'ff-nastavenia')">Nastavenia</span>
    </div>
    <div id="ff-basic">
      <div class="form-grid">
        <div class="field form-full"><label>Názov firmy</label><input id="ff-nazov" value="${v('nazov')}"></div>
        <div class="field"><label>Skratka</label><input id="ff-skratka" value="${v('skratka')}"></div>
        <div class="field"><label>Webová stránka</label><input id="ff-webova_stranka" value="${v('webova_stranka')}"></div>
        <div class="field form-full"><label>Adresa</label><input id="ff-adresa" value="${v('adresa')}"></div>
        <div class="field"><label>PSČ</label><input id="ff-psc" value="${v('psc')}"></div>
        <div class="field"><label>Mesto</label><input id="ff-mesto" value="${v('mesto')}"></div>
        <div class="field"><label>Štát</label><input id="ff-stat" value="${v('stat')}"></div>
        <div class="field"><label>Telefón</label><input id="ff-telefon" value="${v('telefon')}"></div>
        <div class="field"><label>Email</label><input type="email" id="ff-email" value="${v('email')}"></div>
        <div class="field"><label>Fax</label><input id="ff-fax" value="${v('fax')}"></div>
        <div class="field form-full"><label>Poznámka</label><textarea id="ff-poznamka">${v('poznamka')}</textarea></div>
      </div>
    </div>
    <div id="ff-fakturacia" style="display:none">
      <div class="form-grid">
        <div class="field"><label>IČO</label><input id="ff-ico" value="${v('ico')}"></div>
        <div class="field"><label>IČ DPH</label><input id="ff-ic_dph" value="${v('ic_dph')}"></div>
        <div class="field"><label>DIČ</label><input id="ff-dic" value="${v('dic')}"></div>
        <div class="field form-full"><label>Číslo účtu / IBAN</label><input id="ff-cislo_uctu" value="${v('cislo_uctu')}"></div>
      </div>
    </div>
    <div id="ff-nastavenia" style="display:none">
      <div class="checkbox-row" style="flex-direction:column;align-items:flex-start;gap:10px">
        ${cbox('ff-odberatel','Odberateľ',chk('odberatel'))}
        ${cbox('ff-dodavatel','Dodávateľ',chk('dodavatel'))}
        ${cbox('ff-agentura','Agentúra',chk('agentura'))}
        ${cbox('ff-platca_dph','Platca DPH',chk('platca_dph'))}
      </div>
    </div>`;
    App.openModal(f ? `Upraviť firmu: ${f.nazov}` : 'Nová firma', body, f?.id, !!f);
  },

  async save() {
    const text = ['nazov','skratka','adresa','mesto','psc','stat','telefon','email','fax','webova_stranka','ico','ic_dph','dic','cislo_uctu','poznamka'];
    const bools = ['odberatel','dodavatel','agentura','platca_dph'];
    const data = {};
    text.forEach(f => { const e = document.getElementById('ff-'+f); if (e) data[f] = e.value || null; });
    bools.forEach(f => { data[f] = !!document.getElementById('ff-'+f)?.checked; });
    try {
      if (State.editId) await API.put('/api/firmy/' + State.editId, data);
      else await API.post('/api/firmy', data);
      showToast('Firma uložená', 'success');
    } catch(e) { showToast('Chyba ukladania', 'error'); return; }
    App.closeModal();
    App.closeDetail();
    await this.load();
  },

  async delete() {
    if (!confirm('Odstraniť firmu?')) return;
    await API.del('/api/firmy/' + State.editId);
    showToast('Firma odstránená', 'info');
    App.closeModal();
    App.closeDetail();
    await this.load();
  },

  openAddKontakt(firmaId) {
    const body = `<div class="form-grid">
      <div class="field"><label>Priezvisko</label><input id="fk-priezvisko"></div>
      <div class="field"><label>Meno</label><input id="fk-meno"></div>
      <div class="field"><label>Funkcia</label><input id="fk-funkcia"></div>
      <div class="field"><label>Oddelenie</label><input id="fk-oddelenie"></div>
      <div class="field"><label>Telefón (práca)</label><input id="fk-telefon_praca"></div>
      <div class="field"><label>Mobil 1</label><input id="fk-mobil1"></div>
      <div class="field"><label>Mobil 2</label><input id="fk-mobil2"></div>
      <div class="field"><label>Email</label><input type="email" id="fk-email"></div>
      <div class="field form-full"><label>Poznámky</label><textarea id="fk-poznamky"></textarea></div>
    </div>`;
    App.openModal('Nový kontakt', body, null, false);
    // Override save for kontakt
    document.getElementById('modal-save-btn').onclick = async () => {
      const fields = ['priezvisko','meno','funkcia','oddelenie','telefon_praca','mobil1','mobil2','email','poznamky'];
      const data = { firma_id: firmaId };
      fields.forEach(f => { data[f] = document.getElementById('fk-'+f)?.value || null; });
      await API.post('/api/kontakty', data);
      showToast('Kontakt pridaný', 'success');
      App.closeModal();
      this.openDetail(firmaId);
    };
  },
};

// ─── PROJECTS ────────────────────────────────────────────────────────────────
Views.projects = {
  chips: {},

  async render() {
    const cont = document.getElementById('content');
    cont.innerHTML = this.filterBar();
    cont.insertAdjacentHTML('beforeend', '<div id="proj-table-wrap"><div class="loading">Načítavam...</div></div>');
    this.bindFilters();
    await this.load();
  },

  filterBar() {
    const stavy = State.lookups.stavy_projektov || [];
    const opts = stavy.map(s => `<option value="${esc(s.nazov)}">${esc(s.nazov)}</option>`).join('');
    const managers = [...new Set((State.projects.data || []).map(p => p.manazer).filter(Boolean))];
    const mgOpts = managers.map(m => `<option value="${esc(m)}">${esc(m)}</option>`).join('');
    return `
    <div class="filter-bar">
      <input type="search" id="f-search" placeholder="Hľadať projekt / firmu..." value="${esc(State.projects.filters.search||'')}">
      <select id="f-stav"><option value="">Všetky stavy</option>${opts}</select>
      <select id="f-manazer"><option value="">Všetci manažéri</option>${mgOpts}</select>
      <span style="color:#ccc">|</span>
      ${['kreditny','zberny','kniha','cp','oznaceny','cakajuci','bezny','hotovo','expedovat','sledovany'].map(k =>
        `<span class="chip ${State.projects.filters[k]?'active':''}" data-chip="${k}">${chipLabel(k)}</span>`
      ).join('')}
      <button class="btn btn-secondary btn-sm" onclick="Views.projects.clearFilters()">Zrušiť filtre</button>
    </div>`;
  },

  bindFilters() {
    document.getElementById('f-search')?.addEventListener('input', e => { State.projects.filters.search = e.target.value; this.load(); });
    document.getElementById('f-stav')?.addEventListener('change', e => { State.projects.filters.stav = e.target.value; this.load(); });
    document.getElementById('f-manazer')?.addEventListener('change', e => { State.projects.filters.manazer = e.target.value; this.load(); });
    document.querySelectorAll('.chip[data-chip]').forEach(chip => {
      chip.addEventListener('click', () => {
        const k = chip.dataset.chip;
        State.projects.filters[k] = !State.projects.filters[k];
        chip.classList.toggle('active');
        this.load();
      });
    });
  },

  clearFilters() {
    State.projects.filters = {};
    this.render();
  },

  async load() {
    const f = State.projects.filters;
    const params = new URLSearchParams({ limit: 300 });
    if (f.search) params.set('search', f.search);
    if (f.stav) params.set('stav', f.stav);
    if (f.manazer) params.set('manazer', f.manazer);
    ['kreditny','zberny','kniha','cp','oznaceny','cakajuci','bezny','hotovo','expedovat','sledovany'].forEach(k => {
      if (f[k]) params.set(k, 'true');
    });
    const data = await API.get('/api/projects?' + params);
    State.projects.data = data;
    this.renderTable(data);
  },

  renderTable(data) {
    const wrap = document.getElementById('proj-table-wrap');
    if (!wrap) return;
    if (!data.length) { wrap.innerHTML = '<div class="empty">Žiadne projekty</div>'; return; }
    wrap.innerHTML = `
    <div class="table-wrap">
    <table>
      <thead><tr>
        <th>ID</th><th>Názov projektu</th><th>Firma</th><th>Manažér</th>
        <th>Stav</th><th>Prijaté</th><th>Termín</th>
        <th>Cena s DPH</th><th>Zisk</th><th>Príznaky</th>
      </tr></thead>
      <tbody>
      ${data.map(p => `
        <tr data-id="${p.id}" onclick="Views.projects.openDetail(${p.id})">
          <td class="mono">${p.id}</td>
          <td class="td-truncate" style="max-width:220px">${esc(p.nazov_projektu||'')}</td>
          <td class="td-truncate">${esc(p.nazov_firmy||'')}</td>
          <td>${esc(p.manazer||'')}</td>
          <td>${statusBadge(p.stav)}</td>
          <td>${fmt_date(p.prijate)}</td>
          <td>${fmt_date(p.termin_odovzdania)}</td>
          <td class="cur">${fmt_eur(p.cena_s_dph)}</td>
          <td class="cur ${(p.zisk||0)>=0?'cur-pos':'cur-neg'}">${fmt_eur(p.zisk)}</td>
          <td>${projFlags(p)}</td>
        </tr>`).join('')}
      </tbody>
    </table>
    <div class="pagination"><span>${data.length} projektov</span></div>
    </div>`;
  },

  async openDetail(id) {
    const p = await API.get('/api/projects/' + id);
    const items = await API.get('/api/projects/' + id + '/items');
    const body = `
      <div class="tabs">
        <span class="tab active" onclick="switchTab(this,'tab-basic')">Základné</span>
        <span class="tab" onclick="switchTab(this,'tab-items')">Položky (${items.length})</span>
        <span class="tab" onclick="Views.projects.loadNaklady(${id},this)">Náklady</span>
        <span class="tab" onclick="switchTab(this,'tab-notes')">Poznámky</span>
        <span class="tab" onclick="switchTab(this,'tab-log')">Log</span>
      </div>
      <div id="tab-basic">
        <div class="detail-grid">
          ${dfield('ID',p.id)} ${dfield('Stav',statusBadge(p.stav))}
          ${dfield('Firma',p.nazov_firmy)} ${dfield('Kontakt',p.priezvisko_meno)}
          ${dfield('Manažér',p.manazer)} ${dfield('Kategória',p.kategoria)}
          ${dfield('Prijaté',fmt_date(p.prijate))} ${dfield('Termín',fmt_date(p.termin_odovzdania))}
          ${dfield('Č. objednávky',p.cislo_objednavky)} ${dfield('Č. CP',p.cislo_cp)}
        </div>
        <div class="detail-section"><h4>Financie</h4><div class="detail-grid">
          ${dfield('Cena bez DPH',fmt_eur(p.cena_bez_dph))}
          ${dfield('DPH',fmt_eur(p.dph_ceny))}
          ${dfield('Cena s DPH',fmt_eur(p.cena_s_dph))}
          ${dfield('Náklady',fmt_eur(p.naklady))}
          ${dfield('Zisk',`<span class="${(p.zisk||0)>=0?'cur-pos':'cur-neg'}">${fmt_eur(p.zisk)}</span>`)}
          ${dfield('Kredit',fmt_eur(p.kredit))}
        </div></div>
        <div class="detail-section"><h4>Príznaky</h4>
          <div class="checkbox-row">
            ${pflag('Kreditný',p.projekt_kreditny)} ${pflag('Zberný',p.projekt_zberny)}
            ${pflag('Kniha',p.projekt_kniha)} ${pflag('CP',p.projekt_cp)}
            ${pflag('Označený',p.projekt_oznaceny)} ${pflag('Sledovaný',p.projekt_sledovany)}
            ${pflag('Čakajúci',p.projekt_cakajuci)} ${pflag('Bežný',p.projekt_bezny)}
            ${pflag('Hotovo',p.projekt_hotovo)} ${pflag('Fakturovaný',p.projekt_fakturovany)}
            ${pflag('Uhradený',p.projekt_uhradeny)} ${pflag('Expedovať',p.projekt_expedovat)}
          </div>
        </div>
        ${p.strucna_specifikacia ? `<div class="detail-section"><h4>Stručná špecifikácia</h4><p style="font-size:13px">${esc(p.strucna_specifikacia)}</p></div>` : ''}
      </div>
      <div id="tab-items" style="display:none">
        ${items.length ? itemsTable(items) : '<div class="empty">Žiadne položky</div>'}
        <button class="btn btn-primary btn-sm" style="margin-top:10px" onclick="Views.items.openAddForProject(${p.id})">+ Pridať položku</button>
      </div>
      <div id="tab-naklady" style="display:none"><div class="loading">Načítavam...</div></div>
      <div id="tab-notes" style="display:none">
        ${dfield('Poznámky',p.poznamky,'full')}
        ${dfield('Poznámky ZL',p.poznamky_zl,'full')}
        ${dfield('Poznámky 1',p.poznamky_1,'full')}
        ${dfield('Poznámka CP',p.poznamka_cp,'full')}
        ${dfield('Folder zákazky',p.folder_zakazky,'full')}
        ${dfield('Folder CP',p.folder_cp,'full')}
      </div>
      <div id="tab-log" style="display:none">
        <pre style="font-size:12px;white-space:pre-wrap;background:#f8fafc;padding:12px;border-radius:6px">${esc(p.projekt_log||'(prázdny log)')}</pre>
      </div>
    `;
    App.openDetail(`#${p.id} – ${p.nazov_projektu||''}`, body, () => this.openEdit(p.id));
  },

  openAdd() { this.openForm(null); },
  async openEdit(id) {
    const p = await API.get('/api/projects/' + id);
    this.openForm(p);
  },

  openForm(p) {
    const stavy = State.lookups.stavy_projektov || [];
    const stavOpts = stavy.map(s => `<option value="${esc(s.nazov)}" ${p?.stav===s.nazov?'selected':''}>${esc(s.nazov)}</option>`).join('');
    const v = k => esc(p?.[k] ?? '');
    const chk = k => p?.[k] ? 'checked' : '';
    const body = `
    <div class="tabs">
      <span class="tab active" onclick="switchTab(this,'pf-basic')">Základné</span>
      <span class="tab" onclick="switchTab(this,'pf-finance')">Financie</span>
      <span class="tab" onclick="switchTab(this,'pf-flags')">Príznaky</span>
      <span class="tab" onclick="switchTab(this,'pf-notes')">Poznámky</span>
    </div>
    <div id="pf-basic">
      <div class="form-grid">
        <div class="field form-full"><label>Názov projektu</label><input id="f-nazov_projektu" value="${v('nazov_projektu')}"></div>
        <div class="field"><label>Firma</label><input id="f-nazov_firmy" value="${v('nazov_firmy')}"></div>
        <div class="field"><label>Kontakt</label><input id="f-priezvisko_meno" value="${v('priezvisko_meno')}"></div>
        <div class="field"><label>Manažér</label><input id="f-manazer" value="${v('manazer')}"></div>
        <div class="field"><label>Stav</label><select id="f-stav"><option value="">—</option>${stavOpts}</select></div>
        <div class="field"><label>Kategória</label><input id="f-kategoria" value="${v('kategoria')}"></div>
        <div class="field"><label>Priorita</label><input id="f-priorita" value="${v('priorita')}"></div>
        <div class="field"><label>Prijaté</label><input type="date" id="f-prijate" value="${isoDate(p?.prijate)}"></div>
        <div class="field"><label>Termín odovzdania</label><input type="date" id="f-termin_odovzdania" value="${isoDate(p?.termin_odovzdania)}"></div>
        <div class="field"><label>Č. objednávky</label><input id="f-cislo_objednavky" value="${v('cislo_objednavky')}"></div>
        <div class="field"><label>Č. CP</label><input id="f-cislo_cp" value="${v('cislo_cp')}"></div>
        <div class="field"><label>Stručná špecifikácia</label><input id="f-strucna_specifikacia" value="${v('strucna_specifikacia')}"></div>
        <div class="field"><label>Folder zákazky</label><input id="f-folder_zakazky" value="${v('folder_zakazky')}"></div>
        <div class="field"><label>Folder CP</label><input id="f-folder_cp" value="${v('folder_cp')}"></div>
        <div class="field"><label>Zúčastnení</label><input id="f-zucastneni" value="${v('zucastneni')}"></div>
        <div class="field"><label>Prijal</label><input id="f-prijal" value="${v('prijal')}"></div>
        <div class="field"><label>Zostáva</label><input id="f-zostava" value="${v('zostava')}"></div>
        <div class="field"><label>Dát. prijatia obj.</label><input type="date" id="f-datum_prijatia_objednavky" value="${isoDate(p?.datum_prijatia_objednavky)}"></div>
        <div class="field"><label>Dát. na objednávke</label><input type="date" id="f-datum_na_objednavke" value="${isoDate(p?.datum_na_objednavke)}"></div>
        <div class="field"><label>Termín expedície</label><input type="date" id="f-projekt_expedovat_datum" value="${isoDate(p?.projekt_expedovat_datum)}"></div>
        <div class="field"><label>Podobný projekt</label><input id="f-podobny_projekt" value="${v('podobny_projekt')}"></div>
        <div class="field"><label>F1</label><input id="f-f1" value="${v('f1')}"></div>
        <div class="field"><label>F2</label><input id="f-f2" value="${v('f2')}"></div>
        <div class="field"><label>F3</label><input id="f-f3" value="${v('f3')}"></div>
        <div class="field"><label>F4</label><input id="f-f4" value="${v('f4')}"></div>
      </div>
    </div>
    <div id="pf-finance" style="display:none">
      <div class="form-grid">
        <div class="field"><label>Cena bez DPH</label><input type="number" step="0.01" id="f-cena_bez_dph" value="${p?.cena_bez_dph??''}"></div>
        <div class="field"><label>DPH</label><input type="number" step="0.01" id="f-dph_ceny" value="${p?.dph_ceny??''}"></div>
        <div class="field"><label>Cena s DPH</label><input type="number" step="0.01" id="f-cena_s_dph" value="${p?.cena_s_dph??''}"></div>
        <div class="field"><label>Náklady</label><input type="number" step="0.01" id="f-naklady" value="${p?.naklady??''}"></div>
        <div class="field"><label>Zisk</label><input type="number" step="0.01" id="f-zisk" value="${p?.zisk??''}"></div>
        <div class="field"><label>Kredit</label><input type="number" step="0.01" id="f-kredit" value="${p?.kredit??''}"></div>
        <div class="field"><label>Cena bez FA</label><input type="number" step="0.01" id="f-cena_bez_fa" value="${p?.cena_bez_fa??''}"></div>
        <div class="field"><label>Náklady bez FA</label><input type="number" step="0.01" id="f-naklady_bez_fa" value="${p?.naklady_bez_fa??''}"></div>
      </div>
    </div>
    <div id="pf-flags" style="display:none">
      <div class="checkbox-row" style="flex-direction:column;align-items:flex-start">
        ${cbox('projekt_kreditny','Kreditný projekt',chk('projekt_kreditny'))}
        ${cbox('projekt_zberny','Zberný projekt',chk('projekt_zberny'))}
        ${cbox('projekt_kniha','Kniha',chk('projekt_kniha'))}
        ${cbox('projekt_cp','CP',chk('projekt_cp'))}
        ${cbox('projekt_oznaceny','Označený',chk('projekt_oznaceny'))}
        ${cbox('projekt_sledovany','Sledovaný',chk('projekt_sledovany'))}
        ${cbox('projekt_cakajuci','Čakajúci',chk('projekt_cakajuci'))}
        ${cbox('projekt_bezny','Bežný',chk('projekt_bezny'))}
        ${cbox('projekt_hotovo','Hotovo',chk('projekt_hotovo'))}
        ${cbox('projekt_fakturovany','Fakturovaný',chk('projekt_fakturovany'))}
        ${cbox('projekt_fakturovany_vopred','Fakturovaný vopred',chk('projekt_fakturovany_vopred'))}
        ${cbox('projekt_uhradeny','Uhradený',chk('projekt_uhradeny'))}
        ${cbox('projekt_expedovat','Expedovať',chk('projekt_expedovat'))}
        ${cbox('vpt_agenturnacena','VpT agentúrna cena',chk('vpt_agenturnacena'))}
      </div>
    </div>
    <div id="pf-notes" style="display:none">
      <div class="form-grid">
        <div class="field form-full"><label>Poznámky</label><textarea id="f-poznamky">${v('poznamky')}</textarea></div>
        <div class="field form-full"><label>Poznámky ZL</label><textarea id="f-poznamky_zl">${v('poznamky_zl')}</textarea></div>
        <div class="field form-full"><label>Poznámky 1</label><textarea id="f-poznamky_1">${v('poznamky_1')}</textarea></div>
        <div class="field form-full"><label>Poznámka CP</label><textarea id="f-poznamka_cp">${v('poznamka_cp')}</textarea></div>
        <div class="field form-full"><label>Log projektu</label><textarea id="f-projekt_log" style="min-height:100px">${v('projekt_log')}</textarea></div>
      </div>
    </div>`;
    App.openModal(p ? `Upraviť projekt #${p.id}` : 'Nový projekt', body, p?.id, !!p);
    if (p) document.getElementById('modal').classList.add('modal-lg');
  },

  async loadNaklady(projectId, tabEl) {
    switchTab(tabEl, 'tab-naklady');
    const el = document.getElementById('tab-naklady');
    if (!el) return;
    const data = await API.get('/api/projects/' + projectId + '/naklady');
    const total = data.reduce((s, n) => s + (n.vyroba || 0), 0);
    el.innerHTML = data.length ? `
      <div class="table-wrap">
        <table>
          <thead><tr><th>ID</th><th>Popis</th><th>MJ</th><th>Počet</th><th>JC výroba</th><th>Výroba</th><th>Typ</th><th>Hotovo</th><th>Skont.</th></tr></thead>
          <tbody>${data.map(n => `<tr>
            <td class="mono">${n.id}</td>
            <td class="td-truncate">${esc(n.popis||'')}</td>
            <td>${esc(n.mj||'')}</td>
            <td>${n.pocet??''}</td>
            <td class="cur">${fmt_eur(n.jc_vyroba)}</td>
            <td class="cur">${fmt_eur(n.vyroba)}</td>
            <td>${esc(n.typ_nakladu||'')}</td>
            <td>${n.hotovo?'✅':''}</td>
            <td>${n.skontrolovane?'✓':''}</td>
          </tr>`).join('')}</tbody>
        </table>
        <div class="naklady-total">Spolu: <strong>${fmt_eur(total)}</strong></div>
      </div>` : '<div class="empty">Žiadne náklady</div>';
    el.insertAdjacentHTML('beforeend', `<button class="btn btn-primary btn-sm" style="margin-top:10px" onclick="Views.projects.openAddNaklad(${projectId})">+ Pridať náklad</button>`);
  },

  openAddNaklad(projectId) {
    const typy = State.lookups.typy_nakladov || [];
    const typOpts = typy.map(t => `<option value="${esc(t.nazov)}">${esc(t.nazov)}</option>`).join('');
    const body = `<div class="form-grid">
      <div class="field form-full"><label>Popis</label><input id="fn-popis"></div>
      <div class="field"><label>MJ</label><input id="fn-mj"></div>
      <div class="field"><label>Počet</label><input type="number" step="0.001" id="fn-pocet" oninput="calcNakladCena()"></div>
      <div class="field"><label>JC výroba</label><input type="number" step="0.01" id="fn-jc_vyroba" oninput="calcNakladCena()"></div>
      <div class="field"><label>Výroba (spolu)</label><input type="number" step="0.01" id="fn-vyroba" readonly style="background:#f8fafc"></div>
      <div class="field"><label>Typ nákladu</label><select id="fn-typ_nakladu"><option value="">—</option>${typOpts}</select></div>
      <div class="field"><label>Objednávka</label><input id="fn-objednavka"></div>
      <div class="field"><label>Kde je</label><input id="fn-kde_je"></div>
      <div class="field form-full"><label>Poznámka</label><textarea id="fn-poznamka"></textarea></div>
    </div>
    <div class="checkbox-row" style="margin-top:8px">
      ${cbox('fn-hotovo','Hotovo','')}
      ${cbox('fn-skontrolovane','Skontrolované','')}
    </div>`;
    App.openModal('Nový náklad', body, null, false);
    document.getElementById('modal-save-btn').onclick = async () => {
      const text = ['popis','mj','objednavka','kde_je','poznamka','typ_nakladu'];
      const nums = ['pocet','jc_vyroba','vyroba'];
      const bools = ['hotovo','skontrolovane'];
      const data = { id_projektu: projectId };
      text.forEach(f => { data[f] = document.getElementById('fn-'+f)?.value || null; });
      nums.forEach(f => { const e = document.getElementById('fn-'+f); data[f] = e?.value !== '' ? parseFloat(e?.value)||0 : 0; });
      bools.forEach(f => { data[f] = !!document.getElementById('fn-'+f)?.checked; });
      await API.post('/api/projects/' + projectId + '/naklady', data);
      showToast('Náklad pridaný', 'success');
      App.closeModal();
      this.loadNaklady(projectId, document.querySelector('.tab.active'));
    };
  },

  async save() {
    const fields = ['nazov_projektu','nazov_firmy','priezvisko_meno','manazer','stav','kategoria','priorita',
      'cislo_objednavky','cislo_cp','strucna_specifikacia','folder_zakazky','folder_cp','zucastneni',
      'prijal','zostava','podobny_projekt','f1','f2','f3','f4',
      'poznamky','poznamky_zl','poznamky_1','poznamka_cp','projekt_log',
      'cena_bez_dph','dph_ceny','cena_s_dph','naklady','zisk','kredit','cena_bez_fa','naklady_bez_fa'];
    const bools = ['projekt_kreditny','projekt_zberny','projekt_kniha','projekt_cp','projekt_oznaceny',
      'projekt_sledovany','projekt_cakajuci','projekt_bezny','projekt_hotovo','projekt_fakturovany',
      'projekt_fakturovany_vopred','projekt_uhradeny','projekt_expedovat','vpt_agenturnacena'];
    const dates = ['prijate','termin_odovzdania','datum_prijatia_objednavky','datum_na_objednavke','projekt_expedovat_datum'];
    const nums = ['cena_bez_dph','dph_ceny','cena_s_dph','naklady','zisk','kredit','cena_bez_fa','naklady_bez_fa'];
    const data = {};
    fields.forEach(f => {
      const el = document.getElementById('f-'+f);
      if (!el) return;
      data[f] = el.value || null;
    });
    bools.forEach(f => { data[f] = !!document.getElementById('f-'+f)?.checked; });
    dates.forEach(f => { const el = document.getElementById('f-'+f); if (el?.value) data[f] = el.value; else data[f] = null; });
    nums.forEach(f => { if (data[f] !== null) data[f] = parseFloat(data[f]) || 0; });

    if (State.editId) await API.put('/api/projects/' + State.editId, data);
    else await API.post('/api/projects', data);
    showToast('Projekt uložený', 'success');
    App.closeModal();
    App.closeDetail();
    await this.load();
  },

  async delete() {
    if (!confirm('Odstraniť projekt?')) return;
    await API.del('/api/projects/' + State.editId);
    showToast('Projekt odstránený', 'info');
    App.closeModal();
    App.closeDetail();
    await this.load();
  },
};

// ─── ITEMS ───────────────────────────────────────────────────────────────────
Views.items = {
  async render() {
    const cont = document.getElementById('content');
    const statusOpts = (State.lookups.status_polozky||[]).map(s => `<option value="${esc(s.nazov)}">${esc(s.nazov)}</option>`).join('');
    const typOpts = (State.lookups.typy_zakaziek||[]).map(s => `<option value="${esc(s.nazov)}">${esc(s.nazov)}</option>`).join('');
    cont.innerHTML = `
    <div class="filter-bar">
      <input type="search" id="i-search" placeholder="Hľadať popis...">
      <select id="i-status"><option value="">Všetky statusy</option>${statusOpts}</select>
      <select id="i-typ"><option value="">Všetky typy</option>${typOpts}</select>
      <label class="checkbox-item"><input type="checkbox" id="i-fakturovat"> Fakturovať</label>
      <label class="checkbox-item"><input type="checkbox" id="i-fakturovane"> Fakturované</label>
    </div>
    <div id="items-table-wrap"><div class="loading">Načítavam...</div></div>`;
    ['i-search','i-status','i-typ','i-fakturovat','i-fakturovane'].forEach(id => {
      document.getElementById(id)?.addEventListener('change', () => this.load());
      if (id === 'i-search') document.getElementById(id)?.addEventListener('input', () => this.load());
    });
    await this.load();
  },

  async load() {
    const params = new URLSearchParams({ limit: 300 });
    const s = document.getElementById('i-status')?.value;
    const t = document.getElementById('i-typ')?.value;
    const fak = document.getElementById('i-fakturovat')?.checked;
    const fakd = document.getElementById('i-fakturovane')?.checked;
    if (s) params.set('status', s);
    if (t) params.set('typ_zakazky', t);
    if (fak) params.set('fakturovat', 'true');
    if (fakd) params.set('fakturovane', 'true');
    const data = await API.get('/api/items?' + params);
    State.items.data = data;
    const wrap = document.getElementById('items-table-wrap');
    if (!wrap) return;
    if (!data.length) { wrap.innerHTML = '<div class="empty">Žiadne položky</div>'; return; }
    wrap.innerHTML = `<div class="table-wrap"><table>
      <thead><tr><th>ID</th><th>Projekt</th><th>Popis</th><th>MJ</th><th>Počet</th><th>JC</th><th>Cena</th><th>Zľava</th><th>DPH</th><th>s DPH</th><th>Status</th><th>Typ</th><th>Fak.</th></tr></thead>
      <tbody>${data.map(i => `
        <tr onclick="Views.items.openDetail(${i.id})">
          <td class="mono">${i.id}</td>
          <td class="mono">${i.id_projektu||''}</td>
          <td class="td-truncate">${esc(i.popis||'')}</td>
          <td>${esc(i.mj||'')}</td>
          <td>${i.pocet??''}</td>
          <td class="cur">${fmt_eur(i.jc)}</td>
          <td class="cur">${fmt_eur(i.cena)}</td>
          <td>${i.zlava!=null?(i.zlava*100).toFixed(0)+'%':''}</td>
          <td>${i.sadzba_dph!=null?(i.sadzba_dph*100).toFixed(0)+'%':''}</td>
          <td class="cur">${fmt_eur(i.cena_s_dph)}</td>
          <td>${statusBadge(i.status)}</td>
          <td>${esc(i.typ_zakazky||'')}</td>
          <td>${i.fakturovat?'✓':''} ${i.fakturovane?'✅':''}</td>
        </tr>`).join('')}
      </tbody></table>
      <div class="pagination"><span>${data.length} položiek</span></div>
    </div>`;
  },

  async openDetail(id) {
    const item = State.items.data.find(i => i.id === id) || {};
    const body = `
      <div class="detail-grid">
        ${dfield('ID',item.id)} ${dfield('Projekt ID',item.id_projektu)}
        ${dfield('Popis',item.popis,'full')}
        ${dfield('MJ',item.mj)} ${dfield('Počet',item.pocet)}
        ${dfield('JC',fmt_eur(item.jc))} ${dfield('Cena',fmt_eur(item.cena))}
        ${dfield('Zľava',item.zlava!=null?(item.zlava*100).toFixed(1)+'%':'')}
        ${dfield('DPH',item.sadzba_dph!=null?(item.sadzba_dph*100).toFixed(0)+'%':'')}
        ${dfield('Cena s DPH',fmt_eur(item.cena_s_dph))}
        ${dfield('Status',statusBadge(item.status))} ${dfield('Typ zákazky',item.typ_zakazky)}
        ${dfield('Fakturovať',item.fakturovat?'Áno':'Nie')} ${dfield('Fakturované',item.fakturovane?'Áno':'Nie')}
        ${dfield('Č. faktúry',item.cislo_faktury)} ${dfield('Dátum fakt.',fmt_date(item.datum_fakturacie))}
      </div>
      ${item.popis ? `<div class="detail-section"><h4>Podpopis</h4><p style="font-size:13px">${esc(item.podpopis||'—')}</p></div>` : ''}
      ${item.format ? `<div class="detail-section"><h4>Tlačové parametre</h4><div class="detail-grid">
        ${dfield('Formát',item.format)} ${dfield('Väzba',item.vazba)}
        ${dfield('Strán',item.pocet_stran)} ${dfield('Strán FAR',item.pocet_stran_far)}
        ${dfield('Typ kalkulácie',item.typ_kalkulacie)}
      </div></div>` : ''}
      ${item.poznamka ? `<div class="detail-section"><h4>Poznámka</h4><p style="font-size:13px">${esc(item.poznamka)}</p></div>` : ''}
    `;
    App.openDetail(`Položka #${item.id}`, body, () => this.openEdit(id));
  },

  openAdd() { this.openForm(null, null); },
  openAddForProject(projectId) { this.openForm(null, projectId); },
  async openEdit(id) {
    const item = await API.get('/api/items');
    const found = State.items.data.find(i => i.id === id);
    if (found) this.openForm(found, null);
  },

  openForm(item, projectId) {
    const statOpts = (State.lookups.status_polozky||[]).map(s => `<option value="${esc(s.nazov)}" ${item?.status===s.nazov?'selected':''}>${esc(s.nazov)}</option>`).join('');
    const typOpts = (State.lookups.typy_zakaziek||[]).map(s => `<option value="${esc(s.nazov)}" ${item?.typ_zakazky===s.nazov?'selected':''}>${esc(s.nazov)}</option>`).join('');
    const vazbOpts = (State.lookups.vazby||[]).map(s => `<option value="${esc(s.vazba)}" ${item?.vazba===s.vazba?'selected':''}>${esc(s.vazba)} - ${esc(s.popis)}</option>`).join('');
    const v = k => esc(item?.[k] ?? '');
    const chk = k => item?.[k] ? 'checked' : '';
    const body = `
    <div class="tabs">
      <span class="tab active" onclick="switchTab(this,'if-basic')">Základné</span>
      <span class="tab" onclick="switchTab(this,'if-tlac')">Tlač</span>
      <span class="tab" onclick="switchTab(this,'if-expedia')">Expedícia</span>
    </div>
    <div id="if-basic">
      <div class="form-grid">
        <div class="field"><label>Projekt ID</label><input type="number" id="fi-id_projektu" value="${item?.id_projektu ?? projectId ?? ''}"></div>
        <div class="field"><label>Poradie</label><input type="number" id="fi-poradie" value="${item?.poradie??''}"></div>
        <div class="field form-full"><label>Popis</label><input id="fi-popis" value="${v('popis')}"></div>
        <div class="field form-full"><label>Podpopis</label><textarea id="fi-podpopis">${v('podpopis')}</textarea></div>
        <div class="field"><label>MJ</label><input id="fi-mj" value="${v('mj')}"></div>
        <div class="field"><label>Počet</label><input type="number" step="0.001" id="fi-pocet" value="${item?.pocet??''}" oninput="calcItemPrice()"></div>
        <div class="field"><label>JC (bez DPH)</label><input type="number" step="0.01" id="fi-jc" value="${item?.jc??''}" oninput="calcItemPrice()"></div>
        <div class="field"><label>Zľava (0-1)</label><input type="number" step="0.01" min="0" max="1" id="fi-zlava" value="${item?.zlava??0}" oninput="calcItemPrice()"></div>
        <div class="field"><label>Cena bez DPH</label><input type="number" step="0.01" id="fi-cena" value="${item?.cena??''}" readonly style="background:#f8fafc"></div>
        <div class="field"><label>Sadzba DPH (0-1)</label><input type="number" step="0.01" min="0" max="1" id="fi-sadzba_dph" value="${item?.sadzba_dph??0.2}" oninput="calcItemPrice()"></div>
        <div class="field"><label>Cena s DPH</label><input type="number" step="0.01" id="fi-cena_s_dph" value="${item?.cena_s_dph??''}" readonly style="background:#f8fafc"></div>
        <div class="field"><label>Status</label><select id="fi-status"><option value="">—</option>${statOpts}</select></div>
        <div class="field"><label>Typ zákazky</label><select id="fi-typ_zakazky"><option value="">—</option>${typOpts}</select></div>
        <div class="field form-full"><label>Stručná špecifikácia</label><input id="fi-strucna_specifikacia" value="${v('strucna_specifikacia')}"></div>
        <div class="field form-full"><label>Poznámka</label><textarea id="fi-poznamka">${v('poznamka')}</textarea></div>
        <div class="field form-full"><label>Poznámka VL</label><textarea id="fi-poznamka_vl">${v('poznamka_vl')}</textarea></div>
      </div>
      <div class="checkbox-row" style="margin-top:8px">
        ${cbox('fi-fakturovat','Fakturovať',chk('fakturovat'))}
        ${cbox('fi-fakturovane','Fakturované',chk('fakturovane'))}
        ${cbox('fi-faktura_vopred','Faktúra vopred',chk('faktura_vopred'))}
        ${cbox('fi-odovzdane','Odovzdané',chk('odovzdane'))}
        ${cbox('fi-dl','DL',chk('dl'))} ${cbox('fi-vkladacky_ano_nie','Vkladačky',chk('vkladacky_ano_nie'))} ${cbox('fi-do_faktury','Do faktúry',chk('do_faktury'))}
      </div>
    </div>
    <div id="if-tlac" style="display:none">
      <div class="form-grid">
        <div class="field"><label>Formát</label><input id="fi-format" value="${v('format')}"></div>
        <div class="field"><label>Väzba</label><select id="fi-vazba"><option value="">—</option>${vazbOpts}</select></div>
        <div class="field"><label>Strán celkom</label><input type="number" id="fi-pocet_stran" value="${item?.pocet_stran??''}"></div>
        <div class="field"><label>Strán FAR</label><input type="number" id="fi-pocet_stran_far" value="${item?.pocet_stran_far??''}"></div>
        <div class="field"><label>Typ kalkulácie</label><input id="fi-typ_kalkulacie" value="${v('typ_kalkulacie')}"></div>
        <div class="field"><label>Vnútro papier typ</label><input id="fi-db_vn_papier_typ" value="${v('db_vn_papier_typ')}"></div>
        <div class="field"><label>Vnútro lesk/mat</label><input id="fi-db_vn_papier_lesk_mat" value="${v('db_vn_papier_lesk_mat')}"></div>
        <div class="field"><label>Obal farebnosť</label><input id="fi-db_ob_farebnost" value="${v('db_ob_farebnost')}"></div>
        <div class="field"><label>Obal papier typ</label><input id="fi-db_ob_papier_typ" value="${v('db_ob_papier_typ')}"></div>
        <div class="field"><label>Obal PÚ</label><input id="fi-db_ob_pu" value="${v('db_ob_pu')}"></div>
        <div class="field"><label>Chrbát</label><input id="fi-db_chrbat" value="${v('db_chrbat')}"></div>
        <div class="field"><label>Ako vkladať</label><textarea id="fi-ako_vkladat" style="min-height:60px">${v('ako_vkladat')}</textarea></div>
        <div class="field"><label>Na FAR</label><textarea id="fi-na_far">${v('na_far')}</textarea></div>
        <div class="field"><label>Zhrnutý text vyradovača</label><textarea id="fi-zhrnuty_text_vyradovaca">${v('zhrnuty_text_vyradovaca')}</textarea></div>
        <div class="field"><label>Lacetka</label><input id="fi-db_lacetka" value="${v('db_lacetka')}"></div>
      </div>
    </div>
    <div id="if-expedia" style="display:none">
      <div class="form-grid">
        ${cbox('fi-polozka_expedovat','Expedovať',chk('polozka_expedovat'))}
        <div class="field"><label>Dátum expedície</label><input type="date" id="fi-polozka_expedovat_datum" value="${isoDate(item?.polozka_expedovat_datum)}"></div>
        <div class="field"><label>Komu dodať</label><input id="fi-komu_dodat" value="${v('komu_dodat')}"></div>
        <div class="field"><label>Kde vyzdvihnúť</label><input id="fi-polozka_kde_vyzdvihnut" value="${v('polozka_kde_vyzdvihnut')}"></div>
        <div class="field"><label>Číslo faktúry</label><input id="fi-cislo_faktury" value="${v('cislo_faktury')}"></div>
        <div class="field"><label>Dátum fakturácie</label><input type="date" id="fi-datum_fakturacie" value="${isoDate(item?.datum_fakturacie)}"></div>
        <div class="field"><label>Kto fakturuje</label><input id="fi-kto_fakturuje" value="${v('kto_fakturuje')}"></div>
      </div>
    </div>`;
    App.openModal(item ? `Upraviť položku #${item.id}` : 'Nová položka', body, item?.id, !!item);
  },

  async save() {
    const textFields = ['popis','podpopis','mj','strucna_specifikacia','poznamka',
      'status','typ_zakazky','format','vazba','typ_kalkulacie',
      'db_vn_papier_typ','db_vn_papier_lesk_mat','db_vn_papier_specifikacia',
      'db_ob_farebnost','db_ob_papier_typ','db_ob_papier_lesk_mat',
      'db_ob_pu','db_chrbat','db_lacetka','komu_dodat','polozka_kde_vyzdvihnut','poznamka_vl','ako_vkladat','na_far','zhrnuty_text_vyradovaca',
      'cislo_faktury','kto_fakturuje'];
    const nums = ['pocet','jc','cena','zlava','sadzba_dph','cena_s_dph',
      'pocet_stran','pocet_stran_far','id_projektu','poradie'];
    const bools = ['fakturovat','fakturovane','faktura_vopred','odovzdane','dl','polozka_expedovat','vkladacky_ano_nie','do_faktury'];
    const dates = ['polozka_expedovat_datum','datum_fakturacie'];
    const data = {};
    textFields.forEach(f => { const e = document.getElementById('fi-'+f); if (e) data[f] = e.value || null; });
    nums.forEach(f => { const e = document.getElementById('fi-'+f); if (e) data[f] = e.value !== '' ? parseFloat(e.value) : null; });
    bools.forEach(f => { data[f] = !!document.getElementById('fi-'+f)?.checked; });
    dates.forEach(f => { const e = document.getElementById('fi-'+f); data[f] = e?.value || null; });

    const pid = data.id_projektu;
    if (State.editId) await API.put('/api/items/' + State.editId, data);
    else if (pid) await API.post('/api/projects/' + pid + '/items', data);
    App.closeModal();
    await this.load();
  },

  async delete() {
    if (!confirm('Odstraniť položku?')) return;
    await API.del('/api/items/' + State.editId);
    App.closeModal();
    App.closeDetail();
    await this.load();
  },
};

// ─── INVOICES ────────────────────────────────────────────────────────────────
Views.invoices = {
  async render() {
    const cont = document.getElementById('content');
    cont.innerHTML = `
    <div class="filter-bar">
      <input type="search" id="inv-search" placeholder="Hľadať odberateľa...">
      <label class="checkbox-item"><input type="checkbox" id="inv-nezaplatene"> Nezaplatené</label>
      <label class="checkbox-item"><input type="checkbox" id="inv-po_splatnosti"> Po splatnosti</label>
    </div>
    <div id="inv-table-wrap"><div class="loading">Načítavam...</div></div>`;
    ['inv-search','inv-nezaplatene','inv-po_splatnosti'].forEach(id => {
      const el = document.getElementById(id);
      el?.addEventListener(id==='inv-search'?'input':'change', () => this.load());
    });
    await this.load();
  },

  async load() {
    const params = new URLSearchParams({ limit: 300 });
    const s = document.getElementById('inv-search')?.value;
    if (s) params.set('search', s);
    if (document.getElementById('inv-nezaplatene')?.checked) params.set('nezaplatene', 'true');
    if (document.getElementById('inv-po_splatnosti')?.checked) params.set('po_splatnosti', 'true');
    const data = await API.get('/api/invoices?' + params);
    State.invoices.data = data;
    const wrap = document.getElementById('inv-table-wrap');
    if (!wrap) return;
    if (!data.length) { wrap.innerHTML = '<div class="empty">Žiadne faktúry</div>'; return; }
    wrap.innerHTML = `<div class="table-wrap"><table>
      <thead><tr><th>Č. FA</th><th>Dátum</th><th>Odberateľ</th><th>Popis</th><th>Bez DPH</th><th>s DPH</th><th>k úhrade</th><th>Splatnosť</th><th>Zostáva</th><th>Dní po spl.</th><th>Dátum úhrady</th></tr></thead>
      <tbody>${data.map(f => {
        const overdue = (f.dni_po_splatnosti || 0) > 0 && (f.zostava_uhradit || 0) > 0;
        const paid = (f.zostava_uhradit || 0) <= 0;
        return `<tr class="${overdue?'overdue':paid?'paid':''}" onclick="Views.invoices.openDetail(${f.id})">
          <td class="mono">${esc(f.cislo_faktury||'')}</td>
          <td>${fmt_date(f.datum_vystavenia)}</td>
          <td class="td-truncate">${esc(f.odberatel||'')}</td>
          <td class="td-truncate">${esc(f.popis||'')}</td>
          <td class="cur">${fmt_eur(f.suma_bez_dph)}</td>
          <td class="cur">${fmt_eur(f.suma_s_dph)}</td>
          <td class="cur">${fmt_eur(f.suma_k_uhrade)}</td>
          <td>${fmt_date(f.datum_splatnosti)}</td>
          <td class="cur ${overdue?'cur-neg':paid?'cur-pos':''}">${fmt_eur(f.zostava_uhradit)}</td>
          <td ${overdue?'style="color:var(--danger);font-weight:600"':''}>${f.dni_po_splatnosti??'—'}</td>
          <td>${fmt_date(f.datum_uhrady)}</td>
        </tr>`;
      }).join('')}
      </tbody></table>
      <div class="pagination">
        <span>${data.length} faktúr | Celkom s DPH: <strong>${fmt_eur(data.reduce((a,f)=>a+(f.suma_s_dph||0),0))}</strong> | Zostáva uhradiť: <strong>${fmt_eur(data.reduce((a,f)=>a+(f.zostava_uhradit||0),0))}</strong></span>
      </div>
    </div>`;
  },

  async openDetail(id) {
    const f = State.invoices.data.find(i => i.id === id) || {};
    const overdue = (f.dni_po_splatnosti||0) > 0 && (f.zostava_uhradit||0) > 0;
    const body = `
      <div class="detail-grid">
        ${dfield('Č. faktúry',f.cislo_faktury)} ${dfield('Dátum vystavenia',fmt_date(f.datum_vystavenia))}
        ${dfield('Odberateľ',f.odberatel,'full')}
        ${dfield('Popis',f.popis,'full')}
        ${dfield('Suma bez DPH',fmt_eur(f.suma_bez_dph))} ${dfield('Suma s DPH',fmt_eur(f.suma_s_dph))}
        ${dfield('Suma k úhrade',fmt_eur(f.suma_k_uhrade))} ${dfield('Dátum splatnosti',fmt_date(f.datum_splatnosti))}
        ${dfield('Zostáva uhradiť',`<span class="${overdue?'cur-neg':'cur-pos'}">${fmt_eur(f.zostava_uhradit)}</span>`)}
        ${dfield('Dní po splatnosti', overdue?`<span style="color:var(--danger);font-weight:600">${f.dni_po_splatnosti}</span>`:f.dni_po_splatnosti??'—')}
        ${dfield('Dátum úhrady',fmt_date(f.datum_uhrady))}
      </div>`;
    App.openDetail(`Faktúra ${f.cislo_faktury}`, body, () => this.openEdit(id));
  },

  openAdd() { this.openForm(null); },
  async openEdit(id) { const f = State.invoices.data.find(i => i.id === id); if (f) this.openForm(f); },

  openForm(f) {
    const v = k => esc(f?.[k] ?? '');
    const body = `<div class="form-grid">
      <div class="field"><label>Č. faktúry</label><input id="fv-cislo_faktury" value="${v('cislo_faktury')}"></div>
      <div class="field"><label>Dátum vystavenia</label><input type="date" id="fv-datum_vystavenia" value="${isoDate(f?.datum_vystavenia)}"></div>
      <div class="field form-full"><label>Odberateľ</label><input id="fv-odberatel" value="${v('odberatel')}"></div>
      <div class="field form-full"><label>Popis</label><input id="fv-popis" value="${v('popis')}"></div>
      <div class="field"><label>Suma bez DPH</label><input type="number" step="0.01" id="fv-suma_bez_dph" value="${f?.suma_bez_dph??''}"></div>
      <div class="field"><label>Suma s DPH</label><input type="number" step="0.01" id="fv-suma_s_dph" value="${f?.suma_s_dph??''}"></div>
      <div class="field"><label>Suma k úhrade</label><input type="number" step="0.01" id="fv-suma_k_uhrade" value="${f?.suma_k_uhrade??''}"></div>
      <div class="field"><label>Dátum splatnosti</label><input type="date" id="fv-datum_splatnosti" value="${isoDate(f?.datum_splatnosti)}"></div>
      <div class="field"><label>Zostáva uhradiť</label><input type="number" step="0.01" id="fv-zostava_uhradit" value="${f?.zostava_uhradit??''}"></div>
      <div class="field"><label>Dní po splatnosti</label><input type="number" id="fv-dni_po_splatnosti" value="${f?.dni_po_splatnosti??''}"></div>
      <div class="field"><label>Dátum úhrady</label><input type="date" id="fv-datum_uhrady" value="${isoDate(f?.datum_uhrady)}"></div>
    </div>`;
    App.openModal(f ? `Upraviť faktúru ${f.cislo_faktury}` : 'Nová faktúra', body, f?.id, !!f);
  },

  async save() {
    const text = ['cislo_faktury','odberatel','popis'];
    const nums = ['suma_bez_dph','suma_s_dph','suma_k_uhrade','zostava_uhradit','dni_po_splatnosti'];
    const dates = ['datum_vystavenia','datum_splatnosti','datum_uhrady'];
    const data = {};
    text.forEach(f => { data[f] = document.getElementById('fv-'+f)?.value || null; });
    nums.forEach(f => { const e = document.getElementById('fv-'+f); data[f] = e?.value !== '' ? parseFloat(e?.value) : null; });
    dates.forEach(f => { data[f] = document.getElementById('fv-'+f)?.value || null; });
    if (State.editId) await API.put('/api/invoices/' + State.editId, data);
    else await API.post('/api/invoices', data);
    showToast('Faktúra uložená', 'success');
    App.closeModal();
    App.closeDetail();
    await this.load();
  },

  async delete() {
    if (!confirm('Odstraniť faktúru?')) return;
    await API.del('/api/invoices/' + State.editId);
    showToast('Faktúra odstránená', 'info');
    App.closeModal();
    App.closeDetail();
    await this.load();
  },
};

// ─── CUSTOMERS ───────────────────────────────────────────────────────────────
Views.customers = {
  async render() {
    const cont = document.getElementById('content');
    cont.innerHTML = `
    <div class="filter-bar"><input type="search" id="cust-search" placeholder="Hľadať zákazníka..."></div>
    <div id="cust-table-wrap"><div class="loading">Načítavam...</div></div>`;
    document.getElementById('cust-search')?.addEventListener('input', () => this.load());
    await this.load();
  },

  async load() {
    const s = document.getElementById('cust-search')?.value;
    const params = new URLSearchParams({ limit: 200 });
    if (s) params.set('search', s);
    const data = await API.get('/api/customers?' + params);
    State.customers.data = data;
    const wrap = document.getElementById('cust-table-wrap');
    if (!wrap) return;
    if (!data.length) { wrap.innerHTML = '<div class="empty">Žiadni zákazníci</div>'; return; }
    wrap.innerHTML = `<div class="table-wrap"><table>
      <thead><tr><th>ID</th><th>Meno</th><th>Ulica</th><th>PSČ</th><th>Mesto</th><th>Email</th><th>Telefón</th></tr></thead>
      <tbody>${data.map(c => `<tr onclick="Views.customers.openDetail(${c.id})">
        <td class="mono">${c.id}</td>
        <td>${esc(c.customer_name||'')}</td>
        <td>${esc(c.customer_street||'')}</td>
        <td>${esc(c.customer_zipcode||'')}</td>
        <td>${esc(c.customer_city||'')}</td>
        <td>${c.customer_email?`<a href="mailto:${esc(c.customer_email)}" onclick="event.stopPropagation()">${esc(c.customer_email)}</a>`:''}</td>
        <td>${esc(c.customer_phone||'')}</td>
      </tr>`).join('')}
      </tbody></table>
      <div class="pagination"><span>${data.length} zákazníkov</span></div>
    </div>`;
  },

  openDetail(id) {
    const c = State.customers.data.find(x => x.id === id) || {};
    const body = `<div class="detail-grid">
      ${dfield('Meno',c.customer_name,'full')}
      ${dfield('Ulica',c.customer_street,'full')}
      ${dfield('PSČ',c.customer_zipcode)} ${dfield('Mesto',c.customer_city)}
      ${dfield('Email',c.customer_email?`<a href="mailto:${esc(c.customer_email)}">${esc(c.customer_email)}</a>`:'')}
      ${dfield('Telefón',c.customer_phone)}
    </div>`;
    App.openDetail(c.customer_name || 'Zákazník', body, () => this.openEdit(id));
  },

  openAdd() { this.openForm(null); },
  openEdit(id) { const c = State.customers.data.find(x => x.id === id); if (c) this.openForm(c); },

  openForm(c) {
    const v = k => esc(c?.[k] ?? '');
    const body = `<div class="form-grid">
      <div class="field form-full"><label>Meno / Firma</label><input id="fc-customer_name" value="${v('customer_name')}"></div>
      <div class="field form-full"><label>Ulica</label><input id="fc-customer_street" value="${v('customer_street')}"></div>
      <div class="field"><label>PSČ</label><input id="fc-customer_zipcode" value="${v('customer_zipcode')}"></div>
      <div class="field"><label>Mesto</label><input id="fc-customer_city" value="${v('customer_city')}"></div>
      <div class="field"><label>Email</label><input type="email" id="fc-customer_email" value="${v('customer_email')}"></div>
      <div class="field"><label>Telefón</label><input id="fc-customer_phone" value="${v('customer_phone')}"></div>
    </div>`;
    App.openModal(c ? 'Upraviť zákazníka' : 'Nový zákazník', body, c?.id, !!c);
  },

  async save() {
    const fields = ['customer_name','customer_street','customer_zipcode','customer_city','customer_email','customer_phone'];
    const data = {};
    fields.forEach(f => { data[f] = document.getElementById('fc-'+f)?.value || null; });
    if (State.editId) await API.put('/api/customers/' + State.editId, data);
    else await API.post('/api/customers', data);
    App.closeModal();
    App.closeDetail();
    await this.load();
  },

  async delete() {
    if (!confirm('Odstraniť zákazníka?')) return;
    await API.del('/api/customers/' + State.editId);
    App.closeModal();
    App.closeDetail();
    await this.load();
  },
};

// ─── CREDITS ─────────────────────────────────────────────────────────────────
Views.credits = {
  async render() {
    const cont = document.getElementById('content');
    cont.innerHTML = `
    <div class="tab-bar" style="margin-bottom:12px">
      <button class="tab-btn active" onclick="Views.credits.switchTab('pohyby',this)">Pohyby</button>
      <button class="tab-btn" onclick="Views.credits.switchTab('import',this)">Import výpisu</button>
      <button class="tab-btn" onclick="Views.credits.switchTab('parovanie',this)">Párovanie faktúr</button>
    </div>
    <div id="cr-tab-pohyby">
      <div class="filter-bar">
        <input type="search" id="cr-search" placeholder="Hľadať meno / memo...">
        <select id="cr-trntype"><option value="">Všetky typy</option><option>CREDIT</option><option>DEBIT</option></select>
      </div>
      <div id="cr-table-wrap"><div class="loading">Načítavam...</div></div>
    </div>
    <div id="cr-tab-import" style="display:none">
      <div class="card" style="max-width:600px">
        <h3 style="margin-top:0">Import bankového výpisu</h3>
        <div class="form-grid">
          <div class="field form-full">
            <label>Súbor OFX / QFX (odporúčané)</label>
            <input type="file" id="cr-file-ofx" accept=".ofx,.qfx,.txt">
            <small>Export OFX z internet bankingu (Tatra banka, VÚB, ČSOB, Sporiteľňa)</small>
          </div>
          <div class="field form-full" style="margin-top:8px">
            <button class="btn btn-primary" onclick="Views.credits.importOFX()">Importovať OFX</button>
          </div>
          <div class="field form-full" style="margin-top:16px;padding-top:16px;border-top:1px solid var(--border)">
            <label>Súbor PDF (bankový výpis)</label>
            <input type="file" id="cr-file-pdf" accept=".pdf">
            <small>PDF výpis zo slovenských bánk – automatická extrakcia transakcií</small>
          </div>
          <div class="field form-full" style="margin-top:8px">
            <button class="btn btn-primary" onclick="Views.credits.importPDF()">Importovať PDF</button>
          </div>
        </div>
        <div id="cr-import-result" style="margin-top:16px"></div>
      </div>
    </div>
    <div id="cr-tab-parovanie" style="display:none">
      <div style="display:flex;gap:8px;margin-bottom:12px;align-items:center">
        <button class="btn btn-secondary" onclick="Views.credits.previewMatches()">Náhľad párovania</button>
        <button class="btn btn-primary" onclick="Views.credits.runMatch()">Spárovať a aktualizovať faktúry</button>
      </div>
      <div id="cr-match-result"></div>
    </div>`;
    ['cr-search','cr-trntype'].forEach(id => {
      const e = document.getElementById(id);
      e?.addEventListener(id==='cr-search'?'input':'change', () => this.load());
    });
    await this.load();
  },

  switchTab(tab, btn) {
    ['pohyby','import','parovanie'].forEach(t => {
      const el = document.getElementById('cr-tab-'+t);
      if (el) el.style.display = t === tab ? '' : 'none';
    });
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
  },

  async importOFX() {
    const input = document.getElementById('cr-file-ofx');
    if (!input.files.length) { App.toast('Vyberte súbor OFX', 'error'); return; }
    const form = new FormData();
    form.append('file', input.files[0]);
    const res = document.getElementById('cr-import-result');
    res.innerHTML = '<div class="loading">Importujem...</div>';
    try {
      const r = await fetch('/api/bank/import-ofx', { method: 'POST', body: form });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || 'Chyba importu');
      res.innerHTML = `<div class="alert alert-success">
        ✅ Importované: <strong>${data.imported}</strong> transakcií<br>
        Preskočené (duplikáty): ${data.skipped}<br>
        Spolu v súbore: ${data.total}
      </div>`;
      App.toast(`Importované ${data.imported} pohybov`, 'success');
      await this.load();
    } catch(e) {
      res.innerHTML = `<div class="alert alert-error">❌ ${e.message}</div>`;
    }
  },

  async importPDF() {
    const input = document.getElementById('cr-file-pdf');
    if (!input.files.length) { App.toast('Vyberte PDF súbor', 'error'); return; }
    const form = new FormData();
    form.append('file', input.files[0]);
    const res = document.getElementById('cr-import-result');
    res.innerHTML = '<div class="loading">Spracovávam PDF...</div>';
    try {
      const r = await fetch('/api/bank/import-pdf', { method: 'POST', body: form });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || 'Chyba importu PDF');
      res.innerHTML = `<div class="alert alert-success">
        ✅ Importované: <strong>${data.imported}</strong> transakcií<br>
        Preskočené (duplikáty): ${data.skipped}<br>
        Spolu nájdených: ${data.total}
      </div>`;
      App.toast(`Importované ${data.imported} pohybov z PDF`, 'success');
      await this.load();
    } catch(e) {
      res.innerHTML = `<div class="alert alert-error">❌ ${e.message}</div>`;
    }
  },

  async previewMatches() {
    const res = document.getElementById('cr-match-result');
    res.innerHTML = '<div class="loading">Hľadám zhody...</div>';
    try {
      const data = await API.get('/api/bank/match-preview');
      this.renderMatchResult(data, false);
    } catch(e) {
      res.innerHTML = `<div class="alert alert-error">❌ ${e.message}</div>`;
    }
  },

  async runMatch() {
    if (!confirm('Spárovať transakcie s faktúrami? Zostatok faktúr bude aktualizovaný.')) return;
    const res = document.getElementById('cr-match-result');
    res.innerHTML = '<div class="loading">Párujem...</div>';
    try {
      const data = await API.post('/api/bank/match-invoices', {});
      this.renderMatchResult(data, true);
      App.toast(`Spárované: ${data.matched_count} faktúr`, 'success');
    } catch(e) {
      res.innerHTML = `<div class="alert alert-error">❌ ${e.message}</div>`;
    }
  },

  renderMatchResult(data, applied) {
    const res = document.getElementById('cr-match-result');
    const matches = data.matches || data.matched || [];
    const unmatched = data.unmatched || [];
    let html = `<div class="kpi-grid" style="margin-bottom:16px">
      <div class="kpi-card"><div class="kpi-value" style="color:var(--green)">${matches.length}</div><div class="kpi-label">Spárovaných</div></div>
      <div class="kpi-card"><div class="kpi-value" style="color:var(--red)">${unmatched.length}</div><div class="kpi-label">Nespárovaných</div></div>
    </div>`;
    if (matches.length) {
      html += `<h4 style="margin:0 0 8px">✅ Spárované ${applied?'(aplikované)':'(náhľad)'}</h4>
      <div class="table-wrap" style="margin-bottom:16px"><table>
        <thead><tr><th>Č. FA</th><th>Odberateľ</th><th>Zaplatené</th><th>Zostatok pred</th><th>Zostatok po</th><th>Dátum</th></tr></thead>
        <tbody>${matches.map(m => `<tr>
          <td class="mono">${esc(m.cislo_faktury||'')}</td>
          <td>${esc(m.odberatel||m.name||'')}</td>
          <td class="cur cur-pos">${fmt_eur(m.trnamt)}</td>
          <td class="cur">${fmt_eur(m.zostava_uhradit!=null?m.zostava_uhradit:m.old_zostava)}</td>
          <td class="cur ${(m.new_zostava||0)<=0?'cur-pos':'cur-neg'}">${fmt_eur(m.new_zostava||0)}</td>
          <td>${esc(m.dtposted||'')}</td>
        </tr>`).join('')}</tbody>
      </table></div>`;
    }
    if (unmatched.length) {
      html += `<h4 style="margin:0 0 8px">❌ Nespárované platby</h4>
      <div class="table-wrap"><table>
        <thead><tr><th>ID pohybu</th><th>VS</th><th>Suma</th><th>Meno</th><th>Dátum</th><th>Akcia</th></tr></thead>
        <tbody>${unmatched.map(u => `<tr>
          <td class="mono">${u.credit_id}</td>
          <td class="mono">${esc(u.trnvasym||'')}</td>
          <td class="cur">${fmt_eur(u.trnamt)}</td>
          <td>${esc(u.name||'')}</td>
          <td>${esc(u.dtposted||'')}</td>
          <td><button class="btn btn-sm btn-secondary" onclick="Views.credits.manualMatchDialog(${u.credit_id},${u.trnamt})">Spárovať ručne</button></td>
        </tr>`).join('')}</tbody>
      </table></div>`;
    }
    res.innerHTML = html;
  },

  async manualMatchDialog(creditId, amt) {
    const cislo = prompt(`Zadajte číslo faktúry pre platbu ${fmt_eur(amt)}:`);
    if (!cislo) return;
    // Find invoice by number
    const invs = await API.get('/api/invoices?search=' + encodeURIComponent(cislo));
    const inv = invs.find(f => f.cislo_faktury === cislo);
    if (!inv) { App.toast('Faktúra nenájdená: ' + cislo, 'error'); return; }
    try {
      await API.post('/api/bank/manual-match', { credit_id: creditId, invoice_id: inv.id });
      App.toast('Platba spárovaná s faktúrou ' + cislo, 'success');
      await this.previewMatches();
    } catch(e) {
      App.toast('Chyba: ' + e.message, 'error');
    }
  },

  async load() {
    const params = new URLSearchParams({ limit: 300 });
    const s = document.getElementById('cr-search')?.value;
    const t = document.getElementById('cr-trntype')?.value;
    if (s) params.set('search', s);
    if (t) params.set('trntype', t);
    const data = await API.get('/api/credits?' + params);
    State.credits.data = data;
    const wrap = document.getElementById('cr-table-wrap');
    if (!wrap) return;
    if (!data.length) { wrap.innerHTML = '<div class="empty">Žiadne pohyby</div>'; return; }
    wrap.innerHTML = `<div class="table-wrap"><table>
      <thead><tr><th>ID</th><th>Typ</th><th>Dátum</th><th>Suma</th><th>Mena</th><th>Meno</th><th>IBAN</th><th>Memo</th><th>VS</th><th>Poznámka</th></tr></thead>
      <tbody>${data.map(c => {
        const amt = c.trnamt || 0;
        return `<tr onclick="Views.credits.openDetail(${c.id})">
          <td class="mono">${c.id}</td>
          <td><span class="tag ${c.trntype==='CREDIT'?'tag-green':'tag-red'}">${esc(c.trntype||'')}</span></td>
          <td>${fmtBankDate(c.dtposted)}</td>
          <td class="cur ${amt>=0?'cur-pos':'cur-neg'}">${fmt_eur(amt)}</td>
          <td>${esc(c.currency||'')}</td>
          <td class="td-truncate">${esc(c.name||'')}</td>
          <td class="mono" style="font-size:11px">${esc(c.iban4||c.iban||'')}</td>
          <td class="td-truncate">${esc(c.memo||'')}</td>
          <td class="mono">${esc(c.trnvasym||'')}</td>
          <td>${esc(c.poznamka||'')}</td>
        </tr>`;
      }).join('')}
      </tbody></table>
      <div class="pagination">
        <span>${data.length} pohybov | Suma: <strong>${fmt_eur(data.reduce((a,c)=>a+(c.trnamt||0),0))}</strong></span>
      </div>
    </div>`;
  },

  openDetail(id) {
    const c = State.credits.data.find(x => x.id === id) || {};
    const body = `<div class="detail-grid">
      ${dfield('Typ',c.trntype)} ${dfield('Dátum',fmtBankDate(c.dtposted))}
      ${dfield('Suma',fmt_eur(c.trnamt))} ${dfield('Mena',c.currency)}
      ${dfield('Meno',c.name,'full')}
      ${dfield('IBAN odosielateľa',c.iban4||c.iban,'full')}
      ${dfield('VS',c.trnvasym)} ${dfield('KS',c.trncosym)}
      ${dfield('Reference E2E',c.reference_e2e,'full')}
      ${dfield('Memo',c.memo,'full')}
      ${dfield('Poznámka',c.poznamka,'full')}
    </div>`;
    App.openDetail(`Pohyb #${c.id}`, body, () => this.openEdit(id));
  },

  openAdd() { this.openForm(null); },
  openEdit(id) { const c = State.credits.data.find(x => x.id === id); if (c) this.openForm(c); },

  openForm(c) {
    const v = k => esc(c?.[k] ?? '');
    const body = `<div class="form-grid">
      <div class="field"><label>Typ (CREDIT/DEBIT)</label><input id="fcr-trntype" value="${v('trntype')}"></div>
      <div class="field"><label>Suma</label><input type="number" step="0.01" id="fcr-trnamt" value="${c?.trnamt??''}"></div>
      <div class="field"><label>Mena</label><input id="fcr-currency" value="${v('currency')||'EUR'}"></div>
      <div class="field"><label>Dátum (YYYYMMDD)</label><input id="fcr-dtposted" value="${c?.dtposted??''}"></div>
      <div class="field form-full"><label>Meno</label><input id="fcr-name" value="${v('name')}"></div>
      <div class="field form-full"><label>IBAN protistrany</label><input id="fcr-iban4" value="${v('iban4')}"></div>
      <div class="field"><label>VS</label><input id="fcr-trnvasym" value="${v('trnvasym')}"></div>
      <div class="field"><label>KS</label><input id="fcr-trncosym" value="${v('trncosym')}"></div>
      <div class="field form-full"><label>Memo</label><input id="fcr-memo" value="${v('memo')}"></div>
      <div class="field form-full"><label>Reference E2E</label><input id="fcr-reference_e2e" value="${v('reference_e2e')}"></div>
      <div class="field form-full"><label>Poznámka</label><input id="fcr-poznamka" value="${v('poznamka')}"></div>
    </div>`;
    App.openModal(c ? 'Upraviť pohyb' : 'Nový bankový pohyb', body, c?.id, !!c);
  },

  async save() {
    const text = ['trntype','currency','name','iban4','trnvasym','memo','reference_e2e','poznamka'];
    const nums = ['trnamt','dtposted','trncosym'];
    const data = {};
    text.forEach(f => { data[f] = document.getElementById('fcr-'+f)?.value || null; });
    nums.forEach(f => { const e = document.getElementById('fcr-'+f); data[f] = e?.value !== '' ? parseFloat(e?.value) : null; });
    if (State.editId) await API.put('/api/credits/' + State.editId, data);
    else await API.post('/api/credits', data);
    App.closeModal();
    App.closeDetail();
    await this.load();
  },

  async delete() {
    if (!confirm('Odstraniť pohyb?')) return;
    await API.del('/api/credits/' + State.editId);
    App.closeModal();
    App.closeDetail();
    await this.load();
  },
};

// ─── IMPOSITION ──────────────────────────────────────────────────────────────
Views.imposition = {
  async render() {
    const cont = document.getElementById('content');
    cont.innerHTML = `
    <div class="filter-bar">
      <input type="search" id="imp-format" placeholder="Formát (A4, A5...)">
      <input type="search" id="imp-vazba" placeholder="Typ väzby...">
    </div>
    <div id="imp-table-wrap"><div class="loading">Načítavam...</div></div>`;
    ['imp-format','imp-vazba'].forEach(id => {
      document.getElementById(id)?.addEventListener('input', () => this.load());
    });
    await this.load();
  },

  async load() {
    const params = new URLSearchParams({ limit: 200 });
    const f = document.getElementById('imp-format')?.value;
    const v = document.getElementById('imp-vazba')?.value;
    if (f) params.set('format', f);
    if (v) params.set('vazba_typ', v);
    const data = await API.get('/api/imposition?' + params);
    State.imposition.data = data;
    const wrap = document.getElementById('imp-table-wrap');
    if (!wrap) return;
    if (!data.length) { wrap.innerHTML = '<div class="empty">Žiadne záznamy</div>'; return; }
    wrap.innerHTML = `<div class="table-wrap"><table>
      <thead><tr><th>ID</th><th>Formát</th><th>Väzba</th><th>Náklad</th><th>Strán</th><th>JPH</th><th>CPH</th><th>CPK</th><th>Typ</th></tr></thead>
      <tbody>${data.map(d => `<tr onclick="Views.imposition.openDetail(${d.id})">
        <td class="mono">${d.id}</td>
        <td>${esc(d.format||'')}</td>
        <td>${esc(d.vazba_typ||'')}</td>
        <td>${d.naklad??''}</td>
        <td>${d.stran??''}</td>
        <td class="cur">${fmt_eur(d.vn_jph)}</td>
        <td class="cur">${fmt_eur(d.vn_cph)}</td>
        <td class="cur">${fmt_eur(d.vn_cpk)}</td>
        <td>${esc(d.typ_vyradenia||'')}</td>
      </tr>`).join('')}
      </tbody></table>
      <div class="pagination"><span>${data.length} záznamov</span></div>
    </div>`;
  },

  openDetail(id) {
    const d = State.imposition.data.find(x => x.id === id) || {};
    const body = `
      <div class="detail-grid">
        ${dfield('ID',d.id)} ${dfield('Formát',d.format)}
        ${dfield('Typ väzby',d.vazba_typ)} ${dfield('Náklad',d.naklad)}
        ${dfield('Strán',d.stran)} ${dfield('Typ vyradenia',d.typ_vyradenia)}
      </div>
      <div class="detail-section"><h4>Ceny</h4><div class="detail-grid">
        ${dfield('JPH',fmt_eur(d.vn_jph))} ${dfield('CPH',fmt_eur(d.vn_cph))}
        ${dfield('JPK CB→CB',d.vn_jpk_cb_na_cb)} ${dfield('JPK FAR',d.vn_jpk_far)}
        ${dfield('JPK FAR znížený',d.vn_jpk_far_znizeny)} ${dfield('CPK CB→CB',d.vn_cpk_cb_na_cb)}
        ${dfield('CPK FAR',d.vn_cpk_far)} ${dfield('CPK',d.vn_cpk)}
        ${dfield('Kliky spolu V',fmt_eur(d.vn_kliky_spolu_v))}
      </div></div>
      ${d.pdftk_komplet ? `<div class="detail-section"><h4>PDFTK Komplet</h4><pre style="font-size:11px;white-space:pre-wrap;background:#f8fafc;padding:8px;border-radius:4px">${esc(d.pdftk_komplet)}</pre></div>` : ''}
      ${d.ako_vkladat ? `<div class="detail-section"><h4>Ako vkladať</h4><pre style="font-size:11px;white-space:pre-wrap;background:#f8fafc;padding:8px;border-radius:4px">${esc(d.ako_vkladat)}</pre></div>` : ''}
      ${d.statistika ? `<div class="detail-section"><h4>Štatistika</h4><pre style="font-size:11px;white-space:pre-wrap;background:#f8fafc;padding:8px;border-radius:4px">${esc(d.statistika)}</pre></div>` : ''}
    `;
    App.openDetail(`Vyradovanie #${d.id} – ${d.format||''} ${d.vazba_typ||''}`, body, () => {});
  },

  openAdd() { this.openForm(null); },
  openForm(d) {
    const v = k => esc(d?.[k] ?? '');
    const body = `<div class="form-grid">
      <div class="field"><label>Formát</label><input id="fd-format" value="${v('format')}"></div>
      <div class="field"><label>Väzba</label><input id="fd-vazba_typ" value="${v('vazba_typ')}"></div>
      <div class="field"><label>Náklad</label><input type="number" id="fd-naklad" value="${d?.naklad??''}"></div>
      <div class="field"><label>Strán</label><input type="number" id="fd-stran" value="${d?.stran??''}"></div>
      <div class="field"><label>JPH</label><input type="number" step="0.01" id="fd-vn_jph" value="${d?.vn_jph??''}"></div>
      <div class="field"><label>CPH</label><input type="number" step="0.01" id="fd-vn_cph" value="${d?.vn_cph??''}"></div>
      <div class="field"><label>Typ vyradenia</label><input id="fd-typ_vyradenia" value="${v('typ_vyradenia')}"></div>
      <div class="field form-full"><label>Retazec špecifikácie</label><input id="fd-retazec_specifikacie" value="${v('retazec_specifikacie')}"></div>
    </div>`;
    App.openModal(d ? `Upraviť vyradovanie #${d.id}` : 'Nový záznam vyradovania', body, d?.id, !!d);
  },

  async save() {
    const text = ['format','vazba_typ','typ_vyradenia','retazec_specifikacie'];
    const nums = ['naklad','stran','vn_jph','vn_cph'];
    const data = {};
    text.forEach(f => { data[f] = document.getElementById('fd-'+f)?.value || null; });
    nums.forEach(f => { const e = document.getElementById('fd-'+f); data[f] = e?.value !== '' ? parseFloat(e?.value) : null; });
    if (State.editId) await API.put('/api/imposition/' + State.editId, data);
    else await API.post('/api/imposition', data);
    App.closeModal();
    await this.load();
  },

  async delete() {
    if (!confirm('Odstraniť záznam?')) return;
    await API.del('/api/imposition/' + State.editId);
    App.closeModal();
    App.closeDetail();
    await this.load();
  },
};

// ─── SETTINGS ────────────────────────────────────────────────────────────────
Views.settings = {
  async render() {
    const cont = document.getElementById('content');
    cont.innerHTML = '<div class="loading">Načítavam...</div>';
    const lk = State.lookups;
    cont.innerHTML = `
      ${this.section('Stavy projektov', lk.stavy_projektov||[], 'stavy', 'nazov')}
      ${this.section('Status položky', lk.status_polozky||[], 'status-polozky', 'nazov')}
      ${this.section('Typy zákaziek', lk.typy_zakaziek||[], 'typy-zakaziek', 'nazov')}
      ${this.section('Typy odmien', lk.typy_odmeny||[], 'typy-odmeny', 'nazov')}
      ${this.section('Typy nákladov', lk.typy_nakladov||[], 'typy-nakladov', 'nazov')}
      ${this.section('Podfiltre projektov', lk.podfilter_projektov||[], 'podfilter', 'nazov')}
      ${this.sectionVazby(lk.vazby||[])}
      ${this.sectionDPH(lk.sadzby_dph||[])}
      ${this.sectionObalkaCeny(lk.obalka_ceny||[])}
    `;
    this.bindEvents();
  },

  section(title, rows, endpoint, field) {
    const rowsHtml = rows.map(r => `
      <div class="settings-row" data-id="${r.id}" data-endpoint="${endpoint}" data-field="${field}">
        <input class="field input" value="${esc(r[field]||'')}" style="flex:1;padding:5px 8px;border:1px solid var(--border);border-radius:4px;font-size:13px">
        <button class="btn-icon" onclick="Views.settings.saveRow(this)">💾</button>
        <button class="btn-icon" onclick="Views.settings.deleteRow(this)">🗑</button>
      </div>`).join('');
    return `<div class="settings-section">
      <div class="settings-section-header">
        <h3>${title}</h3>
        <button class="btn btn-sm btn-primary" onclick="Views.settings.addRow('${endpoint}','${field}',this)">+ Pridať</button>
      </div>
      <div class="settings-section-body" id="sb-${endpoint}">${rowsHtml}</div>
    </div>`;
  },

  sectionVazby(rows) {
    const rowsHtml = rows.map(r => `
      <div class="settings-row" data-id="${r.id}" data-endpoint="vazby">
        <input placeholder="Kód" value="${esc(r.vazba||'')}" style="width:100px;padding:5px;border:1px solid var(--border);border-radius:4px;font-size:13px" class="fv-vazba">
        <input placeholder="Popis" value="${esc(r.popis||'')}" style="flex:1;padding:5px;border:1px solid var(--border);border-radius:4px;font-size:13px" class="fv-popis">
        <button class="btn-icon" onclick="Views.settings.saveVazba(this)">💾</button>
        <button class="btn-icon" onclick="Views.settings.deleteRow(this)">🗑</button>
      </div>`).join('');
    return `<div class="settings-section">
      <div class="settings-section-header"><h3>Väzby</h3>
        <button class="btn btn-sm btn-primary" onclick="Views.settings.addVazba(this)">+ Pridať</button>
      </div>
      <div class="settings-section-body" id="sb-vazby">${rowsHtml}</div>
    </div>`;
  },

  sectionDPH(rows) {
    const rowsHtml = rows.map(r => `
      <div class="settings-row" data-id="${r.id}" data-endpoint="sadzby-dph">
        <input type="number" step="0.01" value="${r.sadzba??''}" style="width:100px;padding:5px;border:1px solid var(--border);border-radius:4px;font-size:13px" class="fv-sadzba">
        <span style="font-size:13px;color:var(--text-muted)">(${((r.sadzba||0)*100).toFixed(0)}%)</span>
        <button class="btn-icon" onclick="Views.settings.saveDPH(this)">💾</button>
        <button class="btn-icon" onclick="Views.settings.deleteRow(this)">🗑</button>
      </div>`).join('');
    return `<div class="settings-section">
      <div class="settings-section-header"><h3>Sadzby DPH</h3></div>
      <div class="settings-section-body" id="sb-sadzby-dph">${rowsHtml}</div>
    </div>`;
  },

  sectionObalkaCeny(rows) {
    const rowsHtml = rows.map(r => `
      <div class="settings-row" data-id="${r.id}" data-endpoint="obalka-ceny">
        <input placeholder="Farebnosť" value="${esc(r.farebnost||'')}" style="width:100px;padding:5px;border:1px solid var(--border);border-radius:4px;font-size:13px" class="fob-farebnost">
        <input type="number" step="0.0001" placeholder="JCV" value="${r.jcv??''}" style="width:120px;padding:5px;border:1px solid var(--border);border-radius:4px;font-size:13px" class="fob-jcv">
        <span style="font-size:12px;color:var(--text-muted)">(${((r.jcv||0)).toFixed(4)})</span>
        <button class="btn-icon" onclick="Views.settings.saveObalkaCena(this)">💾</button>
        <button class="btn-icon" onclick="Views.settings.deleteRow(this)">🗑</button>
      </div>`).join('');
    return `<div class="settings-section">
      <div class="settings-section-header"><h3>Ceny obálky (JCV)</h3>
        <button class="btn btn-sm btn-primary" onclick="Views.settings.addObalkaCena(this)">+ Pridať</button>
      </div>
      <div class="settings-section-body" id="sb-obalka-ceny">${rowsHtml}</div>
    </div>`;
  },

  async saveObalkaCena(btn) {
    const row = btn.closest('.settings-row');
    const id = row.dataset.id;
    const farebnost = row.querySelector('.fob-farebnost').value;
    const jcv = parseFloat(row.querySelector('.fob-jcv').value) || 0;
    await API.put(`/api/obalka-ceny/${id}`, { farebnost, jcv });
    await this.refreshLookups();
  },

  async addObalkaCena(btn) {
    const farebnost = prompt('Farebnosť (napr. 4+0):');
    if (!farebnost) return;
    const jcv = parseFloat(prompt('JCV (napr. 0.034):')) || 0;
    await API.post('/api/obalka-ceny', { farebnost, jcv });
    await this.refreshLookups();
    this.render();
  },

  bindEvents() {},

  async saveRow(btn) {
    const row = btn.closest('.settings-row');
    const id = row.dataset.id;
    const endpoint = row.dataset.endpoint;
    const field = row.dataset.field;
    const val = row.querySelector('input').value;
    await API.put(`/api/${endpoint}/${id}`, { [field]: val });
    await this.refreshLookups();
  },

  async saveVazba(btn) {
    const row = btn.closest('.settings-row');
    const id = row.dataset.id;
    const vazba = row.querySelector('.fv-vazba').value;
    const popis = row.querySelector('.fv-popis').value;
    await API.put(`/api/vazby/${id}`, { vazba, popis });
    await this.refreshLookups();
  },

  async saveDPH(btn) {
    const row = btn.closest('.settings-row');
    const id = row.dataset.id;
    const sadzba = parseFloat(row.querySelector('.fv-sadzba').value) || 0;
    await API.put(`/api/sadzby-dph/${id}`, { sadzba });
    await this.refreshLookups();
  },

  async deleteRow(btn) {
    if (!confirm('Odstraniť?')) return;
    const row = btn.closest('.settings-row');
    await API.del(`/api/${row.dataset.endpoint}/${row.dataset.id}`);
    row.remove();
    await this.refreshLookups();
  },

  async addRow(endpoint, field, btn) {
    const val = prompt('Nová hodnota:');
    if (!val) return;
    await API.post(`/api/${endpoint}`, { [field]: val });
    await this.refreshLookups();
    this.render();
  },

  async addVazba(btn) {
    const vazba = prompt('Kód väzby:');
    if (!vazba) return;
    const popis = prompt('Popis väzby:') || vazba;
    await API.post('/api/vazby', { vazba, popis });
    await this.refreshLookups();
    this.render();
  },

  async refreshLookups() {
    State.lookups = await API.get('/api/lookups');
  },
};

// ─── Helpers ─────────────────────────────────────────────────────────────────
function dfield(label, val, span) {
  const spanClass = span === 'full' ? ' style="grid-column:1/-1"' : '';
  return `<div class="detail-field"${spanClass}><div class="lbl">${esc(label)}</div><div class="val">${val ?? '—'}</div></div>`;
}
function pflag(label, val) {
  return `<span class="tag ${val?'tag-blue':''}">${val?'✓':''} ${esc(label)}</span>`;
}
function projFlags(p) {
  const on = [];
  if (p.projekt_expedovat) on.push('<span class="flag flag-exp on" title="Expedovať">📦</span>');
  if (p.projekt_sledovany) on.push('<span class="flag flag-sled on" title="Sledovaný">👁</span>');
  if (p.projekt_fakturovany) on.push('<span class="flag flag-fak on" title="Fakturovaný">🧾</span>');
  if (p.projekt_uhradeny) on.push('<span class="flag flag-uhr on" title="Uhradený">✅</span>');
  if (p.projekt_kreditny) on.push('<span class="tag tag-blue" title="Kreditný">K</span>');
  if (p.projekt_zberny) on.push('<span class="tag tag-orange" title="Zberný">Z</span>');
  if (p.projekt_kniha) on.push('<span class="tag tag-purple" title="Kniha">📗</span>');
  return `<div class="flags">${on.join('')}</div>`;
}
function itemsTable(items) {
  return `<div class="table-wrap"><table>
    <thead><tr><th>ID</th><th>Popis</th><th>MJ</th><th>Počet</th><th>Cena</th><th>s DPH</th><th>Status</th><th>Fak.</th></tr></thead>
    <tbody>${items.map(i => `<tr>
      <td class="mono">${i.id}</td>
      <td class="td-truncate">${esc(i.popis||'')}</td>
      <td>${esc(i.mj||'')}</td>
      <td>${i.pocet??''}</td>
      <td class="cur">${fmt_eur(i.cena)}</td>
      <td class="cur">${fmt_eur(i.cena_s_dph)}</td>
      <td>${statusBadge(i.status)}</td>
      <td>${i.fakturovane?'✅':i.fakturovat?'○':''}</td>
    </tr>`).join('')}
    </tbody></table></div>`;
}
function cbox(id, label, checked) {
  return `<label class="checkbox-item"><input type="checkbox" id="${id}" ${checked}> ${esc(label)}</label>`;
}
function chipLabel(k) {
  const m = {kreditny:'Kreditné',zberny:'Zberné',kniha:'Kniha',cp:'CP',oznaceny:'Označené',
    cakajuci:'Čakajúce',bezny:'Bežné',hotovo:'Hotovo',expedovat:'Expedovať',sledovany:'Sledované'};
  return m[k] || k;
}
function isoDate(v) {
  if (!v) return '';
  const d = new Date(v);
  if (isNaN(d)) return '';
  return d.toISOString().slice(0, 10);
}
function fmtBankDate(v) {
  if (!v) return '—';
  const s = String(Math.floor(v));
  if (s.length === 8) return `${s.slice(6,8)}.${s.slice(4,6)}.${s.slice(0,4)}`;
  return s;
}
function calcNakladCena() {
  const pocet = parseFloat(document.getElementById('fn-pocet')?.value) || 0;
  const jc = parseFloat(document.getElementById('fn-jc_vyroba')?.value) || 0;
  const vyroba = document.getElementById('fn-vyroba');
  if (vyroba) vyroba.value = (pocet * jc).toFixed(4);
}
function calcItemPrice() {
  const pocet = parseFloat(document.getElementById('fi-pocet')?.value) || 0;
  const jc = parseFloat(document.getElementById('fi-jc')?.value) || 0;
  const zlava = parseFloat(document.getElementById('fi-zlava')?.value) || 0;
  const dph = parseFloat(document.getElementById('fi-sadzba_dph')?.value) || 0;
  const cena = pocet * jc * (1 - zlava);
  const cena_dph = cena * (1 + dph);
  const cf = document.getElementById('fi-cena');
  const cdf = document.getElementById('fi-cena_s_dph');
  if (cf) cf.value = cena.toFixed(4);
  if (cdf) cdf.value = cena_dph.toFixed(4);
}
function switchTab(el, targetId) {
  const container = el.closest('.modal-body, .detail-body');
  if (!container) return;
  container.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  el.classList.add('active');
  const tabIds = ['tab-basic','tab-items','tab-naklady','tab-notes','tab-log',
                   'pf-basic','pf-finance','pf-flags','pf-notes',
                   'if-basic','if-tlac','if-expedia',
                   'fd-basic','fd-fakturacia','fd-kontakty',
                   'ff-basic','ff-fakturacia','ff-nastavenia','iqk-zakladne','iqk-transakcie-tab'];
  tabIds.forEach(id => {
    const el2 = document.getElementById(id);
    if (el2) el2.style.display = 'none';
  });
  const target = document.getElementById(targetId);
  if (target) target.style.display = '';
}


// ─── IQK ─────────────────────────────────────────────────────────────────────
Views.iqk = {
  async render() {
    const cont = document.getElementById('content');
    cont.innerHTML = `
    <div class="filter-bar">
      <input type="search" id="iqk-search" placeholder="Hľadať názov, ISBN, autora...">
      <button class="btn btn-secondary btn-sm" onclick="Views.iqk.load()">Načítať</button>
    </div>
    <div id="iqk-table-wrap"><div class="loading">Načítavam...</div></div>`;
    document.getElementById('iqk-search')?.addEventListener('input', () => this.load());
    await this.load();
  },

  async load() {
    const s = document.getElementById('iqk-search')?.value || '';
    const data = await API.get('/api/iqk/produkty?search=' + encodeURIComponent(s) + '&limit=200');
    const stat = await API.get('/api/iqk/statistika');
    const wrap = document.getElementById('iqk-table-wrap');
    if (!wrap) return;
    const statBar = `<div class="kpi-grid" style="margin-bottom:16px">
      <div class="kpi-card"><div class="kpi-value">${stat.produktov}</div><div class="kpi-label">Produktov</div></div>
      <div class="kpi-card"><div class="kpi-value">${stat.transakcii}</div><div class="kpi-label">Transakcií</div></div>
      <div class="kpi-card"><div class="kpi-value">${fmt_eur(stat.suma_celkom)}</div><div class="kpi-label">Celková suma</div></div>
    </div>`;
    if (!data.length) { wrap.innerHTML = statBar + '<div class="empty">Žiadne IQK produkty. Kliknite + Pridať na vytvorenie.</div>'; return; }
    wrap.innerHTML = statBar + `<div class="table-wrap"><table>
      <thead><tr><th>ID</th><th>Názov</th><th>ISBN</th><th>Autor</th><th>Vydavateľ</th><th>Rok</th><th>Strán</th><th>Náklad</th><th>Cena s DPH</th><th>Stav</th></tr></thead>
      <tbody>${data.map(p => `<tr onclick="Views.iqk.openDetail(${p.id})">
        <td class="mono">${p.id}</td>
        <td class="td-truncate" style="max-width:250px"><strong>${esc(p.nazov||'')}</strong></td>
        <td class="mono">${esc(p.isbn||'')}</td>
        <td>${esc(p.autor||'')}</td>
        <td>${esc(p.vydavatel||'')}</td>
        <td>${p.rok_vydania||''}</td>
        <td>${p.pocet_stran||''}</td>
        <td>${p.naklad||''}</td>
        <td class="cur">${fmt_eur(p.cena_s_dph)}</td>
        <td>${p.aktualny_stav||0}</td>
      </tr>`).join('')}</tbody></table>
      <div class="pagination"><span>${data.length} produktov</span></div>
    </div>`;
  },

  async openDetail(id) {
    const p = await API.get('/api/iqk/produkty/' + id);
    if (!p) return;
    const transakcie = await API.get('/api/iqk/produkty/' + id + '/transakcie');
    const tBody = transakcie.length ? `<div class="table-wrap"><table>
      <thead><tr><th>ID</th><th>Typ</th><th>Firma</th><th>Množstvo</th><th>JC</th><th>Suma</th><th>Dátum</th><th>Typ odmeny</th><th>Fak.</th></tr></thead>
      <tbody>${transakcie.map(t => `<tr>
        <td class="mono">${t.id}</td>
        <td><span class="tag">${esc(t.typ_transakcie||'')}</span></td>
        <td>${t.firma_id||''}</td>
        <td>${t.mnozstvo||0}</td>
        <td class="cur">${fmt_eur(t.jc)}</td>
        <td class="cur">${fmt_eur(t.suma)}</td>
        <td>${fmt_date(t.datum)}</td>
        <td>${esc(t.typ_odmeny||'')}</td>
        <td>${t.fakturovane?'✅':t.fakturovat?'○':''}</td>
      </tr>`).join('')}</tbody></table></div>` : '<div class="empty" style="padding:10px">Žiadne transakcie</div>';

    const jazyky = State.lookups.jazyky_iqk || [];
    const jazyk = jazyky.find(j => j.id === p.jazyk_id);
    const body = `
      <div class="tabs">
        <span class="tab active" onclick="switchTab(this,'iqk-zakladne')">Základné</span>
        <span class="tab" onclick="switchTab(this,'iqk-transakcie-tab')">Transakcie (${transakcie.length})</span>
      </div>
      <div id="iqk-zakladne">
        <div class="detail-grid">
          ${dfield('ID', p.id)} ${dfield('ISBN', p.isbn)}
          ${dfield('Názov', p.nazov, 'full')}
          ${dfield('Autor', p.autor)} ${dfield('Vydavateľ', p.vydavatel)}
          ${dfield('Rok vydania', p.rok_vydania)} ${dfield('Jazyk', jazyk ? (jazyk.jazyk_vydania + ' / ' + jazyk.jazyk_konkretne) : p.jazyk_id)}
          ${dfield('Počet strán', p.pocet_stran)} ${dfield('Náklad', p.naklad)}
          ${dfield('Cena bez DPH', fmt_eur(p.cena_bez_dph))} ${dfield('Sadzba DPH', p.sadzba_dph != null ? (p.sadzba_dph*100).toFixed(0)+'%' : '')}
          ${dfield('Cena s DPH', fmt_eur(p.cena_s_dph))} ${dfield('Aktuálny stav', p.aktualny_stav)}
        </div>
        ${p.poznamka ? `<div class="detail-section"><h4>Poznámka</h4><p style="font-size:13px">${esc(p.poznamka)}</p></div>` : ''}
      </div>
      <div id="iqk-transakcie-tab" style="display:none">
        ${tBody}
        <button class="btn btn-primary btn-sm" style="margin-top:10px" onclick="Views.iqk.openAddTransakcia(${p.id})">+ Pridať transakciu</button>
      </div>`;
    App.openDetail(p.nazov || 'IQK Produkt', body, () => this.openEdit(p.id));
  },

  openAdd() { this.openForm(null); },
  async openEdit(id) { const p = await API.get('/api/iqk/produkty/' + id); if (p) this.openForm(p); },

  openForm(p) {
    const v = k => esc(p?.[k] ?? '');
    const jazyky = State.lookups.jazyky_iqk || [];
    const jazOpts = jazyky.map(j => `<option value="${j.id}" ${p?.jazyk_id===j.id?'selected':''}>${esc(j.jazyk_vydania)} – ${esc(j.jazyk_konkretne||'')}</option>`).join('');
    const body = `<div class="form-grid">
      <div class="field form-full"><label>Názov</label><input id="iqk-nazov" value="${v('nazov')}"></div>
      <div class="field"><label>ISBN</label><input id="iqk-isbn" value="${v('isbn')}"></div>
      <div class="field"><label>Autor</label><input id="iqk-autor" value="${v('autor')}"></div>
      <div class="field"><label>Vydavateľ</label><input id="iqk-vydavatel" value="${v('vydavatel')}"></div>
      <div class="field"><label>Rok vydania</label><input type="number" id="iqk-rok_vydania" value="${p?.rok_vydania||''}"></div>
      <div class="field"><label>Jazyk</label><select id="iqk-jazyk_id"><option value="">—</option>${jazOpts}</select></div>
      <div class="field"><label>Počet strán</label><input type="number" id="iqk-pocet_stran" value="${p?.pocet_stran||''}"></div>
      <div class="field"><label>Náklad</label><input type="number" id="iqk-naklad" value="${p?.naklad||''}"></div>
      <div class="field"><label>Cena bez DPH</label><input type="number" step="0.01" id="iqk-cena_bez_dph" value="${p?.cena_bez_dph||''}"></div>
      <div class="field"><label>Sadzba DPH (0-1)</label><input type="number" step="0.01" id="iqk-sadzba_dph" value="${p?.sadzba_dph??0.1}"></div>
      <div class="field"><label>Cena s DPH</label><input type="number" step="0.01" id="iqk-cena_s_dph" value="${p?.cena_s_dph||''}"></div>
      <div class="field"><label>Aktuálny stav (ks)</label><input type="number" id="iqk-aktualny_stav" value="${p?.aktualny_stav||0}"></div>
      <div class="field form-full"><label>Poznámka</label><textarea id="iqk-poznamka">${v('poznamka')}</textarea></div>
    </div>`;
    App.openModal(p ? `Upraviť IQK produkt #${p.id}` : 'Nový IQK produkt', body, p?.id, !!p);
  },

  async save() {
    const text = ['nazov','isbn','autor','vydavatel','poznamka'];
    const nums = ['rok_vydania','pocet_stran','naklad','cena_bez_dph','sadzba_dph','cena_s_dph','aktualny_stav','jazyk_id'];
    const data = {};
    text.forEach(f => { data[f] = document.getElementById('iqk-'+f)?.value || null; });
    nums.forEach(f => { const e = document.getElementById('iqk-'+f); data[f] = e?.value !== '' ? parseFloat(e?.value)||null : null; });
    if (State.editId) await API.put('/api/iqk/produkty/' + State.editId, data);
    else await API.post('/api/iqk/produkty', data);
    showToast('IQK produkt uložený', 'success');
    App.closeModal();
    App.closeDetail();
    await this.load();
  },

  async delete() {
    if (!confirm('Odstraniť IQK produkt?')) return;
    await API.del('/api/iqk/produkty/' + State.editId);
    showToast('IQK produkt odstránený', 'info');
    App.closeModal();
    App.closeDetail();
    await this.load();
  },

  openAddTransakcia(produktId) {
    const typy = State.lookups.typy_odmeny || [];
    const typOpts = typy.map(t => `<option value="${esc(t.nazov)}">${esc(t.nazov)}</option>`).join('');
    const body = `<div class="form-grid">
      <div class="field"><label>Typ transakcie</label>
        <select id="it-typ_transakcie">
          <option value="dodanie">Dodanie</option>
          <option value="predaj">Predaj</option>
          <option value="vrátenie">Vrátenie</option>
          <option value="odmena">Odmena</option>
          <option value="fakturácia">Fakturácia</option>
        </select>
      </div>
      <div class="field"><label>Množstvo</label><input type="number" id="it-mnozstvo" value="0"></div>
      <div class="field"><label>Jednotková cena</label><input type="number" step="0.01" id="it-jc" value="0"></div>
      <div class="field"><label>Suma</label><input type="number" step="0.01" id="it-suma" value="0"></div>
      <div class="field"><label>Dátum</label><input type="date" id="it-datum" value="${new Date().toISOString().slice(0,10)}"></div>
      <div class="field"><label>Typ odmeny</label><select id="it-typ_odmeny"><option value="">—</option>${typOpts}</select></div>
      <div class="field form-full"><label>Poznámka</label><textarea id="it-poznamka"></textarea></div>
    </div>
    <div class="checkbox-row" style="margin-top:8px">
      ${cbox('it-fakturovat','Fakturovať','')} ${cbox('it-fakturovane','Fakturované','')}
    </div>`;
    App.openModal('Nová transakcia', body, null, false);
    document.getElementById('modal-save-btn').onclick = async () => {
      const data = {
        produkt_id: produktId,
        typ_transakcie: document.getElementById('it-typ_transakcie')?.value,
        mnozstvo: parseInt(document.getElementById('it-mnozstvo')?.value)||0,
        jc: parseFloat(document.getElementById('it-jc')?.value)||0,
        suma: parseFloat(document.getElementById('it-suma')?.value)||0,
        datum: document.getElementById('it-datum')?.value || null,
        typ_odmeny: document.getElementById('it-typ_odmeny')?.value || null,
        poznamka: document.getElementById('it-poznamka')?.value || null,
        fakturovat: !!document.getElementById('it-fakturovat')?.checked,
        fakturovane: !!document.getElementById('it-fakturovane')?.checked,
      };
      await API.post('/api/iqk/transakcie', data);
      showToast('Transakcia pridaná', 'success');
      App.closeModal();
      Views.iqk.openDetail(produktId);
    };
  },
};


// Patch Settings to add PovrchovaUprava and JazykyIQK sections
const _origSettingsRender = Views.settings.render.bind(Views.settings);
Views.settings.render = async function() {
  const cont = document.getElementById('content');
  cont.innerHTML = '<div class="loading">Načítavam...</div>';
  const lk = State.lookups;
  const usersHtml = await this.sectionUsers();
  cont.innerHTML = `
    ${usersHtml}
    ${this.sectionChangePassword()}
    ${this.section('Stavy projektov', lk.stavy_projektov||[], 'stavy', 'nazov')}
    ${this.section('Status položky', lk.status_polozky||[], 'status-polozky', 'nazov')}
    ${this.section('Typy zákaziek', lk.typy_zakaziek||[], 'typy-zakaziek', 'nazov')}
    ${this.section('Typy odmien', lk.typy_odmeny||[], 'typy-odmeny', 'nazov')}
    ${this.section('Typy nákladov', lk.typy_nakladov||[], 'typy-nakladov', 'nazov')}
    ${this.section('Podfiltre projektov', lk.podfilter_projektov||[], 'podfilter', 'nazov')}
    ${this.sectionVazby(lk.vazby||[])}
    ${this.sectionPovrchovaUprava(lk.povrchova_uprava||[])}
    ${this.sectionDPH(lk.sadzby_dph||[])}
    ${this.sectionObalkaCeny(lk.obalka_ceny||[])}
    ${this.sectionJazykyIQK(lk.jazyky_iqk||[])}
  `;
  this.bindEvents();
};

Views.settings.sectionPovrchovaUprava = function(rows) {
  const rowsHtml = rows.map(r => `
    <div class="settings-row" data-id="${r.id}" data-endpoint="povrchova-uprava">
      <input placeholder="Názov" value="${esc(r.nazov||'')}" style="flex:1;padding:5px;border:1px solid var(--border);border-radius:4px;font-size:13px" class="fpv-nazov">
      <input placeholder="Skratka" value="${esc(r.skratka||'')}" style="width:80px;padding:5px;border:1px solid var(--border);border-radius:4px;font-size:13px" class="fpv-skratka">
      <button class="btn-icon" onclick="Views.settings.savePovrchovaUprava(this)">💾</button>
      <button class="btn-icon" onclick="Views.settings.deleteRow(this)">🗑</button>
    </div>`).join('');
  return `<div class="settings-section">
    <div class="settings-section-header"><h3>Povrchová úprava</h3>
      <button class="btn btn-sm btn-primary" onclick="Views.settings.addPovrchovaUprava(this)">+ Pridať</button>
    </div>
    <div class="settings-section-body" id="sb-povrchova-uprava">${rowsHtml}</div>
  </div>`;
};

Views.settings.savePovrchovaUprava = async function(btn) {
  const row = btn.closest('.settings-row');
  const id = row.dataset.id;
  const nazov = row.querySelector('.fpv-nazov').value;
  const skratka = row.querySelector('.fpv-skratka').value;
  await API.put(`/api/povrchova-uprava/${id}`, { nazov, skratka });
  await this.refreshLookups();
};

Views.settings.addPovrchovaUprava = async function(btn) {
  const nazov = prompt('Povrchová úprava (napr. lesklé lamino):');
  if (!nazov) return;
  const skratka = prompt('Skratka (napr. LL):') || '';
  await API.post('/api/povrchova-uprava', { nazov, skratka });
  await this.refreshLookups();
  this.render();
};

Views.settings.sectionJazykyIQK = function(rows) {
  const rowsHtml = rows.map(r => `
    <div class="settings-row" data-id="${r.id}" data-endpoint="jazyky-iqk">
      <input placeholder="Jazyk vydania" value="${esc(r.jazyk_vydania||'')}" style="width:160px;padding:5px;border:1px solid var(--border);border-radius:4px;font-size:13px" class="fjq-vydania">
      <input placeholder="Konkrétny jazyk" value="${esc(r.jazyk_konkretne||'')}" style="flex:1;padding:5px;border:1px solid var(--border);border-radius:4px;font-size:13px" class="fjq-konkretne">
      <input placeholder="Preklad" value="${esc(r.jazyk_preklad||'')}" style="width:120px;padding:5px;border:1px solid var(--border);border-radius:4px;font-size:13px" class="fjq-preklad">
      <button class="btn-icon" onclick="Views.settings.saveJazyk(this)">💾</button>
      <button class="btn-icon" onclick="Views.settings.deleteRow(this)">🗑</button>
    </div>`).join('');
  return `<div class="settings-section">
    <div class="settings-section-header"><h3>Jazyky IQK</h3>
      <button class="btn btn-sm btn-primary" onclick="Views.settings.addJazyk(this)">+ Pridať</button>
    </div>
    <div class="settings-section-body" id="sb-jazyky-iqk">${rowsHtml}</div>
  </div>`;
};

Views.settings.saveJazyk = async function(btn) {
  const row = btn.closest('.settings-row');
  const id = row.dataset.id;
  const jazyk_vydania = row.querySelector('.fjq-vydania').value;
  const jazyk_konkretne = row.querySelector('.fjq-konkretne').value;
  const jazyk_preklad = row.querySelector('.fjq-preklad').value;
  await API.put(`/api/jazyky-iqk/${id}`, { jazyk_vydania, jazyk_konkretne, jazyk_preklad });
  await this.refreshLookups();
};

Views.settings.addJazyk = async function(btn) {
  const jazyk_vydania = prompt('Jazyk vydania:');
  if (!jazyk_vydania) return;
  const jazyk_konkretne = prompt('Konkrétny jazyk:') || '';
  await API.post('/api/jazyky-iqk', { jazyk_vydania, jazyk_konkretne, jazyk_preklad: '' });
  await this.refreshLookups();
  this.render();
};


// ─── USER MANAGEMENT (Settings) ──────────────────────────────────────────────
Views.settings.sectionUsers = async function() {
  if (!State.currentUser?.is_admin) {
    return `<div class="settings-section"><div class="settings-section-header"><h3>Môj účet</h3></div>
      <div class="settings-section-body" style="padding:12px;font-size:13px;color:var(--text-muted)">
        Prihlásený ako: <strong>${esc(State.currentUser?.plne_meno || State.currentUser?.username || '')}</strong>
      </div></div>`;
  }
  const users = await API.get('/api/auth/users');
  if (!users) return '';
  const rows = users.map(u => `
    <div class="settings-row" style="align-items:center;gap:8px">
      <span style="min-width:120px;font-weight:500">${esc(u.username)}</span>
      <span style="min-width:160px;color:var(--text-muted);font-size:12px">${esc(u.plne_meno||'')}</span>
      <span class="tag ${u.is_admin?'tag-green':'tag-gray'}" style="font-size:11px">${u.is_admin?'Admin':'Používateľ'}</span>
      <span class="tag ${u.active?'tag-green':'tag-red'}" style="font-size:11px">${u.active?'Aktívny':'Neaktívny'}</span>
      <span style="font-size:11px;color:var(--text-muted)">${u.has_password?'✅ má heslo':'⚠️ bez hesla'}</span>
      <div style="margin-left:auto;display:flex;gap:4px">
        <button class="btn btn-sm btn-secondary" onclick="Views.settings.setUserPassword(${u.id},'${esc(u.username)}')">Nastaviť heslo</button>
        <button class="btn btn-sm btn-secondary" onclick="Views.settings.toggleAdmin(${u.id})">Admin: ${u.is_admin?'Odobrať':'Pridať'}</button>
        <button class="btn btn-sm ${u.active?'btn-danger':'btn-secondary'}" onclick="Views.settings.toggleActive(${u.id})">${u.active?'Deaktivovať':'Aktivovať'}</button>
      </div>
    </div>`).join('');
  return `<div class="settings-section">
    <div class="settings-section-header"><h3>Správa používateľov</h3></div>
    <div class="settings-section-body">${rows || '<div style="padding:12px;color:var(--text-muted)">Žiadni používatelia</div>'}</div>
  </div>`;
};

Views.settings.sectionChangePassword = function() {
  return `<div class="settings-section">
    <div class="settings-section-header"><h3>Zmena hesla</h3></div>
    <div class="settings-section-body" style="padding:12px">
      <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:flex-end">
        <div class="field" style="margin:0"><label style="font-size:12px">Staré heslo</label><input type="password" id="cp-old" style="padding:6px 10px;border:1px solid var(--border);border-radius:6px;font-size:13px;width:160px"></div>
        <div class="field" style="margin:0"><label style="font-size:12px">Nové heslo</label><input type="password" id="cp-new" style="padding:6px 10px;border:1px solid var(--border);border-radius:6px;font-size:13px;width:160px"></div>
        <div class="field" style="margin:0"><label style="font-size:12px">Zopakovať</label><input type="password" id="cp-new2" style="padding:6px 10px;border:1px solid var(--border);border-radius:6px;font-size:13px;width:160px"></div>
        <button class="btn btn-primary btn-sm" onclick="Views.settings.changePassword()">Zmeniť heslo</button>
      </div>
    </div>
  </div>`;
};

Views.settings.setUserPassword = async function(uid, username) {
  const pwd = prompt(`Nové heslo pre používateľa "${username}":`);
  if (!pwd) return;
  const r = await API.post(`/api/auth/users/${uid}/set-password`, { password: pwd });
  if (r?.ok) { App.toast(`Heslo nastavené pre ${username}`, 'success'); Views.settings.render(); }
  else App.toast(r?.detail || 'Chyba', 'error');
};

Views.settings.toggleAdmin = async function(uid) {
  const r = await API.post(`/api/auth/users/${uid}/toggle-admin`, {});
  if (r?.ok) { App.toast('Admin práva aktualizované', 'success'); Views.settings.render(); }
};

Views.settings.toggleActive = async function(uid) {
  const r = await API.post(`/api/auth/users/${uid}/toggle-active`, {});
  if (r?.ok) { App.toast('Stav používateľa aktualizovaný', 'success'); Views.settings.render(); }
};

Views.settings.changePassword = async function() {
  const old = document.getElementById('cp-old')?.value || '';
  const np = document.getElementById('cp-new')?.value || '';
  const np2 = document.getElementById('cp-new2')?.value || '';
  if (np !== np2) { App.toast('Heslá sa nezhodujú', 'error'); return; }
  if (np.length < 4) { App.toast('Heslo musí mať aspoň 4 znaky', 'error'); return; }
  const r = await API.post('/api/auth/change-password', { old_password: old, new_password: np });
  if (r?.ok) { App.toast('Heslo zmenené', 'success'); document.getElementById('cp-old').value=''; document.getElementById('cp-new').value=''; document.getElementById('cp-new2').value=''; }
  else App.toast(r?.detail || 'Chyba', 'error');
};

// ── Boot ──────────────────────────────────────────────────────────────────────
window.App = App;
window.Views = Views;
window.switchTab = switchTab;
window.calcItemPrice = calcItemPrice;
window.calcNakladCena = calcNakladCena;
window.showToast = showToast;
window.State = State;
document.addEventListener('DOMContentLoaded', () => App.init());
