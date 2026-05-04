"""
Desktop UI for the OpenLibrary Automation Suite.

Run from the openlibrary_automation/ directory:
    python ui/app.py

No extra dependencies — uses only stdlib tkinter.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from pathlib import Path
from tkinter import messagebox, scrolledtext, ttk
import tkinter as tk

# ── Paths ──────────────────────────────────────────────────────────────────────
_HERE = Path(__file__).resolve().parent          # ui/
_ROOT = _HERE.parent                             # openlibrary_automation/
_ENV  = _ROOT / ".env"

# Colours
_GREEN  = "#2ecc71"
_RED    = "#e74c3c"
_ORANGE = "#f39c12"
_BG     = "#f5f5f5"
_DARK   = "#2c3e50"
_WHITE  = "#ffffff"


# ══════════════════════════════════════════════════════════════════════════════
class AutomationApp:
    """Main application window."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("OpenLibrary Automation Suite")
        self.root.geometry("920x680")
        self.root.resizable(True, True)
        self.root.configure(bg=_BG)

        self._proc: subprocess.Popen | None = None
        self._running = False

        self._build_header()
        self._build_notebook()
        self._build_statusbar()
        self._refresh_env_status()

    # ── Header ─────────────────────────────────────────────────────────────────

    def _build_header(self) -> None:
        hdr = tk.Frame(self.root, bg=_DARK, pady=10)
        hdr.pack(fill="x")

        tk.Label(
            hdr,
            text="OpenLibrary Automation Suite",
            font=("Segoe UI", 16, "bold"),
            fg=_WHITE, bg=_DARK,
        ).pack(side="left", padx=16)

        # .env status pills
        self._env_frame = tk.Frame(hdr, bg=_DARK)
        self._env_frame.pack(side="right", padx=16)

        # Settings button
        tk.Button(
            self._env_frame, text="⚙ Credentials",
            font=("Segoe UI", 9, "bold"),
            bg=_ORANGE, fg=_WHITE, relief="flat",
            padx=8, pady=2,
            command=self._open_credentials_dialog,
        ).pack(side="left", padx=(0, 10))

        self._env_labels: dict[str, tk.Label] = {}
        for key in ("OPENLIBRARY_USER", "OPENLIBRARY_PASS", "OPENLIBRARY_USERNAME"):
            lbl = tk.Label(
                self._env_frame,
                text=f" {key.replace('OPENLIBRARY_', '')} ",
                font=("Segoe UI", 9, "bold"),
                fg=_WHITE, bg=_RED,
                relief="flat", padx=6, pady=2,
                cursor="hand2",
            )
            lbl.pack(side="left", padx=3)
            lbl.bind("<Button-1>", lambda e: self._open_credentials_dialog())
            self._env_labels[key] = lbl

    def _open_credentials_dialog(self) -> None:
        """Open a dialog to view/edit .env credentials."""
        # Read current values
        current: dict[str, str] = {}
        if _ENV.exists():
            for line in _ENV.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    current[k.strip()] = v.strip()

        dlg = tk.Toplevel(self.root)
        dlg.title("Credentials (.env)")
        dlg.geometry("420x240")
        dlg.resizable(False, False)
        dlg.grab_set()  # modal
        dlg.configure(bg=_BG)

        fields = [
            ("Email (OPENLIBRARY_USER):",     "OPENLIBRARY_USER",     False),
            ("Password (OPENLIBRARY_PASS):",   "OPENLIBRARY_PASS",     True),
            ("Username (OPENLIBRARY_USERNAME):","OPENLIBRARY_USERNAME", False),
        ]
        entries: dict[str, tk.Entry] = {}

        for i, (label, key, secret) in enumerate(fields):
            tk.Label(dlg, text=label, font=("Segoe UI", 10), bg=_BG, anchor="w").grid(
                row=i, column=0, sticky="w", padx=16, pady=(12 if i == 0 else 4, 0)
            )
            show = "*" if secret else ""
            e = tk.Entry(dlg, font=("Segoe UI", 10), width=32, show=show)
            e.insert(0, current.get(key, ""))
            e.grid(row=i, column=1, padx=(0, 16), pady=(12 if i == 0 else 4, 0))
            entries[key] = e

        def save() -> None:
            # Build new .env content preserving comments
            lines: list[str] = []
            if _ENV.exists():
                for line in _ENV.read_text(encoding="utf-8").splitlines():
                    stripped = line.strip()
                    if stripped.startswith("#") or not stripped:
                        lines.append(line)
                        continue
                    k = stripped.split("=", 1)[0].strip()
                    if k in entries:
                        lines.append(f"{k}={entries[k].get().strip()}")
                    else:
                        lines.append(line)
            else:
                # Create fresh .env
                for key, entry in entries.items():
                    lines.append(f"{key}={entry.get().strip()}")
                lines.append("ENV=dev")

            # Add any missing keys
            existing_keys = {l.split("=")[0] for l in lines if "=" in l and not l.startswith("#")}
            for key, entry in entries.items():
                if key not in existing_keys:
                    lines.append(f"{key}={entry.get().strip()}")

            _ENV.write_text("\n".join(lines) + "\n", encoding="utf-8")
            self._refresh_env_status()
            dlg.destroy()
            messagebox.showinfo("Saved", ".env updated successfully.\nRestart the Full Flow to apply changes.")

        btn_frame = tk.Frame(dlg, bg=_BG)
        btn_frame.grid(row=len(fields), column=0, columnspan=2, pady=16)

        tk.Button(
            btn_frame, text="Save",
            font=("Segoe UI", 10, "bold"),
            bg=_GREEN, fg=_WHITE, relief="flat",
            padx=16, pady=6,
            command=save,
        ).pack(side="left", padx=8)

        tk.Button(
            btn_frame, text="Cancel",
            font=("Segoe UI", 10),
            bg="#95a5a6", fg=_WHITE, relief="flat",
            padx=16, pady=6,
            command=dlg.destroy,
        ).pack(side="left")

    def _refresh_env_status(self) -> None:
        """Re-read .env and update indicator pills."""
        env_values: dict[str, str] = {}
        if _ENV.exists():
            for line in _ENV.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    env_values[k.strip()] = v.strip()

        for key, lbl in self._env_labels.items():
            present = bool(env_values.get(key, ""))
            lbl.configure(bg=_GREEN if present else _RED)

    # ── Notebook (tabs) ────────────────────────────────────────────────────────

    def _build_notebook(self) -> None:
        style = ttk.Style()
        style.configure("TNotebook.Tab", font=("Segoe UI", 10), padding=[12, 4])

        nb = ttk.Notebook(self.root)
        nb.pack(fill="both", expand=True, padx=12, pady=(8, 0))

        self._build_tests_tab(nb)
        self._build_fullflow_tab(nb)
        self._build_reports_tab(nb)

    # ── Tab 1: Run Tests ───────────────────────────────────────────────────────

    def _build_tests_tab(self, nb: ttk.Notebook) -> None:
        frame = tk.Frame(nb, bg=_BG)
        nb.add(frame, text="  Run Tests  ")

        # Options row
        opts = tk.Frame(frame, bg=_BG, pady=8)
        opts.pack(fill="x", padx=16)

        tk.Label(opts, text="Test scope:", font=("Segoe UI", 10), bg=_BG).pack(side="left")

        self._test_scope = tk.StringVar(value="unit")
        scopes = [
            ("Unit only  (fast, ~5s)", "unit"),
            ("E2E only   (browser, ~5min)", "e2e"),
            ("All tests", "all"),
        ]
        for text, val in scopes:
            ttk.Radiobutton(
                opts, text=text, variable=self._test_scope, value=val,
            ).pack(side="left", padx=10)

        # Buttons row
        btns = tk.Frame(frame, bg=_BG)
        btns.pack(fill="x", padx=16, pady=4)

        self._run_btn = tk.Button(
            btns, text="▶  Run Tests",
            font=("Segoe UI", 10, "bold"),
            bg=_GREEN, fg=_WHITE, relief="flat",
            padx=14, pady=6,
            command=self._run_tests,
        )
        self._run_btn.pack(side="left", padx=(0, 8))

        self._stop_btn = tk.Button(
            btns, text="■  Stop",
            font=("Segoe UI", 10),
            bg=_RED, fg=_WHITE, relief="flat",
            padx=14, pady=6,
            state="disabled",
            command=self._stop_process,
        )
        self._stop_btn.pack(side="left")

        self._clear_btn = tk.Button(
            btns, text="Clear",
            font=("Segoe UI", 10),
            bg="#95a5a6", fg=_WHITE, relief="flat",
            padx=14, pady=6,
            command=lambda: self._output.delete("1.0", "end"),
        )
        self._clear_btn.pack(side="left", padx=8)

        # Output area
        self._output = scrolledtext.ScrolledText(
            frame,
            font=("Consolas", 9),
            bg="#1e1e1e", fg="#d4d4d4",
            insertbackground=_WHITE,
            relief="flat", padx=8, pady=8,
        )
        self._output.pack(fill="both", expand=True, padx=16, pady=(4, 12))

        # colour tags
        self._output.tag_configure("pass",  foreground="#2ecc71")
        self._output.tag_configure("fail",  foreground="#e74c3c")
        self._output.tag_configure("warn",  foreground="#f39c12")
        self._output.tag_configure("info",  foreground="#3498db")
        self._output.tag_configure("plain", foreground="#d4d4d4")

    def _run_tests(self) -> None:
        if self._running:
            return
        scope = self._test_scope.get()
        marker_map = {
            "unit": ["-m", "not e2e"],
            "e2e":  ["-m", "e2e"],
            "all":  [],
        }
        extra = marker_map[scope]
        cmd = [sys.executable, "-m", "pytest"] + extra + ["-v", "--tb=short"]
        self._launch_subprocess(cmd, cwd=str(_ROOT))

    # ── Tab 2: Full Flow ───────────────────────────────────────────────────────

    def _build_fullflow_tab(self, nb: ttk.Notebook) -> None:
        frame = tk.Frame(nb, bg=_BG)
        nb.add(frame, text="  Full Flow  ")

        # Inputs
        inp = tk.Frame(frame, bg=_BG, pady=12)
        inp.pack(fill="x", padx=16)

        def _label(text: str, col: int) -> None:
            tk.Label(inp, text=text, font=("Segoe UI", 10), bg=_BG).grid(
                row=0, column=col, sticky="w", padx=(0, 4)
            )

        _label("Query:", 0)
        self._ff_query = tk.Entry(inp, font=("Segoe UI", 10), width=18)
        self._ff_query.insert(0, "Dune")
        self._ff_query.grid(row=1, column=0, padx=(0, 12))

        _label("Max year:", 2)
        self._ff_year = tk.Entry(inp, font=("Segoe UI", 10), width=8)
        self._ff_year.insert(0, "1980")
        self._ff_year.grid(row=1, column=2, padx=(0, 12))

        _label("Limit:", 4)
        self._ff_limit = tk.Entry(inp, font=("Segoe UI", 10), width=6)
        self._ff_limit.insert(0, "3")
        self._ff_limit.grid(row=1, column=4, padx=(0, 12))

        self._ff_run_btn = tk.Button(
            inp, text="▶  Run Full Flow",
            font=("Segoe UI", 10, "bold"),
            bg=_DARK, fg=_WHITE, relief="flat",
            padx=14, pady=6,
            command=self._run_full_flow,
        )
        self._ff_run_btn.grid(row=1, column=6, padx=(8, 0))

        self._ff_stop_btn = tk.Button(
            inp, text="■  Stop",
            font=("Segoe UI", 10),
            bg=_RED, fg=_WHITE, relief="flat",
            padx=14, pady=6,
            state="disabled",
            command=self._stop_process,
        )
        self._ff_stop_btn.grid(row=1, column=7, padx=(6, 0))

        # Results summary
        res_frame = tk.LabelFrame(
            frame, text="  Last result  ",
            font=("Segoe UI", 10), bg=_BG, pady=8,
        )
        res_frame.pack(fill="x", padx=16, pady=(0, 8))

        self._ff_labels: dict[str, tk.Label] = {}
        keys = [
            ("urls_found",           "Books found"),
            ("urls_added",           "Books added"),
            ("urls_failed",          "Failed"),
            ("reading_list_count",   "List count"),
            ("verification_passed",  "Verified"),
        ]
        for i, (key, display) in enumerate(keys):
            tk.Label(res_frame, text=display + ":", font=("Segoe UI", 10), bg=_BG).grid(
                row=0, column=i * 2, sticky="e", padx=(12, 2)
            )
            lbl = tk.Label(res_frame, text="—", font=("Segoe UI", 10, "bold"), bg=_BG, width=6)
            lbl.grid(row=0, column=i * 2 + 1, sticky="w")
            self._ff_labels[key] = lbl

        # Output
        self._ff_output = scrolledtext.ScrolledText(
            frame,
            font=("Consolas", 9),
            bg="#1e1e1e", fg="#d4d4d4",
            relief="flat", padx=8, pady=8,
        )
        self._ff_output.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        self._ff_output.tag_configure("pass", foreground="#2ecc71")
        self._ff_output.tag_configure("fail", foreground="#e74c3c")
        self._ff_output.tag_configure("plain", foreground="#d4d4d4")

    def _run_full_flow(self) -> None:
        if self._running:
            messagebox.showwarning("Busy", "Another process is already running.")
            return

        query = self._ff_query.get().strip()
        if not query:
            messagebox.showerror("Validation", "Query cannot be empty.")
            return

        try:
            year = int(self._ff_year.get().strip())
            if not (1800 <= year <= 2030):
                raise ValueError
        except ValueError:
            messagebox.showerror("Validation", "Max year must be an integer between 1800 and 2030.")
            return

        try:
            limit = int(self._ff_limit.get().strip())
            if not (1 <= limit <= 20):
                raise ValueError
        except ValueError:
            messagebox.showerror("Validation", "Limit must be an integer between 1 and 20.")
            return

        # Run LibraryTestRunner directly — NOT via pytest
        cmd = [
            sys.executable,
            str(_HERE / "run_flow.py"),
            query, str(year), str(limit),
        ]
        self._launch_subprocess(
            cmd, cwd=str(_ROOT), output_widget=self._ff_output,
            extra_run_btn=self._ff_run_btn, extra_stop_btn=self._ff_stop_btn,
        )

    # ── Tab 3: Reports ─────────────────────────────────────────────────────────

    def _build_reports_tab(self, nb: ttk.Notebook) -> None:
        frame = tk.Frame(nb, bg=_BG)
        nb.add(frame, text="  Reports  ")

        # Performance report table
        perf_lf = tk.LabelFrame(
            frame, text="  Performance Report  ",
            font=("Segoe UI", 10), bg=_BG,
        )
        perf_lf.pack(fill="x", padx=16, pady=(12, 6))

        cols = ("page", "first_paint_ms", "dom_content_loaded_ms", "load_time_ms")
        self._perf_tree = ttk.Treeview(perf_lf, columns=cols, show="headings", height=6)
        for col in cols:
            self._perf_tree.heading(col, text=col.replace("_", " ").title())
            self._perf_tree.column(col, width=180, anchor="center")
        self._perf_tree.pack(fill="x", padx=8, pady=6)

        tk.Button(
            perf_lf, text="Refresh",
            font=("Segoe UI", 9),
            bg="#3498db", fg=_WHITE, relief="flat",
            padx=10, pady=4,
            command=self._load_perf_report,
        ).pack(anchor="e", padx=8, pady=(0, 6))

        # Screenshots list
        ss_lf = tk.LabelFrame(
            frame, text="  Screenshots  ",
            font=("Segoe UI", 10), bg=_BG,
        )
        ss_lf.pack(fill="both", expand=True, padx=16, pady=6)

        self._ss_list = tk.Listbox(ss_lf, font=("Segoe UI", 9), height=8, relief="flat")
        self._ss_list.pack(fill="both", expand=True, padx=8, pady=6)
        self._ss_list.bind("<Double-Button-1>", self._open_screenshot)

        tk.Button(
            ss_lf, text="Refresh list",
            font=("Segoe UI", 9),
            bg="#3498db", fg=_WHITE, relief="flat",
            padx=10, pady=4,
            command=self._load_screenshots,
        ).pack(anchor="e", padx=8, pady=(0, 6))

        self._load_perf_report()
        self._load_screenshots()

    def _load_perf_report(self) -> None:
        for row in self._perf_tree.get_children():
            self._perf_tree.delete(row)

        report_path = _ROOT / "reports" / "performance_report.json"
        if not report_path.exists():
            self._perf_tree.insert("", "end", values=("No report found", "", "", ""))
            return

        try:
            data = json.loads(report_path.read_text(encoding="utf-8"))
            for m in data.get("measurements", []):
                self._perf_tree.insert("", "end", values=(
                    m.get("page_name", ""),
                    m.get("first_paint_ms", ""),
                    m.get("dom_content_loaded_ms", ""),
                    m.get("load_time_ms", ""),
                ))
        except Exception as exc:
            self._perf_tree.insert("", "end", values=(f"Error: {exc}", "", "", ""))

    def _load_screenshots(self) -> None:
        self._ss_list.delete(0, "end")
        ss_dir = _ROOT / "screenshots"
        if not ss_dir.exists():
            self._ss_list.insert("end", "(screenshots/ folder not found)")
            return
        pngs = sorted(ss_dir.glob("*.png"))
        if not pngs:
            self._ss_list.insert("end", "(no screenshots yet)")
            return
        for p in pngs:
            self._ss_list.insert("end", p.name)

    def _open_screenshot(self, _event: object) -> None:
        sel = self._ss_list.curselection()
        if not sel:
            return
        name = self._ss_list.get(sel[0])
        path = _ROOT / "screenshots" / name
        if path.exists():
            os.startfile(str(path))

    # ── Status bar ─────────────────────────────────────────────────────────────

    def _build_statusbar(self) -> None:
        bar = tk.Frame(self.root, bg="#bdc3c7", height=26)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)

        self._status_var = tk.StringVar(value="Ready")
        tk.Label(
            bar, textvariable=self._status_var,
            font=("Segoe UI", 9), bg="#bdc3c7", anchor="w",
        ).pack(side="left", padx=12)

        self._progress = ttk.Progressbar(bar, mode="indeterminate", length=120)
        self._progress.pack(side="right", padx=12, pady=4)

    def _set_status(self, msg: str, busy: bool = False) -> None:
        self._status_var.set(msg)
        if busy:
            self._progress.start(12)
        else:
            self._progress.stop()

    # ── Subprocess management ─────────────────────────────────────────────────

    def _launch_subprocess(
        self,
        cmd: list[str],
        cwd: str,
        env: dict | None = None,
        output_widget: scrolledtext.ScrolledText | None = None,
        extra_run_btn: tk.Button | None = None,
        extra_stop_btn: tk.Button | None = None,
    ) -> None:
        if output_widget is None:
            output_widget = self._output

        self._running = True
        self._run_btn.configure(state="disabled")
        self._stop_btn.configure(state="normal")
        if extra_run_btn:
            extra_run_btn.configure(state="disabled")
        if extra_stop_btn:
            extra_stop_btn.configure(state="normal")
        self._set_status("Running…", busy=True)
        output_widget.delete("1.0", "end")

        def worker() -> None:
            import re
            status = "Done"
            try:
                self._proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    cwd=cwd,
                    env=env,
                )
                passed = failed = 0
                result_json: dict | None = None

                for line in self._proc.stdout:  # type: ignore[union-attr]
                    # Parse RESULT: line from run_flow.py
                    if line.startswith("RESULT:"):
                        try:
                            result_json = json.loads(line[7:])
                        except Exception:
                            pass
                    self.root.after(0, self._append_line, output_widget, line)
                    low = line.lower()
                    m = re.search(r"(\d+) passed", low)
                    if m:
                        passed = int(m.group(1))
                    m = re.search(r"(\d+) failed", low)
                    if m:
                        failed = int(m.group(1))

                self._proc.wait()

                if result_json is not None:
                    self.root.after(0, self._update_ff_summary, result_json)
                    v = result_json.get("verification_passed", False)
                    status = "Flow done: verified" if v else "Flow done: NOT verified"
                elif passed or failed:
                    status = f"Done: {passed} passed, {failed} failed"

            except Exception as exc:
                status = f"Error: {exc}"
            finally:
                self._running = False
                self._proc = None
                self.root.after(0, self._run_btn.configure, {"state": "normal"})
                self.root.after(0, self._stop_btn.configure, {"state": "disabled"})
                if extra_run_btn:
                    self.root.after(0, extra_run_btn.configure, {"state": "normal"})
                if extra_stop_btn:
                    self.root.after(0, extra_stop_btn.configure, {"state": "disabled"})
                self.root.after(0, self._set_status, status, False)

        threading.Thread(target=worker, daemon=True).start()

    def _append_line(self, widget: scrolledtext.ScrolledText, line: str) -> None:
        low = line.lower()
        if "passed" in low and ("failed" not in low):
            tag = "pass"
        elif "failed" in low or "error" in low:
            tag = "fail"
        elif "warning" in low:
            tag = "warn"
        elif line.startswith("tests/") or line.startswith("PASSED") or line.startswith("FAILED"):
            tag = "info"
        else:
            tag = "plain"

        widget.insert("end", line, tag)
        widget.see("end")

    def _stop_process(self) -> None:
        if self._proc:
            self._proc.terminate()
            self._set_status("Stopped by user", busy=False)

    def _update_ff_summary(self, summary: dict) -> None:
        for key, lbl in self._ff_labels.items():
            val = summary.get(key, "—")
            if isinstance(val, bool):
                lbl.configure(text="YES" if val else "NO",
                              fg=_GREEN if val else _RED)
            else:
                lbl.configure(text=str(val), fg=_DARK)


# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    root = tk.Tk()
    try:
        root.iconbitmap(str(_ROOT / "ui" / "icon.ico"))
    except Exception:
        pass
    AutomationApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
