/*
  app.js
  ======
  OBJETIVO DE ESTA VERSION (modo TESTING):
  ---------------------------------------
  - El frontend NO valida datos.
  - El frontend NO “frena” el envío por campos vacíos o mal tipeados.
  - El frontend SIEMPRE envía lo que haya en pantalla.
  - El backend es el único responsable de validar y responder errores 422/400/etc.

  ¿Qué cambia respecto a la versión anterior?
  - Antes: si Sesión Nº estaba vacío => el front mostraba error local y NO enviaba.
  - Ahora: si Sesión Nº está vacío => el front envía igual, y el backend devolverá el error.

  Lo mismo para:
  - Votación Nº vacío
  - Tema vacío
  - Factor no numérico
  etc.

  Nota:
  - Seguimos “normalizando” la coma en el factor (0,66 -> 0.66).
    Esto NO es una validación, solo una conveniencia para que el backend pueda parsear.
    Si querés testear también el caso coma (que falle), lo saco.
*/

///////////////////////////////
// 1) CONFIG BASICA
///////////////////////////////

const API_BASE_URL = "";                 // mismo host del FastAPI
const STATE_ENDPOINT = "/estados/estado_global";
const POLL_MS = 250;
const TIMEOUT_MS = 1500;

///////////////////////////////
// 2) REFERENCIAS A ELEMENTOS DEL DOM
///////////////////////////////

// Topbar
const connText = document.getElementById("connText");
const clockEl  = document.getElementById("clock");

// Sesión (input y botones)
const inSesionNumero = document.getElementById("inSesionNumero");
const btnAbrirSesion = document.getElementById("btnAbrirSesion");
const btnCerrarSesion = document.getElementById("btnCerrarSesion");

// Sesión (solo lectura)
const txtConcejales = document.getElementById("txtConcejales");
const txtQuorumDelta = document.getElementById("txtQuorumDelta");

// Votación (modo normal)
const votacionNormal = document.getElementById("votacionNormal");
const inVotNumero = document.getElementById("inVotNumero");
const selVotTipo = document.getElementById("selVotTipo");
const inVotFactor = document.getElementById("inVotFactor");
const togRespectoPresentes = document.getElementById("togRespectoPresentes");
const togRespectoCuerpo = document.getElementById("togRespectoCuerpo");
const inVotTema = document.getElementById("inVotTema");
const btnAbrirVotacion = document.getElementById("btnAbrirVotacion");
const btnCerrarVotacion = document.getElementById("btnCerrarVotacion");
const votacionEstado = document.getElementById("votacionEstado");

// Votación (modo empate)
const votacionEmpate = document.getElementById("votacionEmpate");
const btnDesempatePositivo = document.getElementById("btnDesempatePositivo");
const btnDesempateNegativo = document.getElementById("btnDesempateNegativo");
const votacionEstadoEmpate = document.getElementById("votacionEstadoEmpate");

// Toast (texto de estado del frontend)
const toastEl = document.getElementById("toast");

///////////////////////////////
// 3) RELOJ LOCAL (NO depende del backend)
///////////////////////////////

function updateClock(){
  clockEl.textContent = new Date().toLocaleString("es-AR");
}
updateClock();
setInterval(updateClock, 250);

///////////////////////////////
// 4) UI helpers: conexión y “toast”
///////////////////////////////

function setConn(kind, text){
  connText.classList.remove("conn-ok","conn-err","conn-warn");

  if (kind === "ok") connText.classList.add("conn-ok");
  else if (kind === "err") connText.classList.add("conn-err");
  else connText.classList.add("conn-warn");

  connText.textContent = text;
}

function toast(kind, msg){
  toastEl.classList.remove("toast--ok","toast--err","toast--warn");

  if (kind === "ok") toastEl.classList.add("toast--ok");
  else if (kind === "err") toastEl.classList.add("toast--err");
  else toastEl.classList.add("toast--warn");

  toastEl.textContent = msg;
}

///////////////////////////////
// 5) FETCH con timeout
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

  if (!res.ok){
    throw new Error(`HTTP ${res.status}`);
  }

  return await res.json();
}

