/*
  app.js
  ======
  Base estable por cuadrantes (Q1..Q4), polling a /estados/estado_global.

  ✅ Cambios en ESTA versión (solo Q2: Orden del día):
  --------------------------------------------------
  1) CSV con comillas dobles (estilo RFC4180) para permitir comas en "tema".
  2) Header obligatorio y exacto:
       nro_votacion,tipo,tema,factor_de_mayoria,respecto
     - sin comillas
     - sin espacios
     - sin columnas extra/faltantes
  3) tipo y respecto NO son case-sensitive:
     - acepta "despacho", "DESPACHO", "Despacho" etc.
     - acepta "presentes"/"cuerpo" en cualquier combinación de mayúsculas.
  4) factor_de_mayoria:
     - "" o "0" => se considera 0
     - ".66", "0.66", "1", "1.0" => permitido (decimal con punto)
     - NO se permite "%" ni coma decimal.
  5) Si el CSV es inválido: se rechaza el archivo completo y la tabla queda vacía.

  ⚠ Nota sobre el selector de archivos:
  - Por seguridad, JS no puede elegir la carpeta inicial.
  - Normalmente el navegador/OS ya abre en la última carpeta utilizada.
*/

///////////////////////////////
// 1) CONFIG
///////////////////////////////
const API_BASE_URL = "";
const STATE_ENDPOINT = "/estados/estado_global";
const POLL_MS = 300;
const TIMEOUT_MS = 1500;
const VOTACION_RESULT_MS = 6000; // tiempo visible del resultado tras cierre

///////////////////////////////
// 2) BUS SIMPLE (desacople)
///////////////////////////////
const bus = (() => {
  const handlers = new Map();

  function on(name, fn){
    if (!handlers.has(name)) handlers.set(name, new Set());
    handlers.get(name).add(fn);
    return () => off(name, fn);
  }

  function off(name, fn){
    const set = handlers.get(name);
    if (!set) return;
    set.delete(fn);
    if (set.size === 0) handlers.delete(name);
  }

  function emit(name, payload){
    const set = handlers.get(name);
    if (!set) return;
    for (const fn of set){
      try { fn(payload); } catch(_e) {}
    }
  }

  return { on, off, emit };
})();

///////////////////////////////
// 3) DOM GLOBAL
///////////////////////////////
const connText = document.getElementById("connText");
const clockEl  = document.getElementById("clock");
const toastEl  = document.getElementById("toast");
const hdrSesionInfo = document.getElementById("hdrSesionInfo");
const hdrQuorumDelta = document.getElementById("hdrQuorumDelta");



///////////////////////////////
// 4) RELOJ
///////////////////////////////
function updateClock(){
  if (!clockEl) return;
  clockEl.textContent = new Date().toLocaleString("es-AR");
}
updateClock();
setInterval(updateClock, 250);

///////////////////////////////
// 5) UI: CONEXION + TOAST
///////////////////////////////
function setConn(kind, text){
  if (!connText) return;

  connText.classList.remove("conn-ok","conn-err","conn-warn");
  if (kind === "ok") connText.classList.add("conn-ok");
  else if (kind === "err") connText.classList.add("conn-err");
  else connText.classList.add("conn-warn");

  connText.textContent = text;
}

let toastTimer = null;

function toast(kind, msg, ms = 2500){
  if (!toastEl) return;

  toastEl.classList.remove("toast--ok","toast--err","toast--warn","toast--show");

  if (kind === "ok") toastEl.classList.add("toast--ok");
  else if (kind === "err") toastEl.classList.add("toast--err");
  else toastEl.classList.add("toast--warn");

  toastEl.textContent = msg;
  toastEl.classList.add("toast--show");

  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    toastEl.classList.remove("toast--show");
  }, ms);
}

///////////////////////////////
// 6) FETCH con TIMEOUT
///////////////////////////////
async function fetchWithTimeout(url, options = {}, timeoutMs = TIMEOUT_MS){
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try{
    return await fetch(url, { ...options, signal: controller.signal });
  } finally {
    clearTimeout(timer);
  }
}

