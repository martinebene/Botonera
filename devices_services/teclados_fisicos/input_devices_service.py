#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Servicio de teclados físicos -> Backend de votación
===================================================

Windows: Raw Input (WM_INPUT) con ctypes (sin pywinusb).
Linux: evdev.

Objetivo:
- Identificar qué teclado/numpad físico originó la tecla.
- Traducir la tecla a formato backend (ej "1" para KP1).
- Enviar POST al backend:
    POST http://127.0.0.1:8000/entradas/tecla
    JSON {"dispositivo":"dev01","tecla":"1"}

Menú:
  1) Iniciar (manda POST)
  2) Ver mapeo
  3) Probar mapeo (no manda POST)
  4) Mapear teclados (captura dispositivo por una tecla)
  5) Debug input (ver eventos crudos y dispositivo)
  6) Salir

Auto-inicio:
- Si DEBUG=False: si no elegís en 5s -> inicia.
- Si DEBUG=True: sin auto-inicio (para debug).

Mapeo:
- JSON en ./data/mapeo_teclados.json
- Key (fingerprint):
    - Windows: "win|<RIDI_DEVICENAME>" (string único del Raw Input)
    - Linux:   "lin|vendor=...|product=...|phys=...|uniq=...|name=..."
- Value: devXX (ej dev01, dev02...)

