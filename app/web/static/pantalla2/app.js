/*
  Pantalla 2 - recinto
  ====================
  Este archivo consume dos fuentes:
  - /estados/info_pantallas: estado vivo de la pantalla.
  - /estados/configuracion: datos fijos de layout, como disposicion_bancas.

  No consulta /estados/estado_global.
*/

///////////////////////////////
// 1) Configuracion general
///////////////////////////////
const API_BASE_URL = "";
const STATE_ENDPOINT = "/estados/info_pantallas";
const CONFIG_ENDPOINT = "/estados/configuracion";

const POLL_MS = 300;
const TIMEOUT_MS = 1500;
const VOTACION_RESULT_MS = 6000;
const VOTACION_COUNTDOWN_SEC = 4;

///////////////////////////////
// 2) Referencias DOM
///////////////////////////////
const DOM = {
  connText: document.getElementById("connText"),
  clock: document.getElementById("clock"),
  toast: document.getElementById("toast"),
  hdrSesionInfo: document.getElementById("hdrSesionInfo"),

  q1VotacionResumen: document.getElementById("q1VotacionResumen"),
  q1QuorumValue: document.getElementById("q1QuorumValue"),
  inVotTema: document.getElementById("inVotTema"),
  votacionEstado: document.getElementById("votacionEstado"),

  recintoCanvas: document.getElementById("recintoCanvas"),
  recintoError: document.getElementById("recintoError"),
  ulUsoPalabra: document.getElementById("ulUsoPalabra"),
  q3Countdown: document.getElementById("q3Countdown"),

  selEventosNivel: document.getElementById("selEventosNivel"),
  preEventos: document.getElementById("preEventos"),
};

///////////////////////////////
// 3) Estado interno de la pantalla
///////////////////////////////
const appState = {
  configLoaded: false,
  configError: null,
  disposicionBancas: null,
  pollingRunning: false,
};

let toastTimer = null;

///////////////////////////////
// 4) Utilidades generales
///////////////////////////////

// Escribe texto solo si el elemento existe.
function setText(el, text){
  if (el) el.textContent = text;
}

// Convierte cualquier valor en arreglo, o devuelve un arreglo vacio.
function asArray(value){
  return Array.isArray(value) ? value : [];
}