async function getJson(url){
  const res = await fetchWithTimeout(url, {
    method: "GET",
    headers: { "Accept":"application/json" },
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

async function postJson(url, body){
  const res = await fetchWithTimeout(url, {
    method: "POST",
    headers: { "Content-Type":"application/json", "Accept":"application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  const text = await res.text();
  if (!res.ok) throw new Error(`HTTP ${res.status} - ${text}`);

  try { return JSON.parse(text); }
  catch { return { ok:true, raw:text }; }
}

///////////////////////////////
// 7) NORMALIZACION DE ESTADO
///////////////////////////////
function normalizeState(raw){
  if (!raw) return { sesion: null };
  if (raw.sesion !== undefined) return raw;
  return { sesion: raw };
}

function getSesion(state){
  const ses = state?.sesion;
  return ses && typeof ses === "object" ? ses : null;
}

function getVotaciones(state){
  const ses = getSesion(state);
  return Array.isArray(ses?.votaciones) ? ses.votaciones : [];
}

function getUltimaVotacion(state){
  const vs = getVotaciones(state);
  return vs.length ? vs[vs.length - 1] : null;
}

/* Eventos pueden venir en state.eventos (lo pedido) */
function getEventosFromState(raw){
  const state = normalizeState(raw);
  if (Array.isArray(state?.eventos)) return state.eventos;

  const ses = getSesion(state);
  if (Array.isArray(ses?.eventos)) return ses.eventos;

  return [];
}

///////////////////////////////
// 8) UI MODEL (toggle respecto)
///////////////////////////////
const uiModel = { respectoPresentes: true };


///////////////////////////////
// 8.5) header
///////////////////////////////
function updateHeaderSesionInfo(raw){
  if (!hdrSesionInfo || !hdrQuorumDelta) return;

  const state = normalizeState(raw);
  const ses = getSesion(state);

  if (!ses || ses.abierta === false){
    hdrSesionInfo.textContent = "";
    hdrQuorumDelta.textContent = "";
    hdrQuorumDelta.classList.remove("num-good","num-bad","num-neutral");
    return;
  }

  const nro = (ses.numero_sesion ?? "–");

  // Total
  let total = ses.cantidad_concejales;
  if (!Number.isInteger(total)){
    const cc = Array.isArray(ses.concejales) ? ses.concejales : [];
    total = cc.length;
  }

  // Presentes
  let presentes = ses.cantidad_presentes;
  if (!Number.isInteger(presentes)){
    const cc = Array.isArray(ses.concejales) ? ses.concejales : [];
    presentes = cc.filter(c => c?.presente === true).length;
  }

  // Texto base (MISMO estilo que el título)
  hdrSesionInfo.textContent =
    ` · Sesión Nº ${nro} - Concejales ${presentes} de ${total} totales - Quorum:`;

  // Delta
  hdrQuorumDelta.classList.remove("num-good","num-bad","num-neutral");

  const quorum = Number.isInteger(ses.quorum) ? ses.quorum : null;
  if (quorum === null){
    hdrQuorumDelta.textContent = "–";
    hdrQuorumDelta.classList.add("num-neutral");
    return;
  }

  const delta = presentes - quorum;
  const deltaTxt = (delta > 0) ? `+${delta}` : `${delta}`;

  hdrQuorumDelta.textContent = deltaTxt;

  if (delta >= 0) hdrQuorumDelta.classList.add("num-good");
  else hdrQuorumDelta.classList.add("num-bad");
}




///////////////////////////////
// 9) Q1 (Comandos)
///////////////////////////////
const Q1 = (() => {
  
  const votacionNormal = document.getElementById("votacionNormal");
  
  const q1VotacionResumen = document.getElementById("q1VotacionResumen");

  const inVotTema = document.getElementById("inVotTema");
  const votacionEstado = document.getElementById("votacionEstado");

  let lastVotRef = null;
  let clearStatusTimer = null;    // timer de blanqueo diferido
  let blankedVotId = null;        // idLike de la última votación que ya “permitimos blanquear”

  function clearQ1EstadoBg(){
    if (!votacionEstado) return;
    votacionEstado.classList.remove("q1-res-pos","q1-res-neg","q1-res-abs");
  }

  function setQ1EstadoBgByEstado(estado){
    if (!votacionEstado) return;

    // Siempre arrancamos limpio
    clearQ1EstadoBg();

    // Mapeo estado -> color (mismos colores que los fondos de concejales)
    if (estado === "APROBADA") votacionEstado.classList.add("q1-res-pos");
    else if (estado === "RECHAZADA") votacionEstado.classList.add("q1-res-neg");
    else if (estado === "EMPATADA") votacionEstado.classList.add("q1-res-abs");
  }

  function clearQ1StatusTexts(){
    // Estos son los .statusbox__text de Q1 que hoy repinta renderVotacionEstado()
    const resumen = document.getElementById("q1VotacionResumen");
    if (resumen) resumen.textContent = "-";
    if (inVotTema) inVotTema.textContent = "-";
    if (votacionEstado) votacionEstado.textContent = "-";
    clearQ1EstadoBg();
  }

  // function setModoEmpate(isEmpate){
  //   if (votacionNormal) votacionNormal.style.display = isEmpate ? "none" : "";
  // }

  function textoResultadoHumano(estado){
    if (estado === "APROBADA") return "Aprobada";
    if (estado === "RECHAZADA") return "Rechazada";
    if (estado === "EMPATADA") return "Empatada";
    if (estado === "EN_CURSO") return "En curso";
    if (estado === "INCONCLUSA") return "Inconclusa";
    return String(estado || "");
  }

  function contarVotos(votacion){
    const votos = Array.isArray(votacion?.votos) ? votacion.votos : [];
    let positivos = 0, negativos = 0, abstenciones = 0;

    for (const v of votos){
      const val = v?.valor_voto;
      if (val === "Positivo") positivos++;
      else if (val === "Negativo") negativos++;
      else if (val === "Abstencion") abstenciones++;
    }

    return { x: votos.length, positivos, negativos, abstenciones };
  }

  function isMayoríaEspecialCeroOVacia(f){
    const s = String(f ?? "").trim();
    if (s === "") return true;
    // permitimos que venga número o string
    const n = Number(String(s).replace(",", "."));
    if (!Number.isFinite(n)) return true;
    return n <= 0;
  }

  function buildTextoResumenVotacion(raw){
    const state = normalizeState(raw);
    const ultima = getUltimaVotacion(state);

    if (!ultima) return "No hay votación en curso.";

    const tipo = String(ultima?.tipo ?? "–");
    const numero = String(ultima?.numero ?? "–");

    const respecto = (ultima?.computa_sobre_los_presentes === true) ? "Presentes" : "Cuerpo";

    const fRaw = (ultima?.factor_mayoria_especial ?? "");
    const sinMayoriaEspecial = isMayoríaEspecialCeroOVacia(fRaw);

    if (sinMayoriaEspecial){
      return `Tipo "${tipo}" Nº${numero} sin mayoria especial, computando sobre "${respecto}".`;
    }

    const factorTxt = String(fRaw).trim();
    return `Tipo "${tipo}" Nº${numero} con mayoria especial de ${factorTxt}, computando sobre "${respecto}".`;
  }

  function renderResumenVotacion(raw){
    if (!q1VotacionResumen) return;
    q1VotacionResumen.textContent = buildTextoResumenVotacion(raw);
  }


  function construirTextoEstadoVotacion(state){
    const ultima = getUltimaVotacion(state);

    if (!ultima){
      return { modoEmpate: false, textoNormal: "-", textoEmpate: "-" };
    }

    const { x, positivos, negativos, abstenciones } = contarVotos(ultima);

    const numero = ultima?.numero ?? "?";
    const estado = ultima?.estado;

    if (estado === "EN_CURSO"){
      const texto =
        `Votacion Nº${numero} en curso: ${x} votos (` +
        `${positivos} positivos, ${negativos} negativos y ${abstenciones} abstenciones.)`;
      return { modoEmpate: false, textoNormal: texto, textoEmpate: texto };
    }

    if (estado === "EMPATADA"){
      const texto =
        `Votacion Nº${numero} empatada: ${x} votos (` +
        `${positivos} positivos, ${negativos} negativos y ${abstenciones} abstenciones.)`;
      return { modoEmpate: true, textoNormal: texto, textoEmpate: texto };
    }

    const estadoHumano = textoResultadoHumano(estado);
    const texto =
      `Votacion Nº${numero} "${estadoHumano}": ` +
      `${x} votos (${positivos} positivos, ${negativos} negativos y ${abstenciones} abstenciones.)`;

    return { modoEmpate: false, textoNormal: texto, textoEmpate: texto };
  }


  function renderVotacionEstado(raw){
    const state = normalizeState(raw);
    
    // Q1: Si hay votación abierta (EN_CURSO o EMPATADA), fijar y bloquear campos
    const ultima = getUltimaVotacion(state);
    // const estadoUlt = String(ultima?.estado ?? "");
    // const votAbierta = isEstadoAbiertoOVivo(estadoUlt);

      // Tema (solo display)
    if (inVotTema){
      inVotTema.textContent = String(ultima?.tema ?? "-");
    }

    // Si ya blanqueamos la última votación cerrada, NO repintar sus textos
    //const ultima = getUltimaVotacion(state);
    if (ultima){
      const idLike = (ultima.id !== undefined && ultima.id !== null)
        ? String(ultima.id)
        : String(ultima.numero ?? "");

      const est = String(ultima.estado ?? "");

      // Si es la misma votación que blanqueamos y ya NO está en curso/empatada -> mantener en blanco
      if (blankedVotId && blankedVotId === idLike && !isEstadoAbiertoOVivo(est)){
        if (votacionEstado) votacionEstado.textContent = "-";
        const resumen = document.getElementById("q1VotacionResumen");
        if (resumen) resumen.textContent = "-";
        if (inVotTema) inVotTema.textContent = "-";

        return; // MUY importante: corta acá para que no repinte con construirTextoEstadoVotacion()
      }

      // Si aparece una votación nueva o vuelve a “viva”, destrabamos
      if (blankedVotId && blankedVotId !== idLike){
        blankedVotId = null;
      }
      if (blankedVotId && isEstadoAbiertoOVivo(est)){
        blankedVotId = null;
      }
    }


    const out = construirTextoEstadoVotacion(state);
    // setModoEmpate(out.modoEmpate);
    if (votacionEstado) votacionEstado.textContent = out.textoNormal;
  }

  function isEstadoAbiertoOVivo(estado){
    return (estado === "EN_CURSO" || estado === "EMPATADA");
  }

  function detectAndHandleVotacionFinalizada(raw){
    const state = normalizeState(raw);
    const ultima = getUltimaVotacion(state);

    if (!ultima){
      lastVotRef = null;
      if (clearStatusTimer) clearTimeout(clearStatusTimer);
      clearStatusTimer = null;
      blankedVotId = null;
      clearQ1EstadoBg();
      return;
    }


    const idLike = (ultima.id !== undefined && ultima.id !== null)
      ? String(ultima.id)
      : String(ultima.numero ?? "");

    const estado = String(ultima.estado ?? "");
    const current = { id: idLike, estado };

    if (lastVotRef && lastVotRef.id === current.id){
      const before = String(lastVotRef.estado ?? "");
      const after  = String(current.estado ?? "");

      if (isEstadoAbiertoOVivo(before) && !isEstadoAbiertoOVivo(after)){
      
        // Cancelamos un blanqueo previo si lo hubiera
        if (clearStatusTimer) clearTimeout(clearStatusTimer);

        setQ1EstadoBgByEstado(after);

        // Programamos blanqueo a los x seg del cierre
        clearStatusTimer = setTimeout(() => {
          blankedVotId = current.id;     // “marcamos” esta votación como ya blanqueada
          clearQ1StatusTexts();          // limpiamos textos
          clearStatusTimer = null;
        }, VOTACION_RESULT_MS);
      }

    }

    lastVotRef = current;
  }


  function init(){

    // Render inicial
    renderVotacionEstado(null);
    renderResumenVotacion(null);
    lastVotRef = null;
  }

  function onState(raw){
    const norm = normalizeState(raw);
    detectAndHandleVotacionFinalizada(raw);
    renderResumenVotacion(raw);
    renderVotacionEstado(raw);
  }

  function onError(_e){}

  return { init, onState, onError };
})();


///////////////////////////////
// 11) Q3 (Estado recinto)
///////////////////////////////
const Q3 = (() => {
  const recintoCanvas = document.getElementById("recintoCanvas");
  const recintoError  = document.getElementById("recintoError");

  const ulUsoPalabra  = document.getElementById("ulUsoPalabra");

  // Cache de layout (disposición no cambia durante la sesión)
  let cachedSesionKey = null;
  let cachedDispoStr = null;
  let cachedLayout = null; // { filasSorted, maxCols, sumCols }

  // Bancas renderizadas: Map<bancaNro, { voteEl }>
  let bancaEls = new Map();

  // Estado de votación para lógica de “blanqueo”
  let activeVotRef = null;
  let clearVotesTimer = null;

  function sesionKey(sesion){
    if (!sesion) return null;
    const n = (sesion.numero_sesion !== undefined && sesion.numero_sesion !== null) ? String(sesion.numero_sesion) : "";
    const h = String(sesion.hora_inicio ?? "");
    return `${n}|${h}`;
  }

  function resetCache(){
    cachedSesionKey = null;
    cachedDispoStr = null;
    cachedLayout = null;
    bancaEls = new Map();

    activeVotRef = null;
    if (clearVotesTimer) clearTimeout(clearVotesTimer);
    clearVotesTimer = null;

    clearLeft();
    clearRight();
    hideLeftError();
  }

  function clearLeft(){
    if (recintoCanvas) recintoCanvas.innerHTML = "";
    bancaEls = new Map();
  }

  function clearRight(){
    if (ulUsoPalabra) ulUsoPalabra.innerHTML = "";
  }

  function showLeftError(msg){
    // Error SOLO en panel izquierdo
    if (!recintoCanvas) return;
    recintoCanvas.innerHTML = "";
    const div = document.createElement("div");
    div.className = "recintoCanvasError";
    div.textContent = msg;
    recintoCanvas.appendChild(div);

    // y mostramos el hint del panel derecho SOLO si ya existe en el DOM,
    // pero la premisa dice que NO debemos mostrar el error en el panel derecho.
    // Por eso lo dejamos oculto.
    if (recintoError) recintoError.style.display = "none";
  }

  function hideLeftError(){
    if (recintoError) recintoError.style.display = "none";
  }

  function safeJsonParse(str){
    try{
      return JSON.parse(String(str ?? ""));
    } catch(_e){
      return null;
    }
  }

  function computeLayout(dispoStr){
    const parsed = safeJsonParse(dispoStr);
    const filas = Array.isArray(parsed?.filas) ? parsed.filas : null;
    if (!filas) return null;

    // Normalizamos y ordenamos por "fila" asc (fila 1 es la más baja)
    const filasNorm = filas
      .map(f => ({
        fila: Number(f?.fila),
        columnas: Number(f?.columnas),
      }))
      .filter(f => Number.isFinite(f.fila) && Number.isFinite(f.columnas) && f.columnas > 0);

    if (!filasNorm.length) return null;

    filasNorm.sort((a,b) => a.fila - b.fila);

    const sumCols = filasNorm.reduce((acc, f) => acc + f.columnas, 0);
    const maxCols = filasNorm.reduce((acc, f) => Math.max(acc, f.columnas), 0);

    return { filasSorted: filasNorm, sumCols, maxCols };
  }

  function setInnerWidthPx(maxCols){
    if (!recintoCanvas) return;

    // Gap entre celdas: 8px (ver CSS .recintoRow)
    const gap = 8;
    const w = recintoCanvas.clientWidth || 0;
    if (!w || !Number.isFinite(maxCols) || maxCols <= 0) return;

    // Aproximación: ancho de celda en la fila más cargada (maxCols)
    const totalGaps = (maxCols - 1) * gap;
    const cellW = (w - totalGaps) / maxCols;
    const innerW = Math.max(20, Math.floor(cellW * 0.92));

    recintoCanvas.style.setProperty("--bancaInnerW", `${innerW}px`);
  }

  function buildLeft(sesion){
    if (!recintoCanvas) return;

    const dispoStr = String(sesion?.disposicion_bancas ?? "");
    const layout = computeLayout(dispoStr);
    if (!layout){
      showLeftError("Error: disposicion_bancas inválida o sin filas.");
      return;
    }

    const concejales = Array.isArray(sesion?.concejales) ? sesion.concejales : [];
    if (layout.sumCols !== concejales.length){
      showLeftError(
        `Error: sum(columnas)=${layout.sumCols} no coincide con cantidad de concejales=${concejales.length}.`
      );
      return;
    }

    // Cacheamos
    cachedDispoStr = dispoStr;
    cachedLayout = layout;

    // Render
    recintoCanvas.innerHTML = "";
    bancaEls = new Map();
    hideLeftError();

    // Armamos una lista ordenada de concejales según banca (1..N)
    const concejalesByBanca = new Map();
    for (const c of concejales){
      const b = Number(c?.banca);
      if (Number.isFinite(b)) concejalesByBanca.set(b, c);
    }

    const totalBancas = concejales.length;

    // Numeración de bancas (REGLA): banca 1 = abajo-izquierda, luego izquierda→derecha,
    // completa la fila y continúa en la fila de arriba, de abajo hacia arriba.
    //
    // layout.filasSorted está ordenado por fila asc (fila 1 = más baja).
    const filas = layout.filasSorted;
    const maxCols = layout.maxCols;

    setInnerWidthPx(maxCols);

    // Prefijos: para cada fila i (en orden asc, de abajo→arriba), prefix[i] = cantidad de bancas en filas inferiores.
    const prefix = [];
    let acc = 0;
    for (let i = 0; i < filas.length; i++){
      prefix[i] = acc;
      acc += filas[i].columnas;
    }

    // Render visual: apilamos en DOM de arriba→abajo (recorremos de la fila más alta a la más baja),
    // pero la numeración se calcula con prefix para respetar abajo→arriba.
    for (let i = filas.length - 1; i >= 0; i--){
      const f = filas[i];
      const row = document.createElement("div");
      row.className = "recintoRow";
      row.style.gridTemplateColumns = `repeat(${f.columnas}, 1fr)`;

      const startBanca = 1 + prefix[i]; // primera banca de esta fila (según regla)

      for (let c = 0; c < f.columnas; c++){
        const bancaNro = startBanca + c;
        const concejal = concejalesByBanca.get(bancaNro) || null;

        const cell = document.createElement("div");
        cell.className = "recintoBanca";

        const inner = document.createElement("div");
        inner.className = "recintoBanca__inner";

        const img = document.createElement("img");
        img.className = "recintoBanca__img";
        img.alt = `Banca ${bancaNro}`;
        img.src = `/bancas/${bancaNro}.png`;

        const vote = document.createElement("div");
        vote.className = "recintoBanca__estado";
        vote.textContent = ""; // reservado para voto

        inner.appendChild(img);
        inner.appendChild(vote);
        cell.appendChild(inner);
        row.appendChild(cell);

        bancaEls.set(Number(bancaNro), { voteEl: vote, imgEl: img, innerEl: inner });
      }

      recintoCanvas.appendChild(row);
    }

  }

  function renderRight(sesion){
    if (!ulUsoPalabra) return;

    ulUsoPalabra.innerHTML = "";
    const cola = Array.isArray(sesion?.pedidos_uso_de_palabra) ? sesion.pedidos_uso_de_palabra : [];

    for (const c of cola){
      const li = document.createElement("li");
      const ape = String(c?.apellido ?? "").trim();
      const nom = String(c?.nombre ?? "").trim();
      const inicial = nom ? nom.charAt(0) + "." : "";
      li.textContent = `${ape} ${inicial}`.trim();
      ulUsoPalabra.appendChild(li);
    }
  }

  function clearAllVoteTexts(){
    for (const [_b, els] of bancaEls){
      if (!els?.voteEl) continue;
      els.voteEl.textContent = "";
      els.voteEl.classList.remove("is-voto", "voto-pos", "voto-neg", "voto-abs");

      if (els.innerEl){
      els.innerEl.classList.remove("voto-pos-bg","voto-neg-bg","voto-abs-bg");
      }
    }
  }

  function currentEnCursoVotaciones(sesion){
    const vs = Array.isArray(sesion?.votaciones) ? sesion.votaciones : [];
    return vs.filter(v => String(v?.estado ?? "") === "EN_CURSO");
  }

  function votacionRef(v){
    if (!v) return null;
    const id = (v.id !== undefined && v.id !== null) ? String(v.id) : String(v.numero ?? "");
    const h  = String(v.hora_inicio ?? "");
    return `${id}|${h}`;
  }

  function voteClassFor(valRaw){
    const v = String(valRaw ?? "").trim().toLowerCase();
    // Normalización simple (sin depender de acentos)
    if (v.startsWith("pos") || v.includes("positivo")) return "voto-pos";
    if (v.startsWith("neg") || v.includes("negativo")) return "voto-neg";
    if (v.startsWith("abs") || v.includes("abst")) return "voto-abs";
    return null;
  }

  function applyVotesFromVotacion(votacion){
    if (!votacion){
      clearAllVoteTexts();
      return;
    }

    // blank first
    clearAllVoteTexts();

    const votos = Array.isArray(votacion?.votos) ? votacion.votos : [];
    for (const v of votos){
      const banca = Number(v?.concejal?.banca);
      if (!Number.isFinite(banca)) continue;

      const val = String(v?.valor_voto ?? "").trim();
      const els = bancaEls.get(banca);
      if (els?.voteEl){
        els.voteEl.textContent = val;
        els.voteEl.classList.add("is-voto");

        const cls = voteClassFor(val);
        if (cls) {
          els.voteEl.classList.add(cls);

          // NUEVO: fondo claro en el inner
          if (els.innerEl){
            els.innerEl.classList.remove("voto-pos-bg","voto-neg-bg","voto-abs-bg");

            if (cls === "voto-pos") els.innerEl.classList.add("voto-pos-bg");
            if (cls === "voto-neg") els.innerEl.classList.add("voto-neg-bg");
            if (cls === "voto-abs") els.innerEl.classList.add("voto-abs-bg");
          }
        }
      }
    }
  }
  
  function applyPresenceAndSpeech(sesion){
    // Opacar imagen si concejal no está presente (60%)
    const concejales = Array.isArray(sesion?.concejales) ? sesion.concejales : [];
    const byBanca = new Map();
    for (const c of concejales){
      const b = Number(c?.banca);
      if (Number.isFinite(b)) byBanca.set(b, c);
    }

    const speakingBanca = Number(sesion?.en_uso_de_palabra?.banca);
    const hasSpeaking = Number.isFinite(speakingBanca);

    for (const [banca, els] of bancaEls){
      const c = byBanca.get(banca) || null;

      if (els?.imgEl){
        const ausente = (c && c.presente === false);
        els.imgEl.classList.toggle("is-ausente", !!ausente);
      }

      if (els?.innerEl){
        const ausente = (c && c.presente === false);
        els.innerEl.classList.toggle("is-ausente", !!ausente);

        const hablando = hasSpeaking && banca === speakingBanca;
        els.innerEl.classList.toggle("is-hablando", !!hablando);

        const test = (c && c.mostrar_test === true);
        els.innerEl.classList.toggle("is-test", !!test);
      }
    }
  }

function handleVotes(sesion){
  // Reglas:
  // - En blanco si no votó
  // - Mostrar voto si votó
  // - Volver a blanquear al abrir una nueva votación o pasados 4s desde el cierre
  // - Si hay MÁS de una votación EN_CURSO => error en recinto (no elegir ninguna)
  //
  // Importante:
  // - Una vez tomada la referencia de la votación (id/numero), durante la “ventana” de 4s
  //   seguimos actualizando los votos desde ESA misma votación aunque ya no esté EN_CURSO,
  //   para no perder el último voto que llega pegado al cierre.

  const votaciones = Array.isArray(sesion?.votaciones) ? sesion.votaciones : [];
  const enCurso = votaciones.filter(v => String(v?.estado ?? "") === "EN_CURSO");

  if (enCurso.length > 1){
    showLeftError("Error: hay más de una votación EN_CURSO. No se puede renderizar votos en el recinto.");
    return;
  }

  const now = Date.now();

  // Helper: encontrar la votación por la referencia activa (id|hora_inicio), o por id/numero
  function findVotByActiveRef(){
    if (!activeVotRef) return null;
    const [idOrNumero, hInicio] = String(activeVotRef).split("|");
    // 1) match por id exacto si existe
    const byId = votaciones.find(v => String(v?.id ?? "") === idOrNumero && String(v?.hora_inicio ?? "") === String(hInicio ?? ""));
    if (byId) return byId;
    // 2) fallback por numero + hora_inicio
    return votaciones.find(v => String(v?.numero ?? "") === idOrNumero && String(v?.hora_inicio ?? "") === String(hInicio ?? ""));
  }

  if (enCurso.length === 1){
    const v = enCurso[0];
    const ref = votacionRef(v);

    // Si cambió la votación activa, blanqueamos inmediatamente y cancelamos timers
    if (activeVotRef !== ref){
      activeVotRef = ref;
      if (clearVotesTimer) clearTimeout(clearVotesTimer);
      clearVotesTimer = null;
      clearAllVoteTexts();
    }

    // Aplicamos votos actuales (en curso)
    applyVotesFromVotacion(v);
    return;
  }

  // No hay votación EN_CURSO
  if (!activeVotRef){
    // No hay referencia activa: aseguramos blanco
    clearAllVoteTexts();
    return;
  }

  // Tenemos una referencia activa previa: seguimos actualizando desde esa votación (aunque ya esté cerrada)
  const vRef = findVotByActiveRef();
  if (vRef){
    applyVotesFromVotacion(vRef);
  }

  // Si no existe timer, lo iniciamos al detectar que ya no está EN_CURSO
  if (!clearVotesTimer){
    // Ideal: usar hora_fin si viene; si no, 4s desde ahora
    let delayMs = VOTACION_RESULT_MS;
    const hf = vRef?.hora_fin ? Date.parse(String(vRef.hora_fin)) : NaN;
    if (Number.isFinite(hf)){
      delayMs = Math.max(0, (hf + VOTACION_RESULT_MS) - now);
    }

    clearVotesTimer = setTimeout(() => {
      clearAllVoteTexts();
      activeVotRef = null;
      clearVotesTimer = null;
    }, delayMs);
  }
}


  function init(){

    // Resize: recalcula ancho uniforme del inner (si hay layout cacheado)
    window.addEventListener("resize", () => {
      if (cachedLayout?.maxCols) setInnerWidthPx(cachedLayout.maxCols);
    });

    resetCache();
  }

  function onState(raw){
    const state = normalizeState(raw);
    const ses = getSesion(state);

    // Si no hay sesión abierta: vacío total (sin placeholder)
    if (!ses || ses.abierta === false){
      resetCache();
      return;
    }

    // Si cambió de sesión: reset completo
    const sk = sesionKey(ses);
    if (cachedSesionKey !== sk){
      resetCache();
      cachedSesionKey = sk;
    }

    // Render derecho siempre (cola)
    renderRight(ses);

    // Render izquierdo: cache por disposicion_bancas
    const dispoStr = String(ses.disposicion_bancas ?? "");
    if (!cachedLayout || cachedDispoStr !== dispoStr){
      // Rebuild
      clearLeft();
      buildLeft(ses);

      // Si buildLeft falló y dejó error en canvas, no seguimos
      // (pero el panel derecho ya está OK)
      if (recintoCanvas && recintoCanvas.querySelector(".recintoCanvasError")){
        return;
      }
    } else {
      // Asegura que el ancho uniforme se mantenga si el canvas cambió de tamaño
      setInnerWidthPx(cachedLayout.maxCols);
    }

    // Si el canvas quedó en estado de error (por ejemplo, múltiples EN_CURSO),
    // y tenemos un layout válido cacheado, reconstruimos la grilla.
    if (recintoCanvas && recintoCanvas.querySelector(".recintoCanvasError") && cachedLayout && cachedDispoStr === String(ses.disposicion_bancas ?? "")){
      clearLeft();
      buildLeft(ses);
      if (recintoCanvas.querySelector(".recintoCanvasError")){
        return;
      }
    }

    // Presencia (opacidad) + en uso de palabra (borde)
    applyPresenceAndSpeech(ses);

    // Votos
    handleVotes(ses);
  }

  function onError(_e){
    // si se cae el polling, NO tocamos Q3: se mantiene la última vista
  }

  return { init, onState, onError };
})();

///////////////////////////////
// 12) Q4 (Eventos)
///////////////////////////////
const Q4 = (() => {
  const selEventosNivel = document.getElementById("selEventosNivel");
  const preEventos = document.getElementById("preEventos");

  let lastSeqSeen = -1;
  const history = []; // {seq, line, level}
  let selectedLevel = 3;

  function parseLevelFromLine(line){
    const s = String(line ?? "");
    if (s.includes("L3")) return 3;
    if (s.includes("L2")) return 2;
    if (s.includes("L1")) return 1;
    return 1;
  }

  function passesFilter(evt){
    if (selectedLevel === 1) return true;
    if (selectedLevel === 2) return evt.level >= 2;
    if (selectedLevel === 3) return evt.level >= 3;
    return true;
  }

  function autoScrollToBottom(){
    if (!preEventos) return;
    preEventos.scrollTop = preEventos.scrollHeight;
  }

  function renderAll(){
    if (!preEventos) return;

    const lines = [];
    for (const evt of history){
      if (!passesFilter(evt)) continue;
      lines.push(evt.line);
    }

    preEventos.textContent = lines.join("\n");
    autoScrollToBottom();
  }

  function ingestEventos(raw){
    const evts = getEventosFromState(raw);
    if (!Array.isArray(evts) || evts.length === 0) return;

    const sorted = [...evts].sort((a,b) => {
      const sa = Number(a?.seq ?? -1);
      const sb = Number(b?.seq ?? -1);
      return sa - sb;
    });

    let addedAny = false;

    for (const e of sorted){
      const seq = Number(e?.seq);
      if (!Number.isFinite(seq)) continue;
      if (seq <= lastSeqSeen) continue;

      const line = String(e?.line ?? "");
      const level = parseLevelFromLine(line);

      history.push({ seq, line, level });
      lastSeqSeen = seq;
      addedAny = true;
    }

    if (addedAny) renderAll();
  }

  function init(){
    if (!selEventosNivel || !preEventos) return;

    selectedLevel = 3;
    selEventosNivel.value = "L3";
    preEventos.textContent = "";

    selEventosNivel.addEventListener("change", () => {
      const v = String(selEventosNivel.value || "L3");
      if (v === "L1") selectedLevel = 1;
      else if (v === "L2") selectedLevel = 2;
      else if (v === "L3") selectedLevel = 3;
      else selectedLevel = 3;

      renderAll();
    });
  }

  function onState(raw){ ingestEventos(raw); }
  function onError(_e){}

  return { init, onState, onError };
})();

///////////////////////////////
// 13) Registro cuadrantes
///////////////////////////////
const Quadrants = [Q1, Q3, Q4];

///////////////////////////////
// 14) Polling core
///////////////////////////////
let pollingRunning = false;

async function pollOnce(){
  const url = API_BASE_URL + STATE_ENDPOINT;

  try{
    const data = await getJson(url);
    setConn("ok", "Conectado");
    updateHeaderSesionInfo(data);
    for (const q of Quadrants) q.onState(data);
  } catch (e){
    setConn("err", "Sin conexión");
    for (const q of Quadrants) q.onError(e);
  }
}

function startPollLoop(){
  if (pollingRunning) return;
  pollingRunning = true;

  const tick = async () => {
    await pollOnce();
    setTimeout(tick, POLL_MS);
  };

  tick();
}

///////////////////////////////
// 15) Inicio
///////////////////////////////
setConn("warn", "Conectando…");
toast("ok", "Listo.");

for (const q of Quadrants) q.init();
startPollLoop();
