/*
  app.js
  ======

  Cambios solicitados:
  1) En la fila de sesión:
     - Mostrar "x de y presentes" usando datos de la API:
         sesion.cantidad_presentes
         sesion.cantidad_concejales
     - Mostrar delta de quorum:
         delta = cantidad_presentes - quorum
       y pintar:
         verde si delta >= 0
         rojo  si delta < 0

  2) Revisar si con el nuevo to_dict hay estados que antes calculábamos en frontend,
     y ahora los entrega la API.
     => Sí:
        - Antes "cantidad_presentes" se infería contando concejales en frontend.
        - Ahora viene directo en sesion.cantidad_presentes, así que se usa ese dato.
        - Antes "cantidad_concejales" se infería por len(concejales).
        - Ahora viene directo en sesion.cantidad_concejales.

  3) Para el texto "votos x de y":
     - y ahora se calcula usando:
        - si computa_sobre_los_presentes == true  => y = sesion.cantidad_presentes
        - si computa_sobre_los_presentes == false => y = sesion.cantidad_concejales
     (y si por compatibilidad no viene alguno, hacemos fallback al conteo anterior)
*/

///////////////////////////////
// 1) CONFIG
///////////////////////////////

const API_BASE_URL = "";
const STATE_ENDPOINT = "/estados/estado_global";
const POLL_MS = 250;
const TIMEOUT_MS = 1500;

///////////////////////////////
// 2) DOM refs
///////////////////////////////

// Topbar
const connText = document.getElementById("connText");
const clockEl  = document.getElementById("clock");

// Sesión (editable)
const inSesionNumero = document.getElementById("inSesionNumero");
const btnAbrirSesion = document.getElementById("btnAbrirSesion");
const btnCerrarSesion = document.getElementById("btnCerrarSesion");

// Sesión (solo lectura - NUEVOS)
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

// Voto desempate (modo empate)
const votacionEmpate = document.getElementById("votacionEmpate");
const btnDesempatePositivo = document.getElementById("btnDesempatePositivo");
const btnDesempateNegativo = document.getElementById("btnDesempateNegativo");
const votacionEstadoEmpate = document.getElementById("votacionEstadoEmpate");

// Toast
const toastEl = document.getElementById("toast");

///////////////////////////////
// 3) Reloj local
///////////////////////////////

function updateClock(){
  clockEl.textContent = new Date().toLocaleString("es-AR");
}
updateClock();
setInterval(updateClock, 250);

///////////////////////////////
// 4) Helpers UI
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
// 5) Fetch con timeout
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
    headers: {
      "Content-Type":"application/json",
      "Accept":"application/json"
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  const text = await res.text();
  if (!res.ok) throw new Error(`HTTP ${res.status} - ${text}`);

  try { return JSON.parse(text); }
  catch { return { ok:true, raw:text }; }
}

///////////////////////////////
// 6) UI Model (para abrir votación)
///////////////////////////////

const uiModel = {
  respectoPresentes: true
};

///////////////////////////////
// 7) Toggle "Respecto" (solo influye al ABRIR votación)
///////////////////////////////

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
// 8) Comandos sesión
///////////////////////////////

