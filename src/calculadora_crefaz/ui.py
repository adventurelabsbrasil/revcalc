"""UI Tkinter — janela única, login, input de cliente, log streaming."""

from __future__ import annotations

import logging
import queue
import threading
import tkinter as tk
import webbrowser
from datetime import datetime
from tkinter import messagebox, scrolledtext, ttk
from typing import Optional

from . import __version__
from .auth import (
    SessaoAutenticada,
    carregar_sessao_existente,
    fluxo_login,
    logout,
)
from .exceptions import CalculadoraError
from .pipeline import ResultadoPipeline, executar

logger = logging.getLogger(__name__)


class CalculadoraApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"Calculadora Crefaz v{__version__}")
        self.root.geometry("700x550")
        self.root.minsize(600, 450)

        self.sessao: Optional[SessaoAutenticada] = None
        self.log_queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self.ultima_pasta_url: Optional[str] = None

        self._build_widgets()
        self._tentar_sessao_existente()
        self._drain_queue_loop()

    # ─── Construção da UI ───────────────────────────────────────────────────

    def _build_widgets(self) -> None:
        style = ttk.Style()
        style.theme_use("aqua" if "aqua" in style.theme_names() else style.theme_use())

        menubar = tk.Menu(self.root)
        menu_ajuda = tk.Menu(menubar, tearoff=0)
        menu_ajuda.add_command(label="Sobre…", command=self._mostrar_sobre)
        menubar.add_cascade(label="Ajuda", menu=menu_ajuda)
        self.root.config(menu=menubar)

        self._footer = ttk.Label(
            self.root,
            text=f"© 2026 Adventure Labs · Rose Portal Advocacia · v{__version__}",
            font=("TkDefaultFont", 9),
            foreground="#555555",
        )
        self._footer.pack(side="bottom", fill="x", padx=12, pady=(0, 8))

        # Frame topo: status do login
        self.frame_login = ttk.Frame(self.root, padding=(12, 10))
        self.frame_login.pack(fill="x")

        self.label_login = ttk.Label(self.frame_login, text="Não autenticado")
        self.label_login.pack(side="left")

        self.btn_login = ttk.Button(self.frame_login, text="Entrar com Google", command=self._on_login)
        self.btn_login.pack(side="right")

        self.btn_logout = ttk.Button(self.frame_login, text="Sair", command=self._on_logout)
        # ainda não exibido — só após login

        # Separador
        ttk.Separator(self.root, orient="horizontal").pack(fill="x", padx=12)

        # Frame input
        self.frame_input = ttk.Frame(self.root, padding=(12, 10))
        self.frame_input.pack(fill="x")

        ttk.Label(self.frame_input, text="Nome do cliente:").pack(anchor="w")
        self.entry_cliente = ttk.Entry(self.frame_input)
        self.entry_cliente.pack(fill="x", pady=(4, 8))
        self.entry_cliente.bind("<Return>", lambda _: self._on_calcular())

        self.btn_calcular = ttk.Button(self.frame_input, text="Calcular", command=self._on_calcular)
        self.btn_calcular.pack(anchor="w")

        # Frame log
        self.frame_log = ttk.Frame(self.root, padding=(12, 4))
        self.frame_log.pack(fill="both", expand=True)

        ttk.Label(self.frame_log, text="Progresso:").pack(anchor="w")
        self.txt_log = scrolledtext.ScrolledText(
            self.frame_log,
            height=14,
            wrap="word",
            state="disabled",
            bg="#1a1a1a",
            fg="#e6e6e6",
            insertbackground="#e6e6e6",
            font=("Menlo", 11),
        )
        self.txt_log.pack(fill="both", expand=True)

        # Frame ações pós-execução
        self.frame_acoes = ttk.Frame(self.root, padding=(12, 8))
        self.frame_acoes.pack(fill="x")

        self.btn_abrir_pasta = ttk.Button(
            self.frame_acoes,
            text="Abrir pasta no Drive",
            command=self._abrir_pasta,
            state="disabled",
        )
        self.btn_abrir_pasta.pack(anchor="w")

        # Estado inicial: input desabilitado até login
        self._set_logado(False)

    def _mostrar_sobre(self) -> None:
        messagebox.showinfo(
            "Sobre a Calculadora Crefaz",
            f"Calculadora de Ação Crefaz\n"
            f"Versão {__version__}\n\n"
            "Desenvolvida pela Adventure Labs\n"
            "para a Rose Portal Advocacia.\n\n"
            "© 2026 Adventure Labs\n"
            "adventurelabs.com.br",
        )

    def _set_logado(self, logado: bool) -> None:
        if logado and self.sessao:
            self.label_login.config(text=f"Logado: {self.sessao.email}")
            self.btn_login.pack_forget()
            self.btn_logout.pack(side="right")
            self.entry_cliente.config(state="normal")
            self.btn_calcular.config(state="normal")
        else:
            self.label_login.config(text="Não autenticado")
            self.btn_logout.pack_forget()
            self.btn_login.pack(side="right")
            self.entry_cliente.config(state="disabled")
            self.btn_calcular.config(state="disabled")

    # ─── Auth ───────────────────────────────────────────────────────────────

    def _tentar_sessao_existente(self) -> None:
        try:
            sessao = carregar_sessao_existente()
        except Exception as e:
            logger.warning("Erro ao carregar sessão existente: %s", e)
            return
        if sessao:
            self.sessao = sessao
            self._set_logado(True)

    def _on_login(self) -> None:
        self.btn_login.config(state="disabled")

        def trabalho():
            try:
                sessao = fluxo_login()
                self.sessao = sessao
                self.root.after(0, lambda: self._set_logado(True))
                self._log("INFO", f"Login OK: {sessao.email}")
            except CalculadoraError as e:
                msg = str(e) or e.__class__.__name__
                self.root.after(0, lambda m=msg: messagebox.showerror("Falha no login", m))
            except Exception as e:
                logger.exception("Erro inesperado no login")
                msg = str(e) or repr(e)
                self.root.after(0, lambda m=msg: messagebox.showerror("Erro", m))
            finally:
                self.root.after(0, lambda: self.btn_login.config(state="normal"))

        threading.Thread(target=trabalho, daemon=True).start()

    def _on_logout(self) -> None:
        if not messagebox.askyesno("Sair", "Tem certeza? Você precisará logar de novo."):
            return
        try:
            logout(self.sessao.email if self.sessao else None)
        except Exception:
            logger.exception("Falha ao deslogar")
        self.sessao = None
        self._set_logado(False)
        self._limpar_log()

    # ─── Cálculo ────────────────────────────────────────────────────────────

    def _on_calcular(self) -> None:
        nome = self.entry_cliente.get().strip()
        if not nome:
            messagebox.showwarning("Atenção", "Digite o nome do cliente.")
            return
        if not self.sessao:
            messagebox.showwarning("Atenção", "Faça login antes de calcular.")
            return

        self._limpar_log()
        self.btn_calcular.config(state="disabled")
        self.btn_abrir_pasta.config(state="disabled")
        self.ultima_pasta_url = None

        def trabalho():
            try:
                resultado: ResultadoPipeline = executar(
                    nome,
                    self.sessao,
                    status=lambda msg: self._log("INFO", msg),
                )
                self.ultima_pasta_url = resultado.pasta_drive_url
                if resultado.pulados and not resultado.arquivos_gerados:
                    self._log(
                        "OK",
                        "✓ Nada novo — todos os contratos já tinham cálculo (pulados).\n"
                        "Para refazer, apague o Calculo.xlsx da pasta no Drive.\n"
                        f"Pasta: {resultado.pasta_drive_url}",
                    )
                else:
                    extra = (
                        f"\n{len(resultado.pulados)} já calculado(s) pulado(s)."
                        if resultado.pulados
                        else ""
                    )
                    self._log(
                        "OK",
                        f"✓ Pronto.\nPasta: {resultado.pasta_drive_url}{extra}",
                    )
                self.root.after(
                    0, lambda: self.btn_abrir_pasta.config(state="normal")
                )
            except CalculadoraError as e:
                msg = str(e) or e.__class__.__name__
                self._log("ERRO", msg)
                self.root.after(0, lambda m=msg: messagebox.showerror("Erro", m))
            except Exception as e:
                logger.exception("Erro inesperado no pipeline")
                msg = str(e) or repr(e)
                self._log("ERRO", f"Erro inesperado: {msg}")
                self.root.after(0, lambda m=msg: messagebox.showerror("Erro", m))
            finally:
                self.root.after(0, lambda: self.btn_calcular.config(state="normal"))

        threading.Thread(target=trabalho, daemon=True).start()

    def _abrir_pasta(self) -> None:
        if self.ultima_pasta_url:
            webbrowser.open(self.ultima_pasta_url)

    # ─── Log streaming ──────────────────────────────────────────────────────

    def _log(self, nivel: str, mensagem: str) -> None:
        self.log_queue.put((nivel, mensagem))

    def _drain_queue_loop(self) -> None:
        try:
            while True:
                nivel, mensagem = self.log_queue.get_nowait()
                ts = datetime.now().strftime("%H:%M:%S")
                self.txt_log.config(state="normal")
                tag = nivel.lower()
                self.txt_log.insert("end", f"[{ts}] {mensagem}\n", tag)
                self.txt_log.tag_config("erro", foreground="#ff6b6b")
                self.txt_log.tag_config("ok", foreground="#51cf66")
                self.txt_log.tag_config("info", foreground="#e6e6e6")
                self.txt_log.see("end")
                self.txt_log.config(state="disabled")
        except queue.Empty:
            pass
        self.root.after(100, self._drain_queue_loop)

    def _limpar_log(self) -> None:
        self.txt_log.config(state="normal")
        self.txt_log.delete("1.0", "end")
        self.txt_log.config(state="disabled")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    root = tk.Tk()
    CalculadoraApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