/*
  postJson:
  - Hace POST con JSON.
  - Si el backend responde error, tiramos un Error con:
      "HTTP <status> - <cuerpo>"
  Esto es ideal para ver validaciones del backend (422, 400, etc.).
*/
async function postJson(url, body){
  const res = await fetchWithTimeout(url, {
    method: "POST",
    headers: {
      "Content-Type":"application/json",
      "Accept":"application/json"
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  const text = await res.text();

  if (!res.ok){
    // Importante: mostramos lo que devuelve el backend
    // (por ejemplo el detalle del 422).
    throw new Error(`HTTP ${res.status} - ${text}`);
  }

  // Si devuelve JSON, lo parseamos; si no, devolvemos crudo.
  try { return JSON.parse(text); }
  catch { return { ok:true, raw:text }; }
}

///////////////////////////////
// 6) UI Model mínimo (solo para el toggle "Respecto")
///////////////////////////////

/*
  El toggle "Respecto" afecta SOLO el body que enviamos al ABRIR VOTACION:
    computa_sobre_los_presentes = true  si Respecto: Presentes
                               = false si Respecto: Cuerpo
*/
const uiModel = {
  respectoPresentes: true
};

function paintToggleRespecto(){
  const pres = uiModel.respectoPresentes === true;
  togRespectoPresentes.classList.toggle("toggle__btn--active", pres);
  togRespectoCuerpo.classList.toggle("toggle__btn--active", !pres);
}

togRespectoPresentes.addEventListener("click", () => {
  uiModel.respectoPresentes = true;
  paintToggleRespecto();
});

togRespectoCuerpo.addEventListener("click", () => {
  uiModel.respectoPresentes = false;
  paintToggleRespecto();
});

paintToggleRespecto();

///////////////////////////////
// 7) COMANDOS - SESION (sin validación frontend)
///////////////////////////////

btnAbrirSesion.addEventListener("click", async () => {
  toast("warn", "Enviando: abrir sesión…");

  try{
    /*
      IMPORTANTE (modo testing):
      - NO parseamos a int.
      - NO comprobamos vacío.
      - Mandamos lo que el usuario escribió.

      Si el backend espera int y llega "", "abc", etc. => backend devolverá 422.
    */
    const raw = String(inSesionNumero.value ?? "");

    // Construimos body de la forma que exige el endpoint:
    // { "numero_sesion": ... }
    // Pero el valor puede ser "" u otra cosa: lo validará el backend.
    const body = { numero_sesion: raw };

    await postJson(API_BASE_URL + "/moderacion/abrir_sesion", body);
    toast("ok", "OK: Abrir sesión enviado (validación en backend).");

  } catch (e){
    // Mostramos el error del backend tal cual
    toast("err", `ERROR abrir sesión: ${e?.message || String(e)}`);
  }
});

btnCerrarSesion.addEventListener("click", async () => {
  toast("warn", "Enviando: cerrar sesión…");

  try{
    await postJson(API_BASE_URL + "/moderacion/cerrar_sesion", undefined);
    toast("ok", "OK: Cerrar sesión enviado.");

  } catch (e){
    toast("err", `ERROR cerrar sesión: ${e?.message || String(e)}`);
  }
});

///////////////////////////////
// 8) COMANDOS - VOTACION (sin validación frontend)
///////////////////////////////

btnAbrirVotacion.addEventListener("click", async () => {
  toast("warn", "Enviando: abrir votación…");

  try{
    /*
      Modo testing:
      - NO parseamos numero a int.
      - NO exigimos tema.
      - NO exigimos factor numérico.
      - Mandamos “lo que hay”.
      - El backend decide si es válido.
    */

    // Votación Nº: mandamos string
    const rawNum = String(inVotNumero.value ?? "");

    // Tipo: viene del select (siempre algo)
    const tipo = String(selVotTipo.value ?? "");

    // Tema: string (puede venir vacío)
    const tema = String(inVotTema.value ?? "");

    // Respecto => boolean real
    const computa_sobre_los_presentes = (uiModel.respectoPresentes === true);

    /*
      Factor:
      - puede venir vacío ""
      - puede venir "abc"
      - puede venir "0,66"
      Para ayudar un poco:
      - reemplazamos coma por punto (0,66 -> 0.66)
      Esto NO valida. Si queda "abc", el backend fallará.
    */
    const rawFactorOriginal = String(inVotFactor.value ?? "");
    const rawFactor = rawFactorOriginal.replace(",", ".");

    // Armamos el body con exactamente los campos del endpoint.
    // OJO: los “types” pueden no coincidir => backend valida.
    const body = {
      numero: rawNum,
      tipo: tipo,
      tema: tema,
      computa_sobre_los_presentes: computa_sobre_los_presentes,
      factor_mayoria_especial: rawFactor
    };

    await postJson(API_BASE_URL + "/moderacion/abrir_votacion", body);
    toast("ok", "OK: Abrir votación enviado (validación en backend).");

  } catch (e){
    toast("err", `ERROR abrir votación: ${e?.message || String(e)}`);
  }
});

btnCerrarVotacion.addEventListener("click", async () => {
  toast("warn", "Enviando: cerrar votación…");

  try{
    await postJson(API_BASE_URL + "/moderacion/cerrar_votacion", undefined);
    toast("ok", "OK: Cerrar votación enviado.");

  } catch (e){
    toast("err", `ERROR cerrar votación: ${e?.message || String(e)}`);
  }
});

///////////////////////////////
// 9) DESEMPATE (sin validación)
///////////////////////////////

btnDesempatePositivo.addEventListener("click", async () => {
  toast("warn", "Enviando: voto desempate POSITIVO…");

  try{
    await postJson(API_BASE_URL + "/moderacion/voto_desempate", true);
    toast("ok", "OK: Desempate positivo enviado.");

  } catch (e){
    toast("err", `ERROR desempate positivo: ${e?.message || String(e)}`);
  }
});

btnDesempateNegativo.addEventListener("click", async () => {
  toast("warn", "Enviando: voto desempate NEGATIVO…");

  try{
    await postJson(API_BASE_URL + "/moderacion/voto_desempate", false);
    toast("ok", "OK: Desempate negativo enviado.");

  } catch (e){
    toast("err", `ERROR desempate negativo: ${e?.message || String(e)}`);
  }
});

///////////////////////////////
// 10) ESTADO - Normalización del JSON de /estados/estado_global
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

///////////////////////////////
// 11) RENDER FILA SESION (presentes/totales y delta quorum)
///////////////////////////////

function renderFilaSesion(state){
  const ses = getSesion(state);

  if (!ses){
    txtConcejales.textContent = "-- de -- presentes";
    txtQuorumDelta.textContent = "--";
    txtQuorumDelta.classList.remove("num-good","num-bad","num-neutral");
    txtQuorumDelta.classList.add("num-neutral");
    return;
  }

  // Preferimos los campos ya calculados por el backend
  let total = ses.cantidad_concejales;
  let presentes = ses.cantidad_presentes;

  // Fallbacks por si falta (compatibilidad)
  if (!Number.isInteger(total)){
    const concejales = Array.isArray(ses.concejales) ? ses.concejales : [];
    total = concejales.length;
  }

  if (!Number.isInteger(presentes)){
    const concejales = Array.isArray(ses.concejales) ? ses.concejales : [];
    presentes = concejales.filter(c => c?.presente === true).length;
  }

  txtConcejales.textContent = `${presentes} de ${total} presentes`;

  const quorum = Number.isInteger(ses.quorum) ? ses.quorum : null;

  if (quorum === null){
    txtQuorumDelta.textContent = "--";
    txtQuorumDelta.classList.remove("num-good","num-bad","num-neutral");
    txtQuorumDelta.classList.add("num-neutral");
    return;
  }

  const delta = presentes - quorum;
  const textDelta = delta > 0 ? `+${delta}` : `${delta}`;
  txtQuorumDelta.textContent = textDelta;

  txtQuorumDelta.classList.remove("num-good","num-bad","num-neutral");
  if (delta >= 0) txtQuorumDelta.classList.add("num-good");
  else txtQuorumDelta.classList.add("num-bad");
}

///////////////////////////////
// 12) CONTEO DE VOTOS (para texto x/n/m/z)
///////////////////////////////

function contarVotos(votacion){
  const votos = Array.isArray(votacion?.votos) ? votacion.votos : [];

  let positivos = 0;
  let negativos = 0;
  let abstenciones = 0;

  for (const v of votos){
    const val = v?.valor_voto;
    if (val === "Positivo") positivos++;
    else if (val === "Negativo") negativos++;
    else if (val === "Abstencion") abstenciones++;
  }

  return { x: votos.length, positivos, negativos, abstenciones };
}

///////////////////////////////
// 13) TOTAL ESPERADO "y" (desde sesión + votación)
///////////////////////////////

function totalEsperadoY(state, ultimaVotacion){
  const ses = getSesion(state);
  if (!ses) return 0;

  // Preferimos lo que diga la votación
  let computa = undefined;
  if (ultimaVotacion && typeof ultimaVotacion.computa_sobre_los_presentes === "boolean"){
    computa = ultimaVotacion.computa_sobre_los_presentes;
  } else {
    // fallback: toggle local (solo compatibilidad)
    computa = (uiModel.respectoPresentes === true);
  }

  // Usamos los conteos ya calculados por el backend
  let total = ses.cantidad_concejales;
  let presentes = ses.cantidad_presentes;

  // fallback si faltan
  if (!Number.isInteger(total)){
    const concejales = Array.isArray(ses.concejales) ? ses.concejales : [];
    total = concejales.length;
  }
  if (!Number.isInteger(presentes)){
    const concejales = Array.isArray(ses.concejales) ? ses.concejales : [];
    presentes = concejales.filter(c => c?.presente === true).length;
  }

  return (computa === true) ? presentes : total;
}

///////////////////////////////
// 14) MODO EMPATE + TEXTO “Estado de votación”
///////////////////////////////

let lastStateRaw = null;

function setModoEmpate(isEmpate){
  votacionNormal.style.display = isEmpate ? "none" : "";
  votacionEmpate.style.display = isEmpate ? "" : "none";
}

function textoResultadoHumano(estado){
  if (estado === "APROBADA") return "Aprobada";
  if (estado === "RECHAZADA") return "Rechazada";
  if (estado === "EMPATADA") return "Empatada";
  if (estado === "EN_CURSO") return "En curso";
  if (estado === "INCONCLUSA") return "Inconclusa";
  return String(estado || "");
}

function construirTextoEstadoVotacion(state){
  const ultima = getUltimaVotacion(state);

  if (!ultima){
    return {
      modoEmpate: false,
      textoNormal: "No hay votación en curso.",
      textoEmpate: "No hay votación en curso."
    };
  }

  const { x, positivos, negativos, abstenciones } = contarVotos(ultima);
  const y = totalEsperadoY(state, ultima);

  const numero = ultima?.numero ?? "?";
  const estado = ultima?.estado;

  if (estado === "EN_CURSO"){
    const texto =
      `Votacion ${numero} en curso: votos ${x} de ${y} - ` +
      `${positivos} positivos, ${negativos} negativos y ${abstenciones} abstenciones.`;
    return { modoEmpate: false, textoNormal: texto, textoEmpate: texto };
  }

  if (estado === "EMPATADA"){
    const texto =
      `Votacion ${numero}: Empatada- votos ${x} de ${y} - ` +
      `${positivos} positivos, ${negativos} negativos y ${abstenciones} abstenciones.`;
    return { modoEmpate: true, textoNormal: texto, textoEmpate: texto };
  }

  const estadoHumano = textoResultadoHumano(estado);
  const texto =
    `El resultado de la anterior: Votacion ${numero}: ${estadoHumano} - ` +
    `votos ${x} de ${y} - ${positivos} positivos, ${negativos} negativos y ${abstenciones} abstenciones.`;

  return { modoEmpate: false, textoNormal: texto, textoEmpate: texto };
}

function renderVotacionEstadoFromLastState(){
  if (!lastStateRaw){
    setModoEmpate(false);
    votacionEstado.textContent = "No hay votación en curso.";
    votacionEstadoEmpate.textContent = "No hay votación en curso.";
    return;
  }

  const state = normalizeState(lastStateRaw);
  const out = construirTextoEstadoVotacion(state);

  setModoEmpate(out.modoEmpate);
  votacionEstado.textContent = out.textoNormal;
  votacionEstadoEmpate.textContent = out.textoEmpate;
}

///////////////////////////////
// 15) POLLING (sin reconstruir DOM)
///////////////////////////////

let pollingRunning = false;

async function pollOnce(){
  const url = API_BASE_URL + STATE_ENDPOINT;

  try{
    const data = await getJson(url);
    lastStateRaw = data;

    setConn("ok", "Conectado");

    // Actualizamos SOLO lo necesario
    const norm = normalizeState(data);
    renderFilaSesion(norm);
    renderVotacionEstadoFromLastState();

    // Evento para paneles futuros
    document.dispatchEvent(new CustomEvent("state:update", {
      detail: { state: data, at: Date.now() }
    }));

  } catch (e){
    setConn("err", "Sin conexión");

    document.dispatchEvent(new CustomEvent("state:error", {
      detail: { error: e, at: Date.now() }
    }));
  }
}

function startPollLoop(){
  if (pollingRunning) return;
  pollingRunning = true;

  const tick = async () => {
    await pollOnce();
    setTimeout(tick, POLL_MS); // evita requests solapadas
  };

  tick();
}

///////////////////////////////
// 16) INICIO
///////////////////////////////

setConn("warn", "Conectando…");
toast("ok", "Listo.");

renderFilaSesion(normalizeState(null));
renderVotacionEstadoFromLastState();
startPollLoop();
