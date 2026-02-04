import tkinter as tk
from tkinter import ttk

# requests puede no estar instalado; lo manejamos con error visible
try:
    import requests
except Exception as e:
    requests = None
    _requests_import_error = e

import json
import time
from datetime import datetime
from urllib.parse import urlparse
import traceback

# =========================
# Configuración
# =========================
API_BASE_URL = "http://127.0.0.1:8000"
API_PATH = "/entradas/tecla"
TIMEOUT_SECONDS = 2.5

NUM_TECLADOS = 12
COLUMNAS = 4  # 12 -> 4 columnas x 3 filas


def now_str() -> str:
    return datetime.now().strftime("%H:%M:%S")


def base_from_post_url(post_url: str) -> str:
    p = urlparse(post_url)
    if not p.scheme or not p.netloc:
        return API_BASE_URL
    return f"{p.scheme}://{p.netloc}"


class ScrollableFrame(ttk.Frame):
    """
    Frame scrollable vertical (Canvas + Scrollbar).
    Soporta rueda del mouse cuando el cursor está dentro.
    """
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vsb.set)

        self.vsb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.inner = ttk.Frame(self.canvas)
        self.window_id = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")

        self.inner.bind("<Configure>", self._on_inner_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        # Mousewheel: lo dejamos, pero si algo falla no debe romper el arranque
        try:
            self._bind_mousewheel(self.canvas)
        except Exception:
            # No queremos que el scroll con rueda impida abrir la app
            traceback.print_exc()

    def _on_inner_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.window_id, width=event.width)

    def _bind_mousewheel(self, widget):
        widget.bind("<Enter>", lambda e: self._bind_global_mousewheel())
        widget.bind("<Leave>", lambda e: self._unbind_global_mousewheel())

    def _bind_global_mousewheel(self):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)       # Windows/macOS
        self.canvas.bind_all("<Button-4>", self._on_mousewheel_linux)   # Linux up
        self.canvas.bind_all("<Button-5>", self._on_mousewheel_linux)   # Linux down

    def _unbind_global_mousewheel(self):
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")

    def _on_mousewheel(self, event):
        delta = int(-1 * (event.delta / 120))
        self.canvas.yview_scroll(delta, "units")

    def _on_mousewheel_linux(self, event):
        if event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")


