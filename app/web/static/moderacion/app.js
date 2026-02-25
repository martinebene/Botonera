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
const POLL_MS = 250;
const TIMEOUT_MS = 1500;

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

function stripDiacritics(s){
  // elimina acentos: "Ratificación" -> "Ratificacion"
  return String(s ?? "").normalize("NFD").replace(/[\u0300-\u036f]/g, "");
}

function normKey(str){
  // ignora mayúsculas, acentos y múltiples espacios
  return String(str ?? "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/\s+/g, " ")
    .trim();
}

function splitSemicolonLine(line){
  // split simple por ';' (mantiene vacíos)
  return String(line ?? "").split(";");
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
// 9) Q1 (Comandos)
///////////////////////////////
const Q1 = (() => {
  const inSesionNumero = document.getElementById("inSesionNumero");
  const btnAbrirSesion = document.getElementById("btnAbrirSesion");
  const btnCerrarSesion = document.getElementById("btnCerrarSesion");

  const txtConcejales = document.getElementById("txtConcejales");
  const txtQuorumDelta = document.getElementById("txtQuorumDelta");

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

  const votacionEmpate = document.getElementById("votacionEmpate");
  const btnDesempatePositivo = document.getElementById("btnDesempatePositivo");
  const btnDesempateNegativo = document.getElementById("btnDesempateNegativo");
  const votacionEstadoEmpate = document.getElementById("votacionEstadoEmpate");

  let lastVotRef = null;

  function paintToggleRespecto(){
    const pres = uiModel.respectoPresentes === true;
    togRespectoPresentes?.classList.toggle("toggle__btn--active", pres);
    togRespectoCuerpo?.classList.toggle("toggle__btn--active", !pres);
  }

  function setRespectoDefault(){
    uiModel.respectoPresentes = true;
    paintToggleRespecto();
  }

  function clearVotacionFields(){
    if (inVotNumero) inVotNumero.value = "";
    if (inVotTema) inVotTema.value = "";
    if (inVotFactor) inVotFactor.value = "";
    setRespectoDefault();
  }

  function clearSesionFields(){
    if (inSesionNumero) inSesionNumero.value = "";
  }

  function setModoEmpate(isEmpate){
    if (votacionNormal) votacionNormal.style.display = isEmpate ? "none" : "";
    if (votacionEmpate) votacionEmpate.style.display = isEmpate ? "" : "none";
  }

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


  function construirTextoEstadoVotacion(state){
    const ultima = getUltimaVotacion(state);

    if (!ultima){
      return { modoEmpate: false, textoNormal: "No hay votación en curso.", textoEmpate: "No hay votación en curso." };
    }

    const { x, positivos, negativos, abstenciones } = contarVotos(ultima);

    const numero = ultima?.numero ?? "?";
    const estado = ultima?.estado;

    if (estado === "EN_CURSO"){
      const texto =
        `Votacion ${numero} en curso: ${x} votos - ` +
        `${positivos} positivos, ${negativos} negativos y ${abstenciones} abstenciones.`;
      return { modoEmpate: false, textoNormal: texto, textoEmpate: texto };
    }

    if (estado === "EMPATADA"){
      const texto =
        `Votacion ${numero} empatada: ${x} votos - ` +
        `${positivos} positivos, ${negativos} negativos y ${abstenciones} abstenciones.`;
      return { modoEmpate: true, textoNormal: texto, textoEmpate: texto };
    }

    const estadoHumano = textoResultadoHumano(estado);
    const texto =
      `Votacion ${numero}: ${estadoHumano} ( ` +
      `${x} votos ) ${positivos} positivos, ${negativos} negativos y ${abstenciones} abstenciones.`;

    return { modoEmpate: false, textoNormal: texto, textoEmpate: texto };
  }

  function renderFilaSesion(state){
    const ses = getSesion(state);

    // Q1: Si hay sesión abierta, fijar el número y bloquear el input
    if (inSesionNumero){
      const abierta = (ses?.abierta === true);

      if (abierta){
        // Fijamos el número real que manda el backend
        inSesionNumero.value = String(ses?.numero_sesion ?? "");
        inSesionNumero.disabled = true;
      } else {
        // Si no hay sesión abierta, permitir edición
        inSesionNumero.disabled = false;
      }
    }

    if (!ses){
      if (txtConcejales) txtConcejales.textContent = "-- de -- presentes";
      if (txtQuorumDelta){
        txtQuorumDelta.textContent = "--";
        txtQuorumDelta.classList.remove("num-good","num-bad","num-neutral");
        txtQuorumDelta.classList.add("num-neutral");
      }
      return;
    }

    let total = ses.cantidad_concejales;
    let presentes = ses.cantidad_presentes;

    if (!Number.isInteger(total)){
      const concejales = Array.isArray(ses.concejales) ? ses.concejales : [];
      total = concejales.length;
    }
    if (!Number.isInteger(presentes)){
      const concejales = Array.isArray(ses.concejales) ? ses.concejales : [];
      presentes = concejales.filter(c => c?.presente === true).length;
    }

    if (txtConcejales) txtConcejales.textContent = `${presentes} de ${total} presentes`;

    const quorum = Number.isInteger(ses.quorum) ? ses.quorum : null;
    if (quorum === null){
      if (txtQuorumDelta){
        txtQuorumDelta.textContent = "--";
        txtQuorumDelta.classList.remove("num-good","num-bad","num-neutral");
        txtQuorumDelta.classList.add("num-neutral");
      }
      return;
    }

    const delta = presentes - quorum;

    if (txtQuorumDelta){
      txtQuorumDelta.textContent = delta > 0 ? `+${delta}` : `${delta}`;
      txtQuorumDelta.classList.remove("num-good","num-bad","num-neutral");
      if (delta >= 0) txtQuorumDelta.classList.add("num-good");
      else txtQuorumDelta.classList.add("num-bad");
    }
  }

  function renderVotacionEstado(raw){
    const state = normalizeState(raw);
    
    // Q1: Si hay votación abierta (EN_CURSO o EMPATADA), fijar y bloquear campos
    const ultima = getUltimaVotacion(state);
    const estadoUlt = String(ultima?.estado ?? "");
    const votAbierta = isEstadoAbiertoOVivo(estadoUlt);

    if (votAbierta && ultima){
      // 1) Fijar valores desde backend
      if (inVotNumero) inVotNumero.value = String(ultima?.numero ?? "");
      if (selVotTipo){
        const desiredKey = normKey(String(ultima?.tipo ?? ""));
        const opt = Array.from(selVotTipo.options).find(o => normKey(o.value) === desiredKey);
        if (opt) selVotTipo.value = opt.value;
        else selVotTipo.value = String(ultima?.tipo ?? "");
      }
      if (inVotTema)   inVotTema.value   = String(ultima?.tema ?? "");

      // Factor: puede venir 0; lo mostramos tal cual (si querés vacío cuando 0, lo ajustamos)
      if (inVotFactor){
        const f = (ultima?.factor_mayoria_especial ?? "");
        inVotFactor.value = String(f);
      }

      // Respecto: sincronizamos uiModel y pintamos el toggle
      if (typeof ultima?.computa_sobre_los_presentes === "boolean"){
        uiModel.respectoPresentes = (ultima.computa_sobre_los_presentes === true);
        paintToggleRespecto();
      }

      // 2) Bloquear inputs/select
      if (inVotNumero) inVotNumero.disabled = true;
      if (selVotTipo)  selVotTipo.disabled  = true;
      if (inVotFactor) inVotFactor.disabled = true;
      if (inVotTema)   inVotTema.disabled   = true;

      // 3) Bloquear toggle por clase
      const toggleWrap = togRespectoPresentes?.closest(".toggle");
      toggleWrap?.classList.add("toggle--locked");

    } else {
      // Si NO hay votación abierta, habilitar todo
      if (inVotNumero) inVotNumero.disabled = false;
      if (selVotTipo)  selVotTipo.disabled  = false;
      if (inVotFactor) inVotFactor.disabled = false;
      if (inVotTema)   inVotTema.disabled   = false;

      const toggleWrap = togRespectoPresentes?.closest(".toggle");
      toggleWrap?.classList.remove("toggle--locked");
    }

    const out = construirTextoEstadoVotacion(state);
    setModoEmpate(out.modoEmpate);
    if (votacionEstado) votacionEstado.textContent = out.textoNormal;
    if (votacionEstadoEmpate) votacionEstadoEmpate.textContent = out.textoEmpate;
  }

  function isEstadoAbiertoOVivo(estado){
    return (estado === "EN_CURSO" || estado === "EMPATADA");
  }

  function detectAndHandleVotacionFinalizada(raw){
    const state = normalizeState(raw);
    const ultima = getUltimaVotacion(state);

    if (!ultima){
      lastVotRef = null;
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
        clearVotacionFields();
      }
    }

    lastVotRef = current;
  }

  /*
    ✅ “Puente” desde Q2 (Orden del día):
    - Q2 emite bus.emit("od:row_selected", row)
    - Q1 recibe ese evento y copia valores a los inputs
    - Para el toggle “Respecto” NO tocamos uiModel directamente:
      hacemos click en el botón correspondiente para reutilizar tu lógica.
  */
  function applyOrdenDelDiaRow(row){
    try{
      // 1) Copiamos tal cual a los inputs de Q1 (trim ya viene aplicado en Q2)
      if (inVotNumero) inVotNumero.value = String(row.nro_votacion ?? "");
      if (inVotTema)   inVotTema.value   = String(row.tema ?? "");
      if (inVotFactor) inVotFactor.value = String(row.factor_de_mayoria ?? "");

      // 2) Tipo: case-insensitive, pero lo seteamos con el valor CANÓNICO del select
      //    Valores canónicos que existen en el <select>:
      //      "Despacho", "Mocion", "Sobre tabla", "Ratificacion"
      // 2) Tipo: tolerante (espacios/mayúsculas/acentos) + default "Otro"
      if (selVotTipo){
        const normKey = (str) => String(str ?? "")
          .normalize("NFD")
          .replace(/[\u0300-\u036f]/g, "")
          .toLowerCase()
          .replace(/\s+/g, " ")
          .trim();

        const desired = String(row.tipo ?? "");
        const desiredKey = normKey(desired);

        const opt = Array.from(selVotTipo.options).find(o => normKey(o.value) === desiredKey);

        if (opt){
          selVotTipo.value = opt.value;
        } else {
          // si no se encuentra, caer a "Otro" si existe
          const optOtro = Array.from(selVotTipo.options).find(o => normKey(o.value) === normKey("Otro"));
          if (optOtro) selVotTipo.value = optOtro.value;
        }
      }

      // 3) Respecto: case-insensitive
      const rLower = String(row.respecto ?? "").toLowerCase();
      if (rLower === "cuerpo"){
        togRespectoCuerpo?.click();
      } else if (rLower === "presentes"){
        togRespectoPresentes?.click();
      }
    } catch(_e){
      // Si algo falla, NO rompemos Q1: silencioso.
    }
  }

  function init(){
    // Toggle respecto: mantiene lógica previa
    togRespectoPresentes?.addEventListener("click", () => {
      uiModel.respectoPresentes = true;
      paintToggleRespecto();
    });

    togRespectoCuerpo?.addEventListener("click", () => {
      uiModel.respectoPresentes = false;
      paintToggleRespecto();
    });

    setRespectoDefault();

    // ✅ Escucha del evento emitido por Q2 al clickear una fila
    bus.on("od:row_selected", (row) => {
      applyOrdenDelDiaRow(row);
      toast("ok", "Orden del día: datos copiados a Comandos.", 1400);
    });

    // ---- Botones de sesión ----
    btnAbrirSesion?.addEventListener("click", async () => {
      toast("warn", "Enviando: abrir sesión…");
      try{
        const raw = String(inSesionNumero?.value ?? "");
        await postJson(API_BASE_URL + "/moderacion/abrir_sesion", { numero_sesion: raw });
        toast("ok", "OK: Abrir sesión enviado.");
      } catch (e){
        toast("err", `ERROR abrir sesión: ${e?.message || String(e)}`, 4000);
      }
    });

    btnCerrarSesion?.addEventListener("click", async () => {
      toast("warn", "Enviando: cerrar sesión…");
      try{
        await postJson(API_BASE_URL + "/moderacion/cerrar_sesion", undefined);
        clearSesionFields();
        clearVotacionFields();
        toast("ok", "OK: Cerrar sesión enviado.");
      } catch (e){
        toast("err", `ERROR cerrar sesión: ${e?.message || String(e)}`, 4000);
      }
    });

    // ---- Botones de votación ----
    btnAbrirVotacion?.addEventListener("click", async () => {
      toast("warn", "Enviando: abrir votación…");
      try{
        const rawNum = String(inVotNumero?.value ?? "");
        const tipo = String(selVotTipo?.value ?? "");
        const tema = String(inVotTema?.value ?? "");
        const computa_sobre_los_presentes = (uiModel.respectoPresentes === true);

        const rawFactorOriginal = String(inVotFactor?.value ?? "").trim();
        const rawFactor = rawFactorOriginal.replace(",", ".");
        const factorFinal = (rawFactor === "") ? 0 : rawFactor;

        const body = {
          numero: rawNum,
          tipo,
          tema,
          computa_sobre_los_presentes,
          factor_mayoria_especial: factorFinal,
        };

        await postJson(API_BASE_URL + "/moderacion/abrir_votacion", body);
        toast("ok", "OK: Abrir votación enviado.");
      } catch (e){
        toast("err", `ERROR abrir votación: ${e?.message || String(e)}`, 4500);
      }
    });

    btnCerrarVotacion?.addEventListener("click", async () => {
      toast("warn", "Enviando: cerrar votación…");
      try{
        await postJson(API_BASE_URL + "/moderacion/cerrar_votacion", undefined);
        clearVotacionFields();
        toast("ok", "OK: Cerrar votación enviado.");
      } catch (e){
        toast("err", `ERROR cerrar votación: ${e?.message || String(e)}`, 4000);
      }
    });

    // ---- Desempate ----
    btnDesempatePositivo?.addEventListener("click", async () => {
      toast("warn", "Enviando: desempate POSITIVO…");
      try{
        await postJson(API_BASE_URL + "/moderacion/voto_desempate", true);
        clearVotacionFields();
        toast("ok", "OK: Desempate positivo enviado.");
      } catch (e){
        toast("err", `ERROR desempate positivo: ${e?.message || String(e)}`, 4000);
      }
    });

    btnDesempateNegativo?.addEventListener("click", async () => {
      toast("warn", "Enviando: desempate NEGATIVO…");
      try{
        await postJson(API_BASE_URL + "/moderacion/voto_desempate", false);
        clearVotacionFields();
        toast("ok", "OK: Desempate negativo enviado.");
      } catch (e){
        toast("err", `ERROR desempate negativo: ${e?.message || String(e)}`, 4000);
      }
    });

    // Render inicial
    renderFilaSesion(normalizeState(null));
    renderVotacionEstado(null);
    lastVotRef = null;
  }

  function onState(raw){
    const norm = normalizeState(raw);
    detectAndHandleVotacionFinalizada(raw);
    renderFilaSesion(norm);
    renderVotacionEstado(raw);
  }

  function onError(_e){}

  return { init, onState, onError };
})();

///////////////////////////////
// 10) Q2 (Orden del día)
///////////////////////////////
const Q2 = (() => {
  // Botones e input de archivo
  const btnOdCargar = document.getElementById("btnOdCargar");
  const btnOdLimpiar = document.getElementById("btnOdLimpiar");
  const fileOdCsv = document.getElementById("fileOdCsv");

  // Tabla
  const odTbody = document.getElementById("odTbody");
  const odInfo = document.getElementById("odInfo");

  // Estado interno del Q2
  let rows = [];              // Array de filas parseadas del CSV
  let selectedIndex = -1;     // Para marcar visualmente la fila seleccionada

  // Header exacto requerido (case-sensitive, sin espacios)
  const REQUIRED_HEADER = "nro_votacion;tipo;tema;factor_de_mayoria;respecto";

  // Valores canónicos aceptados para tipo y respecto (case-insensitive)
  const TIPO_ALLOWED_CANON = [
    "Ratificación",
    "Despacho OP",
    "Despacho Gob",
    "Despacho AS",
    "Despacho HA",
    "Despacho Eco",
    "Mocion",
    "P. Sobre Tabla",
    "Otro",
  ];
  const RESPECTO_ALLOWED_CANON = ["Presentes", "Cuerpo"];

  /*
    --------------------------
    CSV PARSER con comillas
    --------------------------
    Reglas que implementamos:
    - Header NO va con comillas (línea exacta REQUIRED_HEADER)
    - Datos: cada fila debe tener 5 campos, y TODOS los campos van entre comillas dobles:
        "campo1","campo2","campo3","campo4","campo5"
    - Dentro de un campo, una comilla doble se escribe como "" (doble comilla)
    - Se permiten comas en el tema gracias a las comillas.
    - También soporta saltos de línea dentro de campos (por seguridad),
      aunque normalmente no los vas a usar.

    Resultado:
    - Devuelve Array de filas, donde cada fila es Array<string> de largo 5.
    - Si detecta formato inválido => lanza Error (reject).
  */

  function readFirstLineAndRest(text){
    // Normalizamos saltos de línea para facilitar
    const s = String(text ?? "").replace(/\r\n/g, "\n").replace(/\r/g, "\n");
    const idx = s.indexOf("\n");
    if (idx === -1) {
      return { firstLine: s, rest: "" };
    }
    return { firstLine: s.slice(0, idx), rest: s.slice(idx + 1) };
  }

  function parseQuotedCsvRecords(dataText){
    const s = String(dataText ?? "");

    const records = [];
    let record = [];
    let field = "";

    // Estado del parser
    let inQuotes = false;

    // Recorremos carácter por carácter (parser simple pero robusto)
    for (let i = 0; i < s.length; i++){
      const ch = s[i];

      if (inQuotes){
        if (ch === '"'){
          // Puede ser fin de campo, o una comilla escapada ("")
          const next = s[i + 1];
          if (next === '"'){
            // Comilla escapada -> agregamos una comilla y saltamos el siguiente carácter
            field += '"';
            i++;
          } else {
            // Fin de comillas de este campo
            inQuotes = false;
          }
        } else {
          // Cualquier otro carácter dentro de comillas se agrega tal cual (incluye comas y \n)
          field += ch;
        }
        continue;
      }

      // NO estamos enQuotes
      if (ch === '"'){
        // Inicio de un campo entre comillas
        inQuotes = true;
        continue;
      }

      if (ch === ','){
        // Fin de campo
        record.push(field);
        field = "";
        continue;
      }

      if (ch === '\n'){
        // Fin de record (fila)
        record.push(field);
        field = "";

        // Si la fila no está totalmente vacía, la agregamos
        const isEmptyRow = record.length === 1 && record[0] === "";
        if (!isEmptyRow) records.push(record);

        record = [];
        continue;
      }

      // Si hay caracteres fuera de comillas, el formato no es estrictamente válido.
      // Permitimos SOLO espacios/tabs fuera para tolerar casos menores,
      // pero como vos pediste estricto, lo rechazamos si aparece algo no whitespace.
      if (ch !== ' ' && ch !== '\t'){
        throw new Error(`CSV inválido: carácter fuera de comillas en datos: '${ch}'`);
      }
      // si es whitespace, lo ignoramos
    }

    // Flush final (último record si no termina en \n)
    record.push(field);

    const allEmpty = record.every(x => x === "");
    if (!allEmpty){
      records.push(record);
    }

    // Validación: no podemos terminar con comillas abiertas
    if (inQuotes){
      throw new Error("CSV inválido: comillas sin cerrar.");
    }

    return records;
  }

  function normalizeTrim(x){
    return String(x ?? "").trim();
  }

  // Validación estricta (pero tipo/respecto case-insensitive)
  function validateAndBuildRows(records){
    const out = [];

    for (let rowIndex = 0; rowIndex < records.length; rowIndex++){
      const rec = records[rowIndex];

      // Cada fila debe tener exactamente 5 campos
      if (!Array.isArray(rec) || rec.length !== 5){
        throw new Error(`CSV inválido: fila ${rowIndex + 1} debe tener 5 columnas (tiene ${rec.length}).`);
      }

      // Trim de cada campo (solo inicio/fin)
      const nro = normalizeTrim(rec[0]);
      const tipoRaw = normalizeTrim(rec[1]);
      const tema = normalizeTrim(rec[2]);
      const factorRaw = normalizeTrim(rec[3]);
      const respectoRaw = normalizeTrim(rec[4]);

      // nro_votacion: solo dígitos, no vacío
      if (!/^[0-9]+$/.test(nro)){
        throw new Error(`CSV inválido: nro_votacion inválido en fila ${rowIndex + 1} ("${nro}").`);
      }

      // tema: no vacío (puede tener comas y lo que sea)
      if (tema.length === 0){
        throw new Error(`CSV inválido: tema vacío en fila ${rowIndex + 1}.`);
      }

      // tipo: tolerante (ignora mayúsculas, acentos y espacios extra)
      // si no matchea, por defecto "Otro"
      const tipoCanon = TIPO_ALLOWED_CANON.find(v => normKey(v) === normKey(tipoRaw)) ?? "Otro";

      // Si no coincide con ninguno → usar "Otro"
      if (!tipoCanon){
        tipoCanon = "Otro";
      }

      // respecto: case-insensitive, pero debe corresponder a un valor permitido
      const respectoCanon = RESPECTO_ALLOWED_CANON.find(v => v.toLowerCase() === respectoRaw.toLowerCase());
      if (!respectoCanon){
        throw new Error(
          `CSV inválido: respecto inválido en fila ${rowIndex + 1} ("${respectoRaw}"). ` +
          `Permitidos: ${RESPECTO_ALLOWED_CANON.join(", ")}`
        );
      }

      // factor_de_mayoria:
      // - "" o "0" => ok
      // - decimal 0..1 con punto => ok (".66", "0.66", "1", "1.0")
      // - no se permite coma decimal ni "%"
      let factorNormalized = factorRaw;

      if (factorNormalized === "" || factorNormalized === "0"){
        factorNormalized = ""; // mantenemos vacío en tabla (y Q1 lo transforma a 0 al enviar)
      } else {
        // Rechazamos coma decimal o %
        if (factorNormalized.includes(",") || factorNormalized.includes("%")){
          throw new Error(`CSV inválido: factor_de_mayoria inválido en fila ${rowIndex + 1} ("${factorRaw}").`);
        }

        // Permitimos ".66" o "0.66" o "1" o "1.0"
        if (!/^(?:0?\.[0-9]+|1(?:\.0+)?)$/.test(factorNormalized)){
          throw new Error(`CSV inválido: factor_de_mayoria inválido en fila ${rowIndex + 1} ("${factorRaw}").`);
        }

        // Validación numérica 0..1
        const asNum = Number(factorNormalized);
        if (!Number.isFinite(asNum) || asNum < 0 || asNum > 1){
          throw new Error(`CSV inválido: factor_de_mayoria fuera de rango 0..1 en fila ${rowIndex + 1} ("${factorRaw}").`);
        }
      }

      out.push({
        nro_votacion: nro,
        tipo: tipoCanon,                 // guardamos valor CANÓNICO
        tema: tema,
        factor_de_mayoria: factorNormalized, // "" o decimal
        respecto: respectoCanon,          // guardamos valor CANÓNICO
      });
    }

    return out;
  }

  /*
    Parse principal: recibe el texto del archivo completo.
    1) separa primera línea (header) + el resto (datos)
    2) valida header EXACTO
    3) parsea datos con comillas
    4) valida y normaliza filas
  */
  function parseOrdenDelDiaCsvStrict(text){
    const { firstLine, rest } = readFirstLineAndRest(text);

    // 1) Header: debe ser exactamente esas 5 columnas, separadas por ';'
    //    (toleramos espacios, mayúsculas y acentos SOLO en el header)
    const expectedCols = splitSemicolonLine(REQUIRED_HEADER).map(normKey);
    const gotCols = splitSemicolonLine(firstLine).map(normKey);

    if (gotCols.length !== expectedCols.length || gotCols.some((c, i) => c !== expectedCols[i])){
      throw new Error(
        `CSV inválido: header incorrecto.\n` +
        `Esperado: ${REQUIRED_HEADER}\n` +
        `Recibido: ${firstLine}`
      );
    }

    // 2) Parse filas: cada línea no vacía => 5 columnas separadas por ';'
    const s = String(rest ?? "").replace(/\r\n/g, "\n").replace(/\r/g, "\n");
    const lines = s.split("\n").filter(l => normKey(l).length > 0);

    const records = lines.map((line, idx) => {
      const cols = splitSemicolonLine(line);
      if (cols.length !== 5){
        throw new Error(`CSV inválido: fila ${idx + 1} debe tener 5 columnas (tiene ${cols.length}).`);
      }
      return cols;
    });

    // 3) Permitimos archivo con header pero sin filas (tabla vacía)
    if (records.length === 0) return [];

    // 4) Validación y normalización a objetos
    return validateAndBuildRows(records);
  }

  function clearTable(){
    rows = [];
    selectedIndex = -1;

    if (odTbody) odTbody.innerHTML = "";
    if (odInfo) odInfo.textContent = "Sin archivo cargado.";

    // Reset del input: permite seleccionar el mismo archivo 2 veces seguidas
    if (fileOdCsv) fileOdCsv.value = "";
  }

  function renderTable(){
    if (!odTbody) return;

    odTbody.innerHTML = "";

    for (let i = 0; i < rows.length; i++){
      const r = rows[i];

      const tr = document.createElement("tr");

      // Marcado visual si está seleccionada
      if (i === selectedIndex) tr.classList.add("od__row--selected");

      // Guardamos el índice para identificar click
      tr.dataset.idx = String(i);

      // Celdas (en orden)
      const tdNro = document.createElement("td");
      tdNro.textContent = String(r.nro_votacion ?? "");

      const tdTipo = document.createElement("td");
      tdTipo.textContent = String(r.tipo ?? "");

      const tdTema = document.createElement("td");
      tdTema.textContent = String(r.tema ?? "");

      const tdFactor = document.createElement("td");
      tdFactor.textContent = String(r.factor_de_mayoria ?? "");

      const tdRespecto = document.createElement("td");
      tdRespecto.textContent = String(r.respecto ?? "");

      tr.appendChild(tdNro);
      tr.appendChild(tdTipo);
      tr.appendChild(tdTema);
      tr.appendChild(tdFactor);
      tr.appendChild(tdRespecto);

      odTbody.appendChild(tr);
    }

    if (odInfo){
      odInfo.textContent = rows.length
        ? `Filas cargadas: ${rows.length}. Click en una fila para copiar a Comandos.`
        : "Archivo válido, pero sin filas.";
    }
  }

  function onRowClick(evt){
    const tr = evt.target?.closest("tr");
    if (!tr) return;

    const idx = Number(tr.dataset.idx);
    if (!Number.isFinite(idx)) return;
    if (idx < 0 || idx >= rows.length) return;

    selectedIndex = idx;
    renderTable(); // re-render para marcar selección

    // Emitimos hacia Q1 (sin acoplar Q2 con Q1)
    bus.emit("od:row_selected", rows[idx]);
  }

  function init(){
    // Arranca vacío
    clearTable();

    // Cargar CSV
    btnOdCargar?.addEventListener("click", () => {
      // No podemos forzar carpeta. El navegador suele recordar la última.
      fileOdCsv?.click();
    });

    // Limpiar
    btnOdLimpiar?.addEventListener("click", () => {
      clearTable();
      toast("ok", "Orden del día: tabla limpia.", 1200);
    });

    // Archivo seleccionado
    fileOdCsv?.addEventListener("change", () => {
      const f = fileOdCsv.files && fileOdCsv.files[0];
      if (!f) return;

      // Reemplaza TODO el contenido (como pediste)
      clearTable();

      const reader = new FileReader();

      reader.onload = () => {
        try{
          const text = String(reader.result ?? "");
          rows = parseOrdenDelDiaCsvStrict(text);
          selectedIndex = -1;
          renderTable();
          toast("ok", `CSV cargado: ${f.name}`, 1500);
        } catch (e){
          // Rechazo estricto: tabla queda vacía
          clearTable();
          toast("err", `CSV inválido: ${e?.message || String(e)}`, 6000);
        }
      };

      reader.onerror = () => {
        clearTable();
        toast("err", "No se pudo leer el archivo CSV.", 3000);
      };

      reader.readAsText(f, "utf-8");
    });

    // Click en filas (delegación)
    odTbody?.addEventListener("click", onRowClick);
  }

  function onState(_raw){
    // Q2 no depende del backend (solo CSV local)
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
  const btnOtorgarPalabra = document.getElementById("btnOtorgarPalabra");
  const btnQuitarPalabra  = document.getElementById("btnQuitarPalabra");

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
      const banca = (c?.banca !== undefined && c?.banca !== null) ? ` (B${c.banca})` : "";
      li.textContent = `${ape} ${nom}${banca}`.trim();
      ulUsoPalabra.appendChild(li);
    }
  }

  function clearAllVoteTexts(){
    for (const [_b, els] of bancaEls){
      if (!els?.voteEl) continue;
      els.voteEl.textContent = "";
      els.voteEl.classList.remove("is-voto", "voto-pos", "voto-neg", "voto-abs");
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
        if (cls) els.voteEl.classList.add(cls);
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
    let delayMs = 4000;
    const hf = vRef?.hora_fin ? Date.parse(String(vRef.hora_fin)) : NaN;
    if (Number.isFinite(hf)){
      delayMs = Math.max(0, (hf + 4000) - now);
    }

    clearVotesTimer = setTimeout(() => {
      clearAllVoteTexts();
      activeVotRef = null;
      clearVotesTimer = null;
    }, delayMs);
  }
}


  function init(){
    // Botones uso palabra
    btnOtorgarPalabra?.addEventListener("click", async () => {
      toast("warn", "Enviando: otorgar uso de palabra…");
      try{
        await postJson(API_BASE_URL + "/moderacion/otorgar_uso_palabra", undefined);
        toast("ok", "OK: Otorgar palabra enviado.", 1400);
      } catch (e){
        toast("err", `ERROR otorgar palabra: ${e?.message || String(e)}`, 4500);
      }
    });

    btnQuitarPalabra?.addEventListener("click", async () => {
      toast("warn", "Enviando: quitar uso de palabra…");
      try{
        await postJson(API_BASE_URL + "/moderacion/quitar_uso_palabra", undefined);
        toast("ok", "OK: Quitar palabra enviado.", 1400);
      } catch (e){
        toast("err", `ERROR quitar palabra: ${e?.message || String(e)}`, 4500);
      }
    });

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
const Quadrants = [Q1, Q2, Q3, Q4];

///////////////////////////////
// 14) Polling core
///////////////////////////////
let pollingRunning = false;

async function pollOnce(){
  const url = API_BASE_URL + STATE_ENDPOINT;

  try{
    const data = await getJson(url);
    setConn("ok", "Conectado");
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