// Devuelve un numero finito o null si el dato no sirve.
function toFiniteNumber(value){
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

// Normaliza texto para comparar estados sin depender de mayusculas ni acentos.
function normalizeKey(value){
  return String(value ?? "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toUpperCase();
}

// Arma una referencia estable para distinguir votaciones.
function getVotacionRef(info){
  const numero = info?.nro_votacion_en_curso;
  const hora = info?.hora_apertura_votacion;
  if (numero === null || numero === undefined || !hora) return null;
  return `${numero}|${hora}`;
}

// Detecta si el texto de estado indica que hay votacion abierta.
function isVotacionEnCurso(info){
  const estado = normalizeKey(info?.estado_votacion);
  return estado.includes("EN CURSO");
}

// Detecta el resultado principal desde el texto generado por el backend.
function inferResultadoVotacion(info){
  const estado = normalizeKey(info?.estado_votacion);
  if (estado.includes("APROBADA")) return "APROBADA";
  if (estado.includes("RECHAZADA")) return "RECHAZADA";
  if (estado.includes("EMPATADA")) return "EMPATADA";
  if (estado.includes("INCONCLUSA")) return "INCONCLUSA";
  return null;
}

// Indica si hay datos de votacion suficientes para mostrar Q1/Q3.
function hasVotacion(info){
  return getVotacionRef(info) !== null || Boolean(info?.estado_votacion || info?.titulo_votacion);
}

// Fetch JSON con timeout para evitar requests colgadas.
async function fetchJson(url, timeoutMs = TIMEOUT_MS){
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try{
    const res = await fetch(url, {
      method: "GET",
      headers: { "Accept": "application/json" },
      signal: controller.signal,
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } finally {
    clearTimeout(timer);
  }
}

// Actualiza el indicador de conexion de la cabecera.
function setConn(kind, text){
  const el = DOM.connText;
  if (!el) return;

  el.classList.remove("conn-ok", "conn-err", "conn-warn");
  if (kind === "ok") el.classList.add("conn-ok");
  else if (kind === "err") el.classList.add("conn-err");
  else el.classList.add("conn-warn");

  el.textContent = text;
}

// Muestra un aviso flotante breve.
function toast(kind, msg, ms = 2500){
  const el = DOM.toast;
  if (!el) return;

  el.classList.remove("toast--ok", "toast--err", "toast--warn", "toast--show");
  if (kind === "ok") el.classList.add("toast--ok");
  else if (kind === "err") el.classList.add("toast--err");
  else el.classList.add("toast--warn");

  el.textContent = msg;
  el.classList.add("toast--show");

  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    el.classList.remove("toast--show");
  }, ms);
}

// Actualiza el reloj local visible en la cabecera.
function updateClock(){
  if (!DOM.clock) return;
  DOM.clock.textContent = new Date().toLocaleString("es-AR");
}

///////////////////////////////
// 5) Normalizacion de datos
///////////////////////////////

// Convierte la respuesta de info_pantallas en un objeto predecible para la UI.
function normalizeInfoPantallas(raw){
  const info = raw && typeof raw === "object" ? raw : {};
  return {
    hora_actual: info.hora_actual ?? null,
    hora_apertura_recinto: info.hora_apertura_recinto ?? null,
    sesion_abierta: info.sesion_abierta ?? null,
    transmision_en_vivo: info.transmision_en_vivo === true,
    numero_sesion: info.numero_sesion ?? null,
    hora_inicio_sesion: info.hora_inicio_sesion ?? null,
    hora_fin_sesion: info.hora_fin_sesion ?? null,
    cantidad_presentes: toFiniteNumber(info.cantidad_presentes),
    diferencia_contra_quorum: toFiniteNumber(info.diferencia_contra_quorum),
    pedidos_uso_de_palabra: asArray(info.pedidos_uso_de_palabra),
    bancas: asArray(info.bancas),
    nro_votacion_en_curso: info.nro_votacion_en_curso ?? null,
    hora_apertura_votacion: info.hora_apertura_votacion ?? null,
    tema_votacion_en_curso: info.tema_votacion_en_curso ?? null,
    tipo_votacion_en_curso: info.tipo_votacion_en_curso ?? null,
    votos_emitidos_votacion_en_curso: toFiniteNumber(info.votos_emitidos_votacion_en_curso),
    estado_votacion: info.estado_votacion ?? null,
    titulo_votacion: info.titulo_votacion ?? null,
    eventos: asArray(info.eventos),
  };
}

// Extrae disposicion_bancas desde la ruta de configuracion.
function normalizeConfig(raw){
  const config = raw?.settings && typeof raw.settings === "object" ? raw.settings : raw;
  if (!config || typeof config !== "object") return null;
  return config.disposicion_bancas ?? null;
}

// Acepta disposicion_bancas como objeto o como string JSON.
function parseDisposicionBancas(disposicion){
  if (!disposicion) return null;
  if (typeof disposicion === "string"){
    try{
      return JSON.parse(disposicion);
    } catch(_e){
      return null;
    }
  }
  return typeof disposicion === "object" ? disposicion : null;
}

// Calcula filas, columnas y total de bancas esperadas desde configuracion.
function computeLayout(disposicion){
  const parsed = parseDisposicionBancas(disposicion);
  const filasRaw = asArray(parsed?.filas);

  const filasSorted = filasRaw
    .map(f => ({
      fila: toFiniteNumber(f?.fila),
      columnas: toFiniteNumber(f?.columnas),
    }))
    .filter(f => f.fila !== null && f.columnas !== null && f.columnas > 0)
    .sort((a, b) => a.fila - b.fila);

  if (!filasSorted.length) return null;

  const sumCols = filasSorted.reduce((acc, f) => acc + f.columnas, 0);
  const maxCols = filasSorted.reduce((acc, f) => Math.max(acc, f.columnas), 0);

  return { filasSorted, sumCols, maxCols };
}

///////////////////////////////
// 6) Configuracion inicial
///////////////////////////////

// Carga la configuracion fija una sola vez al iniciar la pantalla.
async function loadConfiguration(){
  try{
    const raw = await fetchJson(API_BASE_URL + CONFIG_ENDPOINT);
    const disposicion = normalizeConfig(raw);
    const layout = computeLayout(disposicion);

    if (!layout){
      throw new Error("disposicion_bancas invalida");
    }

    appState.configLoaded = true;
    appState.configError = null;
    appState.disposicionBancas = disposicion;
    setConn("warn", "Conectando...");
  } catch(e){
    appState.configLoaded = false;
    appState.configError = e;
    appState.disposicionBancas = null;
    setConn("err", "Error de configuracion");
  }
}

///////////////////////////////
// 7) Header
///////////////////////////////
const Header = (() => {
  // Pinta la informacion resumida de la sesion en la cabecera.
  function render(info){
    const total = info.bancas.length;
    const presentes = info.cantidad_presentes;

    if (!total && info.sesion_abierta !== true){
      setText(DOM.hdrSesionInfo, "");
      return;
    }

    if (info.sesion_abierta === true){
      const nro = info.numero_sesion ?? "-";
      const presentesTxt = presentes === null ? "-" : String(presentes);
      setText(DOM.hdrSesionInfo, ` · Sesion N° ${nro} - Concejales ${presentesTxt} de ${total} totales`);
      return;
    }

    setText(DOM.hdrSesionInfo, ` · Recinto preparado - Concejales ${total} totales`);
  }

  // Limpia la cabecera cuando no hay estado disponible.
  function clear(){
    setText(DOM.hdrSesionInfo, "");
  }

  return { render, clear };
})();

///////////////////////////////
// 8) Q1 - Resumen de votacion y quorum
///////////////////////////////
const Q1 = (() => {
  let lastVoteRef = null;
  let resultClearTimer = null;
  let blankedVoteRef = null;

  // Quita colores de resultado en el texto de estado.
  function clearEstadoColor(){
    if (!DOM.votacionEstado) return;
    DOM.votacionEstado.classList.remove("q1-res-pos", "q1-res-neg", "q1-res-abs");
  }

  // Aplica color segun el resultado inferido del backend.
  function applyEstadoColor(resultado){
    clearEstadoColor();
    if (!DOM.votacionEstado) return;

    if (resultado === "APROBADA") DOM.votacionEstado.classList.add("q1-res-pos");
    else if (resultado === "RECHAZADA") DOM.votacionEstado.classList.add("q1-res-neg");
    else if (resultado === "EMPATADA") DOM.votacionEstado.classList.add("q1-res-abs");
  }

  // Limpia los textos de votacion una vez vencida la ventana de resultado.
  function clearVotacionTexts(){
    setText(DOM.q1VotacionResumen, "-");
    setText(DOM.inVotTema, "-");
    setText(DOM.votacionEstado, "-");
    clearEstadoColor();
  }

  // Renderiza el delta contra quorum que ya calcula el backend.
  function renderQuorum(info){
    const el = DOM.q1QuorumValue;
    if (!el) return;

    el.classList.remove("num-good", "num-bad", "num-neutral");

    const delta = info.diferencia_contra_quorum;
    if (delta === null || info.sesion_abierta !== true){
      el.textContent = "–";
      el.classList.add("num-neutral");
      return;
    }

    el.textContent = delta > 0 ? `+${delta}` : String(delta);
    el.classList.add(delta >= 0 ? "num-good" : "num-bad");
  }

  // Controla cuando una votacion cerrada debe permanecer visible y cuando debe limpiarse.
  function updateResultWindow(info){
    const voteRef = getVotacionRef(info);
    const inProgress = isVotacionEnCurso(info);
    const resultado = inferResultadoVotacion(info);

    if (!voteRef){
      lastVoteRef = null;
      blankedVoteRef = null;
      if (resultClearTimer) clearTimeout(resultClearTimer);
      resultClearTimer = null;
      clearEstadoColor();
      return;
    }

    if (lastVoteRef !== voteRef){
      lastVoteRef = voteRef;
      blankedVoteRef = null;
      if (resultClearTimer) clearTimeout(resultClearTimer);
      resultClearTimer = null;
      clearEstadoColor();
    }

    if (inProgress){
      blankedVoteRef = null;
      if (resultClearTimer) clearTimeout(resultClearTimer);
      resultClearTimer = null;
      clearEstadoColor();
      return;
    }

    if (!resultado || blankedVoteRef === voteRef || resultClearTimer) return;

    applyEstadoColor(resultado);
    resultClearTimer = setTimeout(() => {
      blankedVoteRef = voteRef;
      resultClearTimer = null;
      clearVotacionTexts();
    }, VOTACION_RESULT_MS);
  }

  // Pinta los textos principales de votacion usando solo info_pantallas.
  function renderVotacion(info){
    const voteRef = getVotacionRef(info);
    const isBlanked = voteRef && blankedVoteRef === voteRef && !isVotacionEnCurso(info);

    if (!hasVotacion(info) || isBlanked){
      clearVotacionTexts();
      if (!hasVotacion(info)) setText(DOM.q1VotacionResumen, "No hay votacion en curso.");
      return;
    }

    setText(DOM.q1VotacionResumen, info.titulo_votacion || "No hay votacion en curso.");
    setText(DOM.inVotTema, info.tema_votacion_en_curso || "-");
    setText(DOM.votacionEstado, info.estado_votacion || "-");

    if (!isVotacionEnCurso(info)){
      applyEstadoColor(inferResultadoVotacion(info));
    }
  }

  // Deja el cuadrante en estado inicial.
  function init(){
    clearVotacionTexts();
    setText(DOM.q1VotacionResumen, "No hay votacion en curso.");
    renderQuorum(normalizeInfoPantallas(null));
  }

  // Reacciona ante cada estado nuevo.
  function onState(info){
    renderQuorum(info);
    updateResultWindow(info);
    renderVotacion(info);
  }

  // Ante error de polling no pisamos el ultimo estado visible.
  function onError(_e){}

  return { init, onState, onError };
})();

///////////////////////////////
// 9) Q3 - Recinto y uso de la palabra
///////////////////////////////
const Q3 = (() => {
  let cachedLayoutKey = null;
  let cachedBancasKey = null;
  let cachedLayout = null;
  let bancaEls = new Map();

  let activeVoteRef = null;
  let blankedVoteRef = null;
  let resultClearTimer = null;

  let countdownRef = null;
  let countdownTimer = null;

  // Borra el recinto renderizado.
  function clearCanvas(){
    if (DOM.recintoCanvas) DOM.recintoCanvas.innerHTML = "";
    bancaEls = new Map();
  }

  // Limpia la lista de pedidos de palabra.
  function clearSpeechQueue(){
    if (DOM.ulUsoPalabra) DOM.ulUsoPalabra.innerHTML = "";
  }

  // Oculta mensajes de error secundarios.
  function hideError(){
    if (DOM.recintoError) DOM.recintoError.style.display = "none";
  }

  // Muestra un error claro dentro del area de bancas.
  function showCanvasError(message){
    if (!DOM.recintoCanvas) return;

    clearCanvas();
    const div = document.createElement("div");
    div.className = "recintoCanvasError";
    div.textContent = message;
    DOM.recintoCanvas.appendChild(div);
    hideError();
  }

  // Calcula una clave para saber si hay que reconstruir el layout.
  function layoutKey(layout){
    if (!layout) return "";
    return layout.filasSorted.map(f => `${f.fila}:${f.columnas}`).join("|");
  }

  // Calcula una clave de bancas para reconstruir si cambia la nomina.
  function bancasKey(bancas){
    return bancas
      .map(b => `${b?.numero_banca ?? ""}:${b?.nombre_concejal ?? ""}`)
      .join("|");
  }

  // Ajusta el ancho interno de cada banca segun la fila mas ancha.
  function setInnerWidthPx(maxCols){
    if (!DOM.recintoCanvas) return;
    const gap = 8;
    const w = DOM.recintoCanvas.clientWidth || 0;
    if (!w || !maxCols) return;

    const totalGaps = (maxCols - 1) * gap;
    const cellW = (w - totalGaps) / maxCols;
    const innerW = Math.max(20, Math.floor(cellW * 0.92));
    DOM.recintoCanvas.style.setProperty("--bancaInnerW", `${innerW}px`);
  }

  // Crea los elementos DOM de una banca.
  function createBancaCell(numeroBanca, banca){
    const cell = document.createElement("div");
    cell.className = "recintoBanca";

    const inner = document.createElement("div");
    inner.className = "recintoBanca__inner";
    if (banca?.nombre_concejal) inner.title = banca.nombre_concejal;

    const img = document.createElement("img");
    img.className = "recintoBanca__img";
    img.alt = `Banca ${numeroBanca}`;
    img.src = `/bancas/${numeroBanca}.png`;

    const vote = document.createElement("div");
    vote.className = "recintoBanca__estado";
    vote.textContent = "";

    inner.appendChild(img);
    inner.appendChild(vote);
    cell.appendChild(inner);

    bancaEls.set(Number(numeroBanca), { voteEl: vote, imgEl: img, innerEl: inner });
    return cell;
  }

  // Construye el recinto desde disposicion_bancas y la lista de bancas.
  function buildCanvas(info){
    const layout = computeLayout(appState.disposicionBancas);
    if (!layout){
      showCanvasError("Error: configuracion de disposicion_bancas invalida.");
      return;
    }

    const bancas = [...info.bancas].sort((a, b) => Number(a?.numero_banca) - Number(b?.numero_banca));
    if (layout.sumCols !== bancas.length){
      showCanvasError(`Error: sum(columnas)=${layout.sumCols} no coincide con bancas=${bancas.length}.`);
      return;
    }

    clearCanvas();
    hideError();

    const bancasByNumero = new Map();
    for (const banca of bancas){
      const numero = toFiniteNumber(banca?.numero_banca);
      if (numero !== null) bancasByNumero.set(numero, banca);
    }

    const filas = layout.filasSorted;
    const prefix = [];
    let acc = 0;
    for (let i = 0; i < filas.length; i++){
      prefix[i] = acc;
      acc += filas[i].columnas;
    }

    setInnerWidthPx(layout.maxCols);

    for (let i = filas.length - 1; i >= 0; i--){
      const fila = filas[i];
      const row = document.createElement("div");
      row.className = "recintoRow";
      row.style.gridTemplateColumns = `repeat(${fila.columnas}, 1fr)`;

      const startBanca = 1 + prefix[i];
      for (let col = 0; col < fila.columnas; col++){
        const numeroBanca = startBanca + col;
        row.appendChild(createBancaCell(numeroBanca, bancasByNumero.get(numeroBanca)));
      }

      DOM.recintoCanvas.appendChild(row);
    }

    cachedLayout = layout;
    cachedLayoutKey = layoutKey(layout);
    cachedBancasKey = bancasKey(bancas);
  }

  // Devuelve la clase CSS de color para un voto.
  function voteClassFor(value){
    const key = normalizeKey(value);
    if (key.includes("POSITIVO") || key === "POS") return "voto-pos";
    if (key.includes("NEGATIVO") || key === "NEG") return "voto-neg";
    if (key.includes("ABSTENCION") || key.includes("ABST")) return "voto-abs";
    return null;
  }

  // Devuelve el texto visible de voto.
  function voteTextFor(value){
    const key = normalizeKey(value);
    if (key.includes("POSITIVO") || key === "POS") return "POSITIVO";
    if (key.includes("NEGATIVO") || key === "NEG") return "NEGATIVO";
    if (key.includes("ABSTENCION") || key.includes("ABST")) return "ABSTENCION";
    return String(value ?? "").trim();
  }

  // Limpia textos y colores de voto en todas las bancas.
  function clearAllVotes(){
    for (const els of bancaEls.values()){
      els.voteEl?.classList.remove("is-voto", "voto-pos", "voto-neg", "voto-abs");
      if (els.voteEl) els.voteEl.textContent = "";
      els.innerEl?.classList.remove("voto-pos-bg", "voto-neg-bg", "voto-abs-bg");
    }
  }

  // Pinta los votos que llegan ya consolidados en info_pantallas.bancas.
  function applyVotes(info){
    clearAllVotes();

    for (const banca of info.bancas){
      const numero = toFiniteNumber(banca?.numero_banca);
      if (numero === null) continue;

      const voto = banca?.voto;
      if (!voto) continue;

      const els = bancaEls.get(numero);
      if (!els?.voteEl) continue;

      const cls = voteClassFor(voto);
      els.voteEl.textContent = voteTextFor(voto);
      els.voteEl.classList.add("is-voto");

      if (cls){
        els.voteEl.classList.add(cls);
        if (cls === "voto-pos") els.innerEl?.classList.add("voto-pos-bg");
        if (cls === "voto-neg") els.innerEl?.classList.add("voto-neg-bg");
        if (cls === "voto-abs") els.innerEl?.classList.add("voto-abs-bg");
      }
    }
  }

  // Aplica presencia, uso de palabra y modo test a cada banca.
  function applyBancaStatus(info){
    const byNumero = new Map();
    for (const banca of info.bancas){
      const numero = toFiniteNumber(banca?.numero_banca);
      if (numero !== null) byNumero.set(numero, banca);
    }

    for (const [numero, els] of bancaEls){
      const banca = byNumero.get(numero);
      const ausente = banca && banca.presente === false;
      const hablando = banca && banca.en_uso_palabra === true;
      const test = banca && banca.test === true;

      els.imgEl?.classList.toggle("is-ausente", !!ausente);
      els.innerEl?.classList.toggle("is-ausente", !!ausente);
      els.innerEl?.classList.toggle("is-hablando", !!hablando);
      els.innerEl?.classList.toggle("is-test", !!test);
    }
  }

  // Renderiza la cola de pedidos de uso de palabra.
  function renderSpeechQueue(info){
    if (!DOM.ulUsoPalabra) return;
    DOM.ulUsoPalabra.innerHTML = "";

    for (const pedido of info.pedidos_uso_de_palabra){
      const li = document.createElement("li");
      li.textContent = String(pedido ?? "").trim();
      DOM.ulUsoPalabra.appendChild(li);
    }
  }

  // Oculta la cuenta regresiva.
  function hideCountdown(){
    if (!DOM.q3Countdown) return;
    DOM.q3Countdown.classList.remove("is-show");
    DOM.q3Countdown.innerHTML = "";
  }

  // Pinta un numero de cuenta regresiva.
  function renderCountdownNum(n){
    if (!DOM.q3Countdown) return;
    DOM.q3Countdown.innerHTML = `
      <div class="q3Countdown__pill">
        <div class="q3Countdown__num">${n}</div>
        <div class="q3Countdown__sub">Tiempo</div>
      </div>
    `;
  }

  // Inicia el contador cuando aparece una votacion nueva.
  function startCountdownFor(ref){
    if (!DOM.q3Countdown || countdownRef === ref) return;

    countdownRef = ref;
    if (countdownTimer) clearInterval(countdownTimer);

    let remaining = Number(VOTACION_COUNTDOWN_SEC) || 0;
    if (remaining <= 0){
      hideCountdown();
      return;
    }

    DOM.q3Countdown.classList.add("is-show");
    renderCountdownNum(remaining);

    countdownTimer = setInterval(() => {
      remaining -= 1;
      if (remaining <= 0){
        clearInterval(countdownTimer);
        countdownTimer = null;
        hideCountdown();
        return;
      }

      renderCountdownNum(remaining);
    }, 1000);
  }

  // Decide si los votos se ocultan, se muestran o se limpian.
  function handleVotes(info){
    const voteRef = getVotacionRef(info);
    const inProgress = isVotacionEnCurso(info);

    if (!voteRef){
      activeVoteRef = null;
      blankedVoteRef = null;
      if (resultClearTimer) clearTimeout(resultClearTimer);
      resultClearTimer = null;
      clearAllVotes();
      return;
    }

    if (inProgress){
      if (activeVoteRef !== voteRef){
        activeVoteRef = voteRef;
        blankedVoteRef = null;
        if (resultClearTimer) clearTimeout(resultClearTimer);
        resultClearTimer = null;
        clearAllVotes();
        startCountdownFor(voteRef);
      }

      clearAllVotes();
      return;
    }

    if (blankedVoteRef === voteRef){
      clearAllVotes();
      return;
    }

    applyVotes(info);

    if (!resultClearTimer){
      resultClearTimer = setTimeout(() => {
        blankedVoteRef = voteRef;
        activeVoteRef = null;
        resultClearTimer = null;
        clearAllVotes();
      }, VOTACION_RESULT_MS);
    }
  }

  // Limpia todo el cuadrante Q3.
  function reset(){
    clearCanvas();
    clearSpeechQueue();
    hideError();
    hideCountdown();

    cachedLayoutKey = null;
    cachedBancasKey = null;
    cachedLayout = null;
    activeVoteRef = null;
    blankedVoteRef = null;
    countdownRef = null;

    if (resultClearTimer) clearTimeout(resultClearTimer);
    resultClearTimer = null;

    if (countdownTimer) clearInterval(countdownTimer);
    countdownTimer = null;
  }

  // Inicializa listeners del cuadrante.
  function init(){
    window.addEventListener("resize", () => {
      if (cachedLayout?.maxCols) setInnerWidthPx(cachedLayout.maxCols);
    });
    reset();
  }

  // Renderiza el recinto completo con el estado recibido.
  function onState(info){
    renderSpeechQueue(info);

    if (!appState.configLoaded){
      showCanvasError("Error: no se pudo cargar /estados/configuracion.");
      return;
    }

    if (!info.bancas.length){
      clearCanvas();
      clearAllVotes();
      return;
    }

    const layout = computeLayout(appState.disposicionBancas);
    const nextLayoutKey = layoutKey(layout);
    const nextBancasKey = bancasKey(info.bancas);
    const needsRebuild = !cachedLayout || cachedLayoutKey !== nextLayoutKey || cachedBancasKey !== nextBancasKey;

    if (needsRebuild || DOM.recintoCanvas?.querySelector(".recintoCanvasError")){
      buildCanvas(info);
      if (DOM.recintoCanvas?.querySelector(".recintoCanvasError")) return;
    } else {
      setInnerWidthPx(cachedLayout.maxCols);
    }

    applyBancaStatus(info);
    handleVotes(info);
  }

  // Ante error de polling se conserva la ultima vista valida.
  function onError(_e){}

  return { init, onState, onError };
})();

///////////////////////////////
// 10) Q4 - Eventos futuros
///////////////////////////////
const Q4 = (() => {
  let selectedLevel = 3;
  let lastSeqSeen = -1;
  let stringSnapshot = "";
  const history = [];

  // Extrae el nivel de una linea de log.
  function parseLevelFromLine(line){
    const text = String(line ?? "");
    if (text.includes("L3")) return 3;
    if (text.includes("L2")) return 2;
    if (text.includes("L1")) return 1;
    return 1;
  }

  // Decide si un evento pasa el filtro elegido.
  function passesFilter(evt){
    if (selectedLevel === 1) return true;
    if (selectedLevel === 2) return evt.level >= 2;
    return evt.level >= 3;
  }

  // Lleva la consola al final.
  function autoScrollToBottom(){
    if (!DOM.preEventos) return;
    DOM.preEventos.scrollTop = DOM.preEventos.scrollHeight;
  }

  // Renderiza el historial actual.
  function renderAll(){
    if (!DOM.preEventos) return;
    DOM.preEventos.textContent = history
      .filter(passesFilter)
      .map(evt => evt.line)
      .join("\n");
    autoScrollToBottom();
  }

  // Normaliza eventos futuros: strings o {seq,line,level}.
  function normalizeEvento(evt, fallbackSeq){
    if (typeof evt === "string"){
      return {
        seq: fallbackSeq,
        line: evt,
        level: parseLevelFromLine(evt),
        hasRealSeq: false,
      };
    }

    const line = String(evt?.line ?? "");
    const seq = toFiniteNumber(evt?.seq);
    const level = toFiniteNumber(evt?.level) ?? parseLevelFromLine(line);

    return {
      seq: seq ?? fallbackSeq,
      line,
      level,
      hasRealSeq: seq !== null,
    };
  }

  // Incorpora eventos si el backend empieza a enviarlos en info_pantallas.
  function ingestEventos(info){
    const eventos = asArray(info.eventos);
    if (!eventos.length) return;

    const allStrings = eventos.every(evt => typeof evt === "string");
    if (allStrings){
      const snapshot = eventos.join("\n");
      if (snapshot === stringSnapshot) return;

      stringSnapshot = snapshot;
      history.length = 0;
      eventos.forEach((evt, index) => {
        history.push(normalizeEvento(evt, index));
      });
      renderAll();
      return;
    }

    let added = false;
    eventos
      .map((evt, index) => normalizeEvento(evt, index))
      .sort((a, b) => a.seq - b.seq)
      .forEach(evt => {
        if (!evt.hasRealSeq || evt.seq <= lastSeqSeen) return;
        history.push(evt);
        lastSeqSeen = evt.seq;
        added = true;
      });

    if (added) renderAll();
  }

  // Oculta visualmente eventos durante votacion en curso.
  function applySecretMode(info){
    if (!DOM.preEventos) return;
    DOM.preEventos.classList.toggle("is-secret", isVotacionEnCurso(info));
  }

  // Inicializa selector de nivel y consola.
  function init(){
    if (!DOM.selEventosNivel || !DOM.preEventos) return;

    selectedLevel = 3;
    DOM.selEventosNivel.value = "L3";
    DOM.preEventos.textContent = "";

    DOM.selEventosNivel.addEventListener("change", () => {
      const value = String(DOM.selEventosNivel.value || "L3");
      if (value === "L1") selectedLevel = 1;
      else if (value === "L2") selectedLevel = 2;
      else selectedLevel = 3;
      renderAll();
    });
  }

  // Reacciona ante cada estado nuevo.
  function onState(info){
    applySecretMode(info);
    ingestEventos(info);
  }

  // Ante error de polling no tocamos la consola.
  function onError(_e){}

  return { init, onState, onError };
})();

///////////////////////////////
// 11) Polling
///////////////////////////////
const Modules = [Q1, Q3, Q4];

// Consulta una vez el estado vivo de info_pantallas.
async function pollOnce(){
  try{
    const raw = await fetchJson(API_BASE_URL + STATE_ENDPOINT);
    const info = normalizeInfoPantallas(raw);

    setConn("ok", "Conectado");
    Header.render(info);
    for (const module of Modules) module.onState(info);
  } catch(e){
    setConn("err", "Sin conexion");
    for (const module of Modules) module.onError(e);
  }
}

// Inicia el loop de polling sin solapar ciclos.
function startPollLoop(){
  if (appState.pollingRunning) return;
  appState.pollingRunning = true;

  const tick = async () => {
    await pollOnce();
    setTimeout(tick, POLL_MS);
  };

  tick();
}

///////////////////////////////
// 12) Inicio
///////////////////////////////

// Inicializa reloj, configuracion, modulos y polling.
async function start(){
  updateClock();
  setInterval(updateClock, 250);

  setConn("warn", "Cargando configuracion...");
  toast("ok", "Listo.");

  await loadConfiguration();

  Header.clear();
  for (const module of Modules) module.init();
  startPollLoop();
}

start();