class App(tk.Tk):
    def __init__(self):
        super().__init__()

        # Si requests no importó, mostrar el error (consola + popup) y salir.
        if requests is None:
            msg = f"No se pudo importar 'requests': {repr(_requests_import_error)}\n\n" \
                  f"Instalá con: python -m pip install requests"
            print(msg)
            try:
                import tkinter.messagebox as mb
                mb.showerror("Falta dependency: requests", msg)
            except Exception:
                pass
            # cerrar root
            self.destroy()
            return

        self.title("Frontend de prueba - 12 teclados")
        self.geometry("980x640")
        self.minsize(900, 560)

        self.api_url_var = tk.StringVar(value=f"{API_BASE_URL}{API_PATH}")

        self._build_ui()

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # =========================
        # Top bar
        # =========================
        top = ttk.Frame(self, padding=10)
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(1, weight=1)

        ttk.Label(top, text="URL API (POST):").grid(row=0, column=0, sticky="w")
        ttk.Entry(top, textvariable=self.api_url_var).grid(row=0, column=1, sticky="ew", padx=8)

        ttk.Button(top, text="Probar conexión (/)", command=self.probar_root).grid(row=0, column=2, padx=4)
        ttk.Button(top, text="Limpiar log", command=self.limpiar_log).grid(row=0, column=3, padx=4)

        # =========================
        # PanedWindow: teclados + log
        # =========================
        paned = ttk.PanedWindow(self, orient="vertical")
        paned.grid(row=1, column=0, sticky="nsew")

        # ---------
        # Teclados (scrollable)
        # ---------
        teclados_container = ttk.Frame(paned, padding=10)
        teclados_container.columnconfigure(0, weight=1)
        teclados_container.rowconfigure(0, weight=1)

        self.teclados_scroll = ScrollableFrame(teclados_container)
        self.teclados_scroll.grid(row=0, column=0, sticky="nsew")

        self.teclados_frame = self.teclados_scroll.inner

        for c in range(COLUMNAS):
            self.teclados_frame.columnconfigure(c, weight=1)

        self.dispositivo_vars = []
        for i in range(NUM_TECLADOS):
            if i<9:
                disp_var = tk.StringVar(value=f"dev0{i+1}")
            else:
                disp_var = tk.StringVar(value=f"dev{i+1}")
            self.dispositivo_vars.append(disp_var)

            teclado = self._crear_teclado(self.teclados_frame, idx=i, dispositivo_var=disp_var)
            fila = i // COLUMNAS
            col = i % COLUMNAS
            teclado.grid(row=fila, column=col, padx=8, pady=8, sticky="n")

        # ---------
        # Log
        # ---------
        log_container = ttk.Frame(paned, padding=10)
        log_container.columnconfigure(0, weight=1)
        log_container.rowconfigure(1, weight=1)

        ttk.Label(log_container, text="Log / Respuestas:").grid(row=0, column=0, sticky="w")

        text_container = ttk.Frame(log_container)
        text_container.grid(row=1, column=0, sticky="nsew")
        text_container.columnconfigure(0, weight=1)
        text_container.rowconfigure(0, weight=1)

        self.log_text = tk.Text(text_container, height=10, wrap="word")
        self.log_text.grid(row=0, column=0, sticky="nsew")

        scroll = ttk.Scrollbar(text_container, orient="vertical", command=self.log_text.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=scroll.set)

        paned.add(teclados_container, weight=3)
        paned.add(log_container, weight=1)

        self._log(f"[{now_str()}] Listo. POST -> {self.api_url_var.get()}")

    def _crear_teclado(self, parent, idx: int, dispositivo_var: tk.StringVar):
        frame = ttk.Frame(parent, padding=8, relief="ridge")

        ttk.Label(frame, text=f"Teclado {idx+1}", font=("Segoe UI", 10, "bold")).pack(anchor="w")

        row = ttk.Frame(frame)
        row.pack(fill="x", pady=(6, 8))

        ttk.Label(row, text="Dispositivo:").pack(side="left")
        ttk.Entry(row, textvariable=dispositivo_var, width=14).pack(side="left", padx=6)

        grid = ttk.Frame(frame)
        grid.pack()

        # Numpad físico (sin 0)
        layout = [
            ["7", "8", "9"],
            ["4", "5", "6"],
            ["1", "2", "3"],
        ]

        for r in range(3):
            for c in range(3):
                t = layout[r][c]
                b = ttk.Button(
                    grid,
                    text=t,
                    width=6,
                    command=lambda tecla=t, dv=dispositivo_var: self.enviar_pulsacion(dv.get(), tecla),
                )
                b.grid(row=r, column=c, padx=3, pady=3)

        return frame

    def _log(self, msg: str):
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")

    def limpiar_log(self):
        self.log_text.delete("1.0", "end")

    def probar_root(self):
        try:
            post_url = self.api_url_var.get().strip()
            base = base_from_post_url(post_url) if post_url else API_BASE_URL
            url = f"{base}/"

            t0 = time.perf_counter()
            r = requests.get(url, timeout=TIMEOUT_SECONDS)
            ms = (time.perf_counter() - t0) * 1000

            tag = "✅" if 200 <= r.status_code < 300 else "❌"
            self._log(f"[{now_str()}] {tag} {ms:7.1f} ms | GET {url} -> {r.status_code} {r.text}")

        except requests.exceptions.Timeout:
            self._log(f"[{now_str()}] ⏱️ TIMEOUT GET / ({TIMEOUT_SECONDS}s)")
        except Exception as e:
            self._log(f"[{now_str()}] ERROR probando root: {repr(e)}")

    def enviar_pulsacion(self, dispositivo: str, tecla: str):
        dispositivo = (dispositivo or "").strip()
        tecla = (tecla or "").strip()

        if not dispositivo:
            self._log(f"[{now_str()}] ⚠️ No se envió: dispositivo vacío.")
            return

        url = self.api_url_var.get().strip()
        if not url:
            self._log(f"[{now_str()}] ⚠️ No se envió: URL API vacía.")
            return

        payload = {"dispositivo": dispositivo, "tecla": tecla}

        try:
            t0 = time.perf_counter()
            r = requests.post(url, json=payload, timeout=TIMEOUT_SECONDS)
            ms = (time.perf_counter() - t0) * 1000

            try:
                data = r.json()
                body = json.dumps(data, ensure_ascii=False)
            except Exception:
                body = r.text

            tag = "✅" if 200 <= r.status_code < 300 else "❌"
            self._log(f"[{now_str()}] {tag} {ms:7.1f} ms | POST {payload} -> {r.status_code} {body}")

        except requests.exceptions.Timeout:
            self._log(f"[{now_str()}] ⏱️ TIMEOUT POST {payload} ({TIMEOUT_SECONDS}s)")
        except Exception as e:
            self._log(f"[{now_str()}] ERROR POST {payload}: {repr(e)}")


if __name__ == "__main__":
    print("Arrancando frontend_teclados.py...")

    try:
        app = App()

        # Si la app se autodestruyó por falta de requests, evitar mainloop()
        if isinstance(app, App) and app.winfo_exists():
            print("App creada. Entrando a mainloop()...")
            app.mainloop()
            print("mainloop terminó.")
        else:
            print("La ventana no existe (probablemente falta requests u otro error temprano).")

    except Exception:
        print("ERROR al ejecutar la app:")
        traceback.print_exc()
        try:
            import tkinter.messagebox as mb
            mb.showerror("Error en frontend_teclados.py", "Mirá la consola para el traceback.")
        except Exception:
            pass
        input("Enter para cerrar...")