btnAbrirSesion.addEventListener("click", async () => {
  toast("warn", "Enviando: abrir sesión…");
  try{
    const raw = String(inSesionNumero.value || "").trim();
    const numero = parseInt(raw, 10);
    if (!Number.isInteger(numero)){
      throw new Error("Sesión Nº inválido (ingresá un entero).");
    }
    await postJson(API_BASE_URL + "/moderacion/abrir_sesion", { numero_sesion: numero });
    toast("ok", `OK: Abrir sesión ${numero} enviado.`);
  } catch (e){
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
// 9) Comandos votación (modo normal)
///////////////////////////////

btnAbrirVotacion.addEventListener("click", async () => {
  toast("warn", "Enviando: abrir votación…");
  try{
    const rawNum = String(inVotNumero.value || "").trim();
    const numero = parseInt(rawNum, 10);
    if (!Number.isInteger(numero)){
      throw new Error("Votación Nº inválido (ingresá un entero).");
    }

    const tipo = String(selVotTipo.value || "").trim();
    const tema = String(inVotTema.value || "").trim();
    if (!tema){
      throw new Error("Tema requerido (no puede estar vacío).");
    }

    const computa_sobre_los_presentes = (uiModel.respectoPresentes === true);

    const rawFactor = String(inVotFactor.value ?? "").trim();
    let factor_mayoria_especial = 0;
    if (rawFactor !== ""){
      factor_mayoria_especial = parseFloat(rawFactor.replace(",", "."));
      if (!Number.isFinite(factor_mayoria_especial)){
        throw new Error("Factor de mayoría inválido (número, 0 o vacío).");
      }
    }

    const body = {
      numero,
      tipo,
      tema,
      computa_sobre_los_presentes,
      factor_mayoria_especial
    };

    await postJson(API_BASE_URL + "/moderacion/abrir_votacion", body);
    toast("ok", `OK: Abrir votación ${numero} enviado.`);
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
// 10) Desempate
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
// 11) Normalización del estado
///////////////////////////////

function normalizeState(raw){
  if (!raw) return { sesion: null };
  if (raw.sesion !== undefined) return raw;   // si ya viene {sesion: ...}
  return { sesion: raw };                      // si viene directo la sesión
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
// 12) Render fila sesión (NUEVO)
///////////////////////////////

/*
  Esta función actualiza:
  - "x de y presentes" usando sesion.cantidad_presentes y sesion.cantidad_concejales
  - "delta quorum" = presentes - quorum

  Si por compatibilidad faltan esos campos, hacemos fallback a:
  - cantidad_concejales = concejales.length
  - cantidad_presentes = contar concejales con presente=true
*/
function renderFilaSesion(state){
  const ses = getSesion(state);

  // Si no hay sesión (o es null), mostramos placeholders “bonitos”
  if (!ses){
    txtConcejales.textContent = "-- de -- presentes";
    txtQuorumDelta.textContent = "--";
    txtQuorumDelta.classList.remove("num-good","num-bad","num-neutral");
    txtQuorumDelta.classList.add("num-neutral");
    return;
  }

  // 1) Total concejales (preferimos API)
  let total = ses.cantidad_concejales;

  // fallback: si no vino, usamos lista concejales
  if (!Number.isInteger(total)){
    const concejales = Array.isArray(ses.concejales) ? ses.concejales : [];
    total = concejales.length;
  }

  // 2) Presentes (preferimos API)
  let presentes = ses.cantidad_presentes;

  // fallback: si no vino, contamos
  if (!Number.isInteger(presentes)){
    const concejales = Array.isArray(ses.concejales) ? ses.concejales : [];
    presentes = concejales.filter(c => c?.presente === true).length;
  }

  // 3) Texto "x de y presentes"
  txtConcejales.textContent = `${presentes} de ${total} presentes`;

  // 4) Delta de quorum
  // quorum viene en ses.quorum según tu to_dict
  const quorum = Number.isInteger(ses.quorum) ? ses.quorum : null;

  if (quorum === null){
    // si no viene quorum, mostramos "--" neutral
    txtQuorumDelta.textContent = "--";
    txtQuorumDelta.classList.remove("num-good","num-bad","num-neutral");
    txtQuorumDelta.classList.add("num-neutral");
    return;
  }

  const delta = presentes - quorum;

  // Formato: +2, -1, 0
  const textDelta = delta > 0 ? `+${delta}` : `${delta}`;
  txtQuorumDelta.textContent = textDelta;

  // Color:
  // - verde si delta >= 0
  // - rojo si delta < 0
  txtQuorumDelta.classList.remove("num-good","num-bad","num-neutral");
  if (delta >= 0) txtQuorumDelta.classList.add("num-good");
  else txtQuorumDelta.classList.add("num-bad");
}

///////////////////////////////
// 13) Conteo de votos
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

  const x = votos.length;
  return { x, positivos, negativos, abstenciones };
}

///////////////////////////////
// 14) Total esperado "y" (actualizado: ahora usa API de sesión)
///////////////////////////////

/*
  y depende de la votación:
  - si ultima.computa_sobre_los_presentes == true:
      y = sesion.cantidad_presentes  (API)
  - si == false:
      y = sesion.cantidad_concejales (API)

  Fallbacks:
  - si faltan esos campos, caemos a conteos por lista.
*/
function totalEsperadoY(state, ultimaVotacion){
  const ses = getSesion(state);

  // Si no hay sesión, devolvemos 0 (para que no reviente el texto)
  if (!ses){
    return 0;
  }

  // Determinamos “computa”:
  // 1) Preferimos lo que diga la votación (API)
  // 2) Si no viene, usamos toggle local (solo por compatibilidad)
  let computa = undefined;

  if (ultimaVotacion && typeof ultimaVotacion.computa_sobre_los_presentes === "boolean"){
    computa = ultimaVotacion.computa_sobre_los_presentes;
  } else {
    computa = (uiModel.respectoPresentes === true);
  }

  // Total y presentes (preferimos API)
  let total = ses.cantidad_concejales;
  let presentes = ses.cantidad_presentes;

  // fallback total
  if (!Number.isInteger(total)){
    const concejales = Array.isArray(ses.concejales) ? ses.concejales : [];
    total = concejales.length;
  }

  // fallback presentes
  if (!Number.isInteger(presentes)){
    const concejales = Array.isArray(ses.concejales) ? ses.concejales : [];
    presentes = concejales.filter(c => c?.presente === true).length;
  }

  // Elegimos según computa
  return (computa === true) ? presentes : total;
}

///////////////////////////////
// 15) Modo empate + texto estado votación
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
// 16) Polling (actualiza solo lo necesario)
///////////////////////////////

let pollingRunning = false;

async function pollOnce(){
  const url = API_BASE_URL + STATE_ENDPOINT;

  try{
    const data = await getJson(url);
    lastStateRaw = data;

    setConn("ok", "Conectado");

    // 1) Actualizar fila sesión (concejales + quorum delta)
    renderFilaSesion(normalizeState(data));

    // 2) Actualizar estado de votación + modo empate
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
    setTimeout(tick, POLL_MS);
  };

  tick();
}

///////////////////////////////
// 17) Inicio
///////////////////////////////

setConn("warn", "Conectando…");
toast("ok", "Listo.");

// Estado inicial
renderFilaSesion(normalizeState(null));
renderVotacionEstadoFromLastState();

// Arrancar polling
startPollLoop();