Dependencias:
- Windows: py -m pip install requests
- Linux : py -m pip install requests evdev
"""

from __future__ import annotations

import json
import os
import sys
import time
import signal
import threading
import platform
from dataclasses import dataclass
from typing import Dict, Optional, Callable, Tuple

import requests

# =========================
# CONFIG
# =========================

API_BASE_URL = "http://127.0.0.1:8000"
API_PATH = "/entradas/tecla"
API_URL = f"{API_BASE_URL}{API_PATH}"
HTTP_TIMEOUT = 1.5

DEFAULT_MAPPING_FILE = os.path.join(os.path.dirname(__file__), "data", "mapeo_teclados.json")

# DEBUG=True:
# - NO limpiamos consola
# - NO auto-inicio
# - logs detallados
DEBUG = False


def dprint(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs)


# =========================
# Consola / util
# =========================

def clear_console():
    """
    Limpia la consola SOLO si no estamos en modo DEBUG.
    En DEBUG se deja todo para no perder logs.
    """
    if DEBUG:
        return

    if os.name == "nt":      # Windows
        os.system("cls")
    else:                    # Linux / macOS
        os.system("clear")



def print_header():
    print("=" * 70)
    print(" Servicio de Teclados -> Backend de Votación (Linux + Windows) ")
    print("=" * 70)
    print(f"API: {API_URL}")
    print(f"SO : {platform.system()} ({platform.release()})")
    print(f"DEBUG: {DEBUG}")
    print()


def input_with_timeout(prompt: str, timeout_sec: int) -> Optional[str]:
    """Input con timeout (solo si DEBUG=False)."""
    result = {"value": None}

    def _reader():
        try:
            flush_stdin()
            result["value"] = input(prompt)
        except Exception:
            result["value"] = None

    t = threading.Thread(target=_reader, daemon=True)
    t.start()
    t.join(timeout=timeout_sec)
    if t.is_alive():
        return None
    return result["value"]


def ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(path)
    if parent and not os.path.isdir(parent):
        os.makedirs(parent, exist_ok=True)


def load_mapping(path: str) -> Dict[str, str]:
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {}
        out: Dict[str, str] = {}
        for k, v in data.items():
            if isinstance(k, str) and isinstance(v, str) and v.strip():
                out[k] = v.strip()
        return out
    except Exception:
        return {}


def save_mapping(path: str, mapping: Dict[str, str]) -> None:
    ensure_parent_dir(path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2, sort_keys=True)


def post_key_to_backend(dispositivo: str, tecla: str) -> Tuple[bool, str]:
    payload = {"dispositivo": dispositivo, "tecla": tecla}
    try:
        r = requests.post(API_URL, json=payload, timeout=HTTP_TIMEOUT)
        if 200 <= r.status_code < 300:
            return True, f"HTTP {r.status_code}"
        return False, f"HTTP {r.status_code}: {r.text[:200]}"
    except Exception as e:
        return False, f"ERROR: {e}"


# =========================
# Normalización de teclas
# =========================

def normalize_key_for_api(key_name: str) -> Optional[str]:
    """Convierte nombres internos a lo que quiere el backend (ej 'KP1'->'1')."""
    if not key_name:
        return None
    k = key_name.upper().strip()

    kp = {
        "KP0": "0", "KP1": "1", "KP2": "2", "KP3": "3", "KP4": "4",
        "KP5": "5", "KP6": "6", "KP7": "7", "KP8": "8", "KP9": "9",
        "KPDOT": ".", "KPPLUS": "+", "KPMINUS": "-", "KPASTERISK": "*", "KPSLASH": "/",
        "KPENTER": "ENTER",
    }
    if k in kp:
        return kp[k]

    if k in {"0", "1", "2", "3", "4", "5", "6", "7", "8", "9"}:
        return k

    common = {"ENTER": "ENTER", "ESC": "ESC", "TAB": "TAB", "SPACE": "SPACE", "BACKSPACE": "BACKSPACE"}
    if k in common:
        return common[k]

    return None


# =========================
# Modelo común
# =========================

@dataclass
class KeyPress:
    device_id: str
    device_desc: str
    key_name: str


# ===========================================================
# Linux: evdev
# ===========================================================

def linux_supported() -> bool:
    return platform.system().lower() == "linux"


class LinuxKeyboardListener:
    def __init__(self, on_keypress: Callable[[KeyPress], None]):
        self.on_keypress = on_keypress
        self._stop = threading.Event()
        self._devices = []

    def stop(self):
        self._stop.set()

    def _open_devices(self):
        from evdev import InputDevice, list_devices, ecodes
        self._devices = []
        for path in list_devices():
            try:
                dev = InputDevice(path)
                caps = dev.capabilities(verbose=False)
                if ecodes.EV_KEY in caps:
                    self._devices.append(dev)
                else:
                    dev.close()
            except Exception:
                continue

        dprint("\n[LINUX] Dispositivos con EV_KEY abiertos:")
        for d in self._devices:
            try:
                dprint(f"  - {d.path} | {d.name} | phys={d.phys} uniq={d.uniq}")
            except Exception:
                pass
        dprint("")

    def _fingerprint(self, dev) -> str:
        info = dev.info
        phys = (dev.phys or "").strip()
        uniq = (dev.uniq or "").strip()
        name = (dev.name or "").strip()
        return (
            "lin|"
            f"vendor={info.vendor:04x}|product={info.product:04x}|version={info.version:04x}"
            f"|phys={phys}|uniq={uniq}|name={name}"
        )

    def run(self):
        from evdev import ecodes
        from evdev.events import KeyEvent
        from evdev import util as evutil

        self._open_devices()
        if not self._devices:
            print("⚠ Linux: no se encontraron teclados accesibles.")
            print("   - ¿Permisos para /dev/input/event* ? Probá con sudo.")
            return

        while not self._stop.is_set():
            try:
                r, _, _ = evutil.select(self._devices, [], [], 0.25)
                for dev in r:
                    for event in dev.read():
                        if event.type != ecodes.EV_KEY:
                            continue
                        ke = KeyEvent(event)
                        if ke.keystate != KeyEvent.key_down:
                            continue

                        key_name = ecodes.KEY.get(event.code, f"KEY_{event.code}")
                        if key_name.startswith("KEY_"):
                            key_name_simple = key_name[4:]
                        else:
                            key_name_simple = key_name

                        dprint(f"[LINUX][KEYDOWN] dev={dev.path} key={key_name_simple}")

                        kp = KeyPress(
                            device_id=self._fingerprint(dev),
                            device_desc=f"{dev.path} | {dev.name}",
                            key_name=key_name_simple
                        )
                        self.on_keypress(kp)

            except (OSError, IOError):
                try:
                    for d in self._devices:
                        try:
                            d.close()
                        except Exception:
                            pass
                finally:
                    self._open_devices()
            except Exception as e:
                dprint(f"[LINUX][EXC] {e}")
                continue

        for d in self._devices:
            try:
                d.close()
            except Exception:
                pass


# ===========================================================
# Windows: Raw Input (ctypes)
# ===========================================================

def windows_supported() -> bool:
    return platform.system().lower() == "windows"


class WindowsRawInputKeyboardListener:
    def __init__(self, on_keypress: Callable[[KeyPress], None], debug_mode: bool = False):
        self.on_keypress = on_keypress
        self.debug_mode = debug_mode
        self._stop = threading.Event()
        self._devname_cache: Dict[int, str] = {}
        self._devdesc_cache: Dict[int, str] = {}

    def stop(self):
        self._stop.set()

    def _flush_stdin_buffer(self):
        """Evita que teclas presionadas queden en el buffer del input() del menú."""
        try:
            import msvcrt
            while msvcrt.kbhit():
                msvcrt.getwch()
        except Exception:
            pass

    def run(self):
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

        # --------- TIPOS CORRECTOS 64-bit / 32-bit (pointer-sized) ----------
        # WPARAM es unsigned pointer-sized, LPARAM es signed pointer-sized, LRESULT signed pointer-sized
        WPARAM = ctypes.c_size_t
        LPARAM = ctypes.c_ssize_t
        LRESULT = ctypes.c_ssize_t

        # en algunas versiones no existe HRAWINPUT, lo definimos
        HRAWINPUT = wintypes.HANDLE

        # --- Constantes ---
        WM_INPUT = 0x00FF
        RID_INPUT = 0x10000003
        RIM_TYPEKEYBOARD = 1
        RIDI_DEVICENAME = 0x20000007
        PM_REMOVE = 0x0001

        RIDEV_INPUTSINK = 0x00000100

        # RAWINPUTDEVICE usUsagePage/usUsage (teclado = 0x01/0x06)
        class RAWINPUTDEVICE(ctypes.Structure):
            _fields_ = [
                ("usUsagePage", wintypes.USHORT),
                ("usUsage", wintypes.USHORT),
                ("dwFlags", wintypes.DWORD),
                ("hwndTarget", wintypes.HWND),
            ]

        class RAWINPUTHEADER(ctypes.Structure):
            _fields_ = [
                ("dwType", wintypes.DWORD),
                ("dwSize", wintypes.DWORD),
                ("hDevice", wintypes.HANDLE),
                ("wParam", wintypes.WPARAM),
            ]

        class RAWKEYBOARD(ctypes.Structure):
            _fields_ = [
                ("MakeCode", wintypes.USHORT),
                ("Flags", wintypes.USHORT),
                ("Reserved", wintypes.USHORT),
                ("VKey", wintypes.USHORT),
                ("Message", wintypes.UINT),
                ("ExtraInformation", wintypes.ULONG),
            ]

        class RAWINPUT(ctypes.Structure):
            class _DATA(ctypes.Union):
                _fields_ = [("keyboard", RAWKEYBOARD)]
            _anonymous_ = ("data",)
            _fields_ = [("header", RAWINPUTHEADER), ("data", _DATA)]

        # Flags teclas
        RI_KEY_BREAK = 0x0001  # key up

        # VK codes útiles
        VK_RETURN = 0x0D
        VK_ESCAPE = 0x1B
        VK_TAB = 0x09
        VK_SPACE = 0x20
        VK_BACK = 0x08

        VK_NUMPAD0 = 0x60
        VK_NUMPAD1 = 0x61
        VK_NUMPAD2 = 0x62
        VK_NUMPAD3 = 0x63
        VK_NUMPAD4 = 0x64
        VK_NUMPAD5 = 0x65
        VK_NUMPAD6 = 0x66
        VK_NUMPAD7 = 0x67
        VK_NUMPAD8 = 0x68
        VK_NUMPAD9 = 0x69
        VK_DECIMAL = 0x6E
        VK_ADD = 0x6B
        VK_SUBTRACT = 0x6D
        VK_MULTIPLY = 0x6A
        VK_DIVIDE = 0x6F

        def vkey_to_keyname(vk: int) -> Optional[str]:
            if VK_NUMPAD0 <= vk <= VK_NUMPAD9:
                return f"KP{vk - VK_NUMPAD0}"
            if vk == VK_DECIMAL:
                return "KPDOT"
            if vk == VK_ADD:
                return "KPPLUS"
            if vk == VK_SUBTRACT:
                return "KPMINUS"
            if vk == VK_MULTIPLY:
                return "KPASTERISK"
            if vk == VK_DIVIDE:
                return "KPSLASH"

            if vk == VK_RETURN:
                return "ENTER"
            if vk == VK_ESCAPE:
                return "ESC"
            if vk == VK_TAB:
                return "TAB"
            if vk == VK_SPACE:
                return "SPACE"
            if vk == VK_BACK:
                return "BACKSPACE"

            if 0x30 <= vk <= 0x39:
                return chr(vk)

            return None

        # Prototipos para evitar conversiones erróneas
        user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, WPARAM, LPARAM]
        user32.DefWindowProcW.restype = LRESULT

        user32.PeekMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND,
                                    wintypes.UINT, wintypes.UINT, wintypes.UINT]
        user32.PeekMessageW.restype = wintypes.BOOL

        user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
        user32.TranslateMessage.restype = wintypes.BOOL

        user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
        user32.DispatchMessageW.restype = LRESULT


        # WndProc type
        WNDPROCTYPE = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT, WPARAM, LPARAM)


        def get_raw_device_name(hdev: int) -> str:
            size = wintypes.UINT(0)
            res = user32.GetRawInputDeviceInfoW(wintypes.HANDLE(hdev), RIDI_DEVICENAME, None, ctypes.byref(size))
            if res == 0xFFFFFFFF:
                return ""
            buf = ctypes.create_unicode_buffer(size.value)
            res = user32.GetRawInputDeviceInfoW(wintypes.HANDLE(hdev), RIDI_DEVICENAME, buf, ctypes.byref(size))
            if res == 0xFFFFFFFF:
                return ""
            return buf.value

        def get_raw_device_desc(hdev: int) -> str:
            name = get_raw_device_name(hdev)
            tail = name[-80:] if len(name) > 80 else name
            return f"hDevice=0x{hdev:016X} name_tail='{tail}'"

        @WNDPROCTYPE
        def WndProc(hwnd, msg, wParam, lParam):
            if msg == WM_INPUT:
                dwSize = wintypes.UINT(0)
                res = user32.GetRawInputData(
                    HRAWINPUT(lParam), RID_INPUT, None, ctypes.byref(dwSize),
                    ctypes.sizeof(RAWINPUTHEADER)
                )
                if res == 0xFFFFFFFF:
                    return 0

                buf = ctypes.create_string_buffer(dwSize.value)
                res = user32.GetRawInputData(
                    HRAWINPUT(lParam), RID_INPUT, buf, ctypes.byref(dwSize),
                    ctypes.sizeof(RAWINPUTHEADER)
                )
                if res == 0xFFFFFFFF:
                    return 0

                ri = ctypes.cast(buf, ctypes.POINTER(RAWINPUT)).contents
                if ri.header.dwType != RIM_TYPEKEYBOARD:
                    return 0

                hdev = int(ri.header.hDevice)
                flags = int(ri.keyboard.Flags)
                vk = int(ri.keyboard.VKey)

                # ignorar key-up
                if (flags & RI_KEY_BREAK) != 0:
                    return 0

                key_name = vkey_to_keyname(vk)
                if key_name is None:
                    if self.debug_mode:
                        dprint(f"[WIN][RAW] hdev=0x{hdev:016X} vk=0x{vk:02X} (IGNORADA)")
                    return 0

                if hdev not in self._devname_cache:
                    devname = get_raw_device_name(hdev)
                    self._devname_cache[hdev] = devname
                    self._devdesc_cache[hdev] = get_raw_device_desc(hdev)

                devname = self._devname_cache[hdev]
                devdesc = self._devdesc_cache[hdev]
                fingerprint = "win|" + devname

                if self.debug_mode:
                    dprint(f"[WIN][RAW] key={key_name:<7} vk=0x{vk:02X} {devdesc}")

                kp = KeyPress(device_id=fingerprint, device_desc=devdesc, key_name=key_name)
                self.on_keypress(kp)
                return 0

            return user32.DefWindowProcW(hwnd, msg, WPARAM(wParam), LPARAM(lParam))

        class WNDCLASS(ctypes.Structure):
            _fields_ = [
                ("style", wintypes.UINT),
                ("lpfnWndProc", WNDPROCTYPE),
                ("cbClsExtra", ctypes.c_int),
                ("cbWndExtra", ctypes.c_int),
                ("hInstance", wintypes.HINSTANCE),
                ("hIcon", wintypes.HICON),
                ("hCursor", wintypes.HCURSOR),
                ("hbrBackground", wintypes.HBRUSH),
                ("lpszMenuName", wintypes.LPCWSTR),
                ("lpszClassName", wintypes.LPCWSTR),
            ]

        hInstance = kernel32.GetModuleHandleW(None)
        className = "RawInputHiddenWindowClass_v1"

        wc = WNDCLASS()
        wc.style = 0
        wc.lpfnWndProc = WndProc
        wc.cbClsExtra = 0
        wc.cbWndExtra = 0
        wc.hInstance = hInstance
        wc.hIcon = None
        wc.hCursor = None
        wc.hbrBackground = None
        wc.lpszMenuName = None
        wc.lpszClassName = className

        atom = user32.RegisterClassW(ctypes.byref(wc))
        if not atom:
            # puede ser que ya exista; no nos importa demasiado
            dprint("[WIN][RAW] RegisterClassW: class ya registrada o error no crítico.")

        hwnd = user32.CreateWindowExW(
            0,
            className,
            "RawInputHiddenWindow",
            0,
            0, 0, 0, 0,
            None, None, hInstance, None
        )
        if not hwnd:
            print("⚠ Windows: no pude crear ventana oculta para Raw Input.")
            return

        rid = RAWINPUTDEVICE()
        rid.usUsagePage = 0x01
        rid.usUsage = 0x06
        rid.dwFlags = RIDEV_INPUTSINK
        rid.hwndTarget = hwnd

        ok = user32.RegisterRawInputDevices(ctypes.byref(rid), 1, ctypes.sizeof(rid))
        if not ok:
            print("⚠ Windows: RegisterRawInputDevices falló.")
            return

        self._flush_stdin_buffer()
        dprint("\n[WIN][RAW] ✅ Listener activo (Raw Input). Presioná teclas...\n")

        msg = wintypes.MSG()
        while not self._stop.is_set():
            # procesar mensajes pendientes
            while user32.PeekMessageW(ctypes.byref(msg), hwnd, 0, 0, PM_REMOVE):
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
            time.sleep(0.01)

        user32.DestroyWindow(hwnd)


# ===========================================================
# Factory listener
# ===========================================================

def build_listener(on_keypress: Callable[[KeyPress], None], debug_mode: bool = False):
    if linux_supported():
        return LinuxKeyboardListener(on_keypress)
    if windows_supported():
        return WindowsRawInputKeyboardListener(on_keypress, debug_mode=debug_mode)
    raise RuntimeError(f"SO no soportado: {platform.system()}")


# ===========================================================
# Modos
# ===========================================================

def mostrar_mapeo(mapping: Dict[str, str]) -> None:
    if not mapping:
        print("No hay mapeos cargados.")
        return
    print("Mapeo actual (devX <= fingerprint):")
    print("-" * 70)
    for k, v in mapping.items():
        tail = k[-100:] if len(k) > 100 else k
        print(f"{v:<10} <= {tail}")
    print("-" * 70)


def modo_debug_input():
    clear_console()
    print_header()
    print("MODO: DEBUG INPUT")
    print(" - Muestra eventos por dispositivo (NO manda POST)")
    print(" - Ctrl+C para volver\n")

    def on_keypress(kp: KeyPress):
        tecla_api = normalize_key_for_api(kp.key_name) or "(IGNORADA)"
        print(f"[DEBUG] key={kp.key_name:<8} -> '{tecla_api:<6}' | dev_id_tail={kp.device_id[-70:]}")

    listener = build_listener(on_keypress, debug_mode=True)
    try:
        listener.run()
    except KeyboardInterrupt:
        pass
    finally:
        try:
            listener.stop()
        except Exception:
            pass


def modo_probar_mapeo(mapping: Dict[str, str]):
    clear_console()
    print_header()
    print("MODO: Probar mapeo")
    print(" - Imprime tecla + dispositivo físico + devXX (si está mapeado)")
    print(" - Ctrl+C para volver\n")

    def on_keypress(kp: KeyPress):
        dev_api = mapping.get(kp.device_id, "(NO MAPEADO)")
        tecla_api = normalize_key_for_api(kp.key_name)
        tecla_show = tecla_api if tecla_api is not None else "(IGNORADA)"
        print(f"[TEST] key={kp.key_name:<8} -> '{tecla_show:<8}' | api={dev_api:<12} | dev_id_tail={kp.device_id[-70:]}")

    listener = build_listener(on_keypress, debug_mode=True)
    try:
        listener.run()
    except KeyboardInterrupt:
        pass
    finally:
        try:
            listener.stop()
        except Exception:
            pass


def modo_mapear_teclados(mapping_path: str, mapping: Dict[str, str]) -> Dict[str, str]:
    clear_console()
    print_header()
    print("MODO: Mapear teclados")
    print(" - Presioná UNA tecla en el numpad que querés mapear.")
    print(" - Luego asignás devXX y se guarda en JSON.")
    print(" - Ctrl+C para volver\n")

    captured = {"kp": None}
    got_one = threading.Event()

    def on_keypress_once(kp: KeyPress):
        if not got_one.is_set():
            captured["kp"] = kp
            got_one.set()

    while True:
        print("\n--- Captura de un dispositivo ---")
        print("Presioná UNA tecla en el numpad a mapear (Ctrl+C para volver)...")
        got_one.clear()
        captured["kp"] = None

        listener = build_listener(on_keypress_once, debug_mode=True)
        t = threading.Thread(target=listener.run, daemon=True)
        t.start()

        try:
            last = time.time()
            while not got_one.is_set():
                if DEBUG and (time.time() - last) >= 1.0:
                    dprint("[MAPEO] ... esperando tecla ...")
                    last = time.time()
                time.sleep(0.02)
        except KeyboardInterrupt:
            try:
                listener.stop()
            except Exception:
                pass
            t.join(timeout=1.0)
            print("\nVolviendo al menú...")
            return mapping
        finally:
            try:
                listener.stop()
            except Exception:
                pass
            t.join(timeout=1.0)

        kp = captured["kp"]
        if kp is None:
            print("⚠ No se capturó nada. Reintentá.")
            continue

        tecla_api = normalize_key_for_api(kp.key_name)
        tecla_show = tecla_api if tecla_api is not None else "(IGNORADA)"

        print("\n✅ Dispositivo detectado:")
        print(f" - ID físico (tail) : {kp.device_id[-120:]}")
        print(f" - Tecla detectada  : {kp.key_name} -> '{tecla_show}'")
        if DEBUG:
            print(f" - ID completo      : {kp.device_id}")

        while True:
            flush_stdin()
            api_name = input("Ingresá nombre API para este dispositivo (ej dev01): ").strip()
            if api_name:
                break
            print("⚠ No puede estar vacío.")

        mapping[kp.device_id] = api_name
        save_mapping(mapping_path, mapping)

        print(f"💾 Guardado: {api_name} <= (fingerprint)")
        flush_stdin()
        otro = input("¿Mapear otro? (s/n): ").strip().lower()
        if otro != "s":
            break

    return mapping


def modo_iniciar(mapping: Dict[str, str]):
    clear_console()
    print_header()
    print("MODO: Iniciar servicio")
    print(" - Escuchando teclas y enviando POST al backend.")
    print(" - Ctrl+C para volver\n")

    def on_keypress(kp: KeyPress):
        dev_api = mapping.get(kp.device_id)
        if not dev_api:
            dprint(f"[SERVICIO] (NO MAPEADO) key={kp.key_name} dev_id_tail={kp.device_id[-70:]}")
            return

        tecla_api = normalize_key_for_api(kp.key_name)
        if tecla_api is None:
            dprint(f"[SERVICIO] (IGNORADA) key={kp.key_name} dev={dev_api}")
            return

        ok, msg = post_key_to_backend(dev_api, tecla_api)
        status = "OK " if ok else "ERR"
        print(f"[{status}] dev={dev_api:<10} key={kp.key_name:<8} -> '{tecla_api}' | {msg}")

    listener = build_listener(on_keypress, debug_mode=False)
    try:
        listener.run()
    except KeyboardInterrupt:
        pass
    finally:
        try:
            listener.stop()
        except Exception:
            pass



def flush_stdin():
    """
    Vacía el buffer de entrada de la consola (Windows).
    Evita que teclas capturadas por Raw Input aparezcan luego en input().
    """
    if os.name != "nt":
        return

    try:
        import msvcrt
        while msvcrt.kbhit():
            msvcrt.getwch()
    except Exception:
        pass



# ===========================================================
# Menú
# ===========================================================

def menu_loop(mapping_path: str):
    mapping = load_mapping(mapping_path)

    if not mapping:
        clear_console()
        print_header()
        print("⚠ No hay archivo de mapeo válido o está vacío.")
        print(f"Ruta esperada: {mapping_path}\n")
        print("Opciones:")
        print("  1) Iniciar mapeo nuevo")
        print("  2) Debug input (ver si llegan teclas)")
        print("  3) Salir")
        flush_stdin()
        op = input("Elegí opción (1/2/3): ").strip()
        if op == "1":
            mapping = modo_mapear_teclados(mapping_path, mapping)
        elif op == "2":
            modo_debug_input()
        else:
            return

    while True:
        clear_console()
        print_header()
        print("Menú:")
        print("  1) Iniciar")
        print("  2) Ver mapeo")
        print("  3) Probar mapeo")
        print("  4) Mapear teclados")
        print("  5) Debug input")
        print("  6) Salir")
        print()

        if DEBUG:
            flush_stdin()
            choice = input("Elegí opción: ").strip()
        else:
            choice = input_with_timeout("Elegí opción (auto inicia en 5s): ", timeout_sec=5)
            if choice is None or choice.strip() == "":
                choice = "1"
            choice = choice.strip()

        if choice == "1":
            mapping = load_mapping(mapping_path)
            if not mapping:
                print("⚠ No hay mapeo. Primero mapeá teclados.")
                time.sleep(1.2)
                continue
            modo_iniciar(mapping)

        elif choice == "2":
            print_header()
            mostrar_mapeo(mapping)
            flush_stdin()
            input("\nEnter para volver...")

        elif choice == "3":
            mapping = load_mapping(mapping_path)
            modo_probar_mapeo(mapping)
            flush_stdin()
            input("\nEnter para volver...")

        elif choice == "4":
            mapping = modo_mapear_teclados(mapping_path, mapping)
            flush_stdin()
            input("\nEnter para volver...")

        elif choice == "5":
            modo_debug_input()
            flush_stdin()
            input("\nEnter para volver...")

        elif choice == "6":
            print("Saliendo...")
            return

        else:
            print("Opción inválida.")
            time.sleep(1.0)


# ===========================================================
# Main
# ===========================================================

def main():
    mapping_path = DEFAULT_MAPPING_FILE
    if len(sys.argv) >= 3 and sys.argv[1] == "--mapping":
        mapping_path = sys.argv[2]

    def _sigterm_handler(signum, frame):
        print("\nSIGTERM recibido. Cerrando...")
        sys.exit(0)

    try:
        signal.signal(signal.SIGTERM, _sigterm_handler)
    except Exception:
        pass

    so = platform.system().lower()
    if so not in ("linux", "windows"):
        print(f"SO no soportado: {platform.system()}")
        sys.exit(1)

    menu_loop(mapping_path)


if __name__ == "__main__":
    main()
