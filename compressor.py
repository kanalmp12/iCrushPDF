import customtkinter as ctk
from tkinter import filedialog
import fitz  # PyMuPDF
import os
import subprocess
import multiprocessing
import uuid
import time
from dataclasses import dataclass
from tkinterdnd2 import TkinterDnD, DND_FILES


def get_macos_accent_color():
    try:
        result = subprocess.run(["defaults", "read", "-g", "AppleAccentColor"], capture_output=True, text=True)
        val = result.stdout.strip()
        if val == "0": return ("#FF3B30", "#FF453A") # Red
        if val == "1": return ("#FF9500", "#FF9F0A") # Orange
        if val == "2": return ("#FFCC00", "#FFD60A") # Yellow
        if val == "3": return ("#28CD41", "#32D74B") # Green
        if val == "5": return ("#AF52DE", "#BF5AF2") # Purple
        if val == "6": return ("#FF2D55", "#FF375F") # Pink
        if val == "7": return ("#8E8E93", "#98989D") # Graphite
    except Exception:
        pass
    return ("#007AFF", "#0A84FF") # Default Blue


def get_macos_hover_color():
    try:
        result = subprocess.run(["defaults", "read", "-g", "AppleAccentColor"], capture_output=True, text=True)
        val = result.stdout.strip()
        if val == "0": return ("#D70015", "#FF6961") # Red Hover
        if val == "1": return ("#C93400", "#FFB340") # Orange Hover
        if val == "2": return ("#B25000", "#FFD426") # Yellow Hover
        if val == "3": return ("#248A3D", "#30DB5B") # Green Hover
        if val == "5": return ("#8944AB", "#D38DF1") # Purple Hover
        if val == "6": return ("#D30F45", "#FF6482") # Pink Hover
        if val == "7": return ("#6C6C70", "#AEAEB2") # Graphite Hover
    except Exception:
        pass
    return ("#0051CB", "#409CFF") # Default Blue Hover


def compress_worker(input_path, output_path, level_str, queue):
    try:
        if level_str == "Low":
            garbage = 1
            clean = False
        elif level_str == "Medium":
            garbage = 3
            clean = True
        else: # High
            garbage = 4
            clean = True

        doc = fitz.open(input_path)
        
        if level_str == "Medium":
            doc.rewrite_images(dpi_target=144, quality=70)
        elif level_str == "High":
            doc.rewrite_images(dpi_target=72, quality=40)
        
        doc.save(output_path, garbage=garbage, deflate=True, clean=clean)
        doc.close()
        queue.put("SUCCESS")
    except Exception as e:
        queue.put(f"ERROR: {str(e)}")


@dataclass
class QueueItem:
    id: str
    input_path: str
    output_folder: str = "" # Empty means same directory as input
    level: str = "Medium"
    status: str = "pending" # "pending", "compressing", "done", "error", "cancelled"
    original_size: int = 0
    compressed_size: int = 0
    savings_pct: float = 0.0
    error_msg: str = ""
    output_path: str = ""


class QueueItemRow(ctk.CTkFrame):
    SPINNER_FRAMES = ["◐", "◓", "◑", "◒"]

    def __init__(self, master, app, item: QueueItem, **kwargs):
        super().__init__(master, corner_radius=8, fg_color=("gray92", "#2B2B2E"), **kwargs)
        self.app = app
        self.item = item
        self._spin_idx = 0
        self._spinner_after_id = None

        # Configure Grid Layout: [Status (0), File Info (1), Level Menu (2), Action Button (3)]
        self.grid_columnconfigure(1, weight=1)

        # Status Icon Label
        self.status_label = ctk.CTkLabel(self, text="🕐", font=ctk.CTkFont(size=16), width=24)
        self.status_label.grid(row=0, column=0, padx=(10, 5), pady=8, sticky="w")

        # Filename & Size Details Container Frame
        self.info_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.info_frame.grid(row=0, column=1, padx=5, pady=6, sticky="ew")
        self.info_frame.grid_columnconfigure(0, weight=1)

        # Filename (Truncated cleanly)
        filename = os.path.basename(item.input_path)
        display_name = filename if len(filename) <= 28 else filename[:25] + "..."
        self.name_label = ctk.CTkLabel(self.info_frame, text=display_name, font=ctk.CTkFont(size=13, weight="bold"), anchor="w")
        self.name_label.grid(row=0, column=0, sticky="w")

        # Size / Detail Status Label
        orig_mb = item.original_size / (1024 * 1024)
        self.detail_label = ctk.CTkLabel(self.info_frame, text=f"{orig_mb:.2f} MB", font=ctk.CTkFont(size=11), text_color="gray60", anchor="w")
        self.detail_label.grid(row=1, column=0, sticky="w")

        # Compression Level Dropdown
        self.level_var = ctk.StringVar(value=item.level)
        self.level_menu = ctk.CTkOptionMenu(
            self,
            values=["Low", "Medium", "High"],
            variable=self.level_var,
            command=self._on_level_changed,
            width=90,
            height=28,
            font=ctk.CTkFont(size=11),
            fg_color=self.app.accent_color,
            button_color=self.app.hover_color,
            button_hover_color=self.app.hover_color
        )
        self.level_menu.grid(row=0, column=2, padx=6, pady=8)

        # Action Button (✕ / 📂 / ↺)
        self.action_button = ctk.CTkButton(
            self,
            text="✕",
            width=28,
            height=28,
            command=self._on_action_click,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="transparent",
            hover_color=("gray80", "#3E3E42"),
            text_color=("gray20", "gray80"),
            border_width=1,
            border_color=("gray75", "gray40")
        )
        self.action_button.grid(row=0, column=3, padx=(4, 10), pady=8)

        self.refresh()

    def _on_level_changed(self, choice):
        self.item.level = choice

    def _on_action_click(self):
        if self.item.status == "pending":
            self.app.remove_item(self.item)
        elif self.item.status == "compressing":
            self.app.cancel_current_item()
        elif self.item.status == "done":
            if self.item.output_path and os.path.exists(self.item.output_path):
                subprocess.run(["open", "-R", self.item.output_path])
        elif self.item.status in ("error", "cancelled"):
            self.app.retry_item(self.item)

    def refresh(self):
        orig_mb = self.item.original_size / (1024 * 1024)

        if self.item.status == "pending":
            self.status_label.configure(text="🕐", text_color=("gray30", "gray70"))
            self.detail_label.configure(text=f"{orig_mb:.2f} MB • Ready", text_color="gray60")
            self.level_menu.configure(state="normal")
            self.action_button.configure(text="✕", text_color=("gray30", "gray70"), state="normal")
            self._stop_spinner()

        elif self.item.status == "compressing":
            self.level_menu.configure(state="disabled")
            self.detail_label.configure(text=f"{orig_mb:.2f} MB • Compressing...", text_color=self.app.accent_color)
            self.action_button.configure(text="⏹", text_color="#FF3B30", state="normal")
            self._start_spinner()

        elif self.item.status == "done":
            self._stop_spinner()
            self.status_label.configure(text="✅", text_color="#34C759")
            new_mb = self.item.compressed_size / (1024 * 1024)
            self.detail_label.configure(
                text=f"{orig_mb:.2f} MB → {new_mb:.2f} MB (-{self.item.savings_pct:.1f}%)",
                text_color=self.app.accent_color
            )
            self.level_menu.configure(state="disabled")
            self.action_button.configure(text="📂", text_color=self.app.accent_color, state="normal")

        elif self.item.status == "error":
            self._stop_spinner()
            self.status_label.configure(text="❌", text_color="#FF3B30")
            error_short = self.item.error_msg if len(self.item.error_msg) <= 26 else self.item.error_msg[:23] + "..."
            self.detail_label.configure(text=f"Error: {error_short}", text_color="#FF3B30")
            self.level_menu.configure(state="normal")
            self.action_button.configure(text="↺", text_color=self.app.accent_color, state="normal")

        elif self.item.status == "cancelled":
            self._stop_spinner()
            self.status_label.configure(text="⏹", text_color="#FF9500")
            self.detail_label.configure(text="Cancelled", text_color="#FF9500")
            self.level_menu.configure(state="normal")
            self.action_button.configure(text="↺", text_color=self.app.accent_color, state="normal")

    def _start_spinner(self):
        if not self._spinner_after_id:
            self._tick_spinner()

    def _stop_spinner(self):
        if self._spinner_after_id:
            self.after_cancel(self._spinner_after_id)
            self._spinner_after_id = None

    def _tick_spinner(self):
        if self.item.status == "compressing":
            self.status_label.configure(
                text=self.SPINNER_FRAMES[self._spin_idx % len(self.SPINNER_FRAMES)],
                text_color=self.app.accent_color
            )
            self._spin_idx += 1
            self._spinner_after_id = self.after(150, self._tick_spinner)
        else:
            self._spinner_after_id = None


# Set appearance mode and color theme
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class App(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self):
        super().__init__()
        try:
            self.TkdndVersion = TkinterDnD._require(self)
        except Exception as e:
            print("TkinterDnD init error:", e)

        # Configure Window
        self.title("iCrushPDF")
        self.geometry("600x600")
        self.minsize(560, 480)
        self.resizable(False, True)

        # State Variables
        self.queue_items: list[QueueItem] = []
        self.row_widgets: dict[str, QueueItemRow] = {}
        self.global_output_folder: str | None = None
        self._is_running: bool = False
        self._current_process: multiprocessing.Process | None = None
        self._current_queue: multiprocessing.Queue | None = None
        self._current_item: QueueItem | None = None
        self._current_item_progress: float = 0.0
        self._queue_start_time: float = 0.0
        self._completed_count: int = 0
        self._total_in_batch: int = 0

        # Colors
        self.accent_color = get_macos_accent_color()
        self.hover_color = get_macos_hover_color()

        # Layout Configuration (1 column, main frame stretches)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Main Container Frame
        self.main_frame = ctk.CTkFrame(self, corner_radius=15)
        self.main_frame.grid(row=0, column=0, padx=16, pady=16, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(4, weight=1) # Scrollable area expands

        # Row 0: App Title
        self.title_label = ctk.CTkLabel(self.main_frame, text="💘 iCrushPDF", font=ctk.CTkFont(size=24, weight="bold"))
        self.title_label.grid(row=0, column=0, padx=20, pady=(16, 8))

        # Row 1: Top Toolbar (Add Files, Clear All)
        self.toolbar_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.toolbar_frame.grid(row=1, column=0, padx=20, pady=4, sticky="ew")
        self.toolbar_frame.grid_columnconfigure(0, weight=1)

        self.add_button = ctk.CTkButton(
            self.toolbar_frame,
            text="📁 Add PDF Files...",
            command=self.select_files,
            height=36,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="transparent",
            border_width=2,
            border_color=self.accent_color,
            text_color=self.accent_color,
            hover_color=("gray90", "gray20")
        )
        self.add_button.grid(row=0, column=0, sticky="w")

        self.clear_all_button = ctk.CTkButton(
            self.toolbar_frame,
            text="Clear All",
            command=self.clear_all_items,
            height=36,
            width=90,
            font=ctk.CTkFont(size=12),
            fg_color="transparent",
            border_width=1,
            border_color=("gray75", "gray40"),
            text_color=("gray30", "gray70"),
            hover_color=("gray85", "#353538")
        )
        self.clear_all_button.grid(row=0, column=1, padx=(10, 0), sticky="e")

        # Row 2: Output Destination Bar
        self.output_bar_frame = ctk.CTkFrame(self.main_frame, corner_radius=8, fg_color=("gray90", "#242427"))
        self.output_bar_frame.grid(row=2, column=0, padx=20, pady=(8, 4), sticky="ew")
        self.output_bar_frame.grid_columnconfigure(0, weight=1)

        self.output_label = ctk.CTkLabel(
            self.output_bar_frame,
            text="📂 Output: Same as input",
            font=ctk.CTkFont(size=12),
            text_color=("gray30", "gray70"),
            anchor="w"
        )
        self.output_label.grid(row=0, column=0, padx=12, pady=6, sticky="w")

        self.change_output_btn = ctk.CTkButton(
            self.output_bar_frame,
            text="Change...",
            width=75,
            height=24,
            command=self.choose_global_output_folder,
            font=ctk.CTkFont(size=11),
            fg_color="transparent",
            border_width=1,
            border_color=("gray75", "gray40"),
            text_color=("gray20", "gray80")
        )
        self.change_output_btn.grid(row=0, column=1, padx=4, pady=6)

        self.reset_output_btn = ctk.CTkButton(
            self.output_bar_frame,
            text="Reset",
            width=50,
            height=24,
            command=self.reset_global_output_folder,
            font=ctk.CTkFont(size=11),
            fg_color="transparent",
            border_width=1,
            border_color=("gray75", "gray40"),
            text_color=("gray20", "gray80")
        )
        self.reset_output_btn.grid(row=0, column=2, padx=(2, 8), pady=6)

        # Row 3: Warning / Notice Banner (Hidden initially)
        self.warning_label = ctk.CTkLabel(
            self.main_frame,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="#FF9500",
            wraplength=520
        )
        self.warning_label.grid(row=3, column=0, padx=20, pady=2)
        self.warning_label.grid_remove()

        # Row 4: Queue Scrollable Frame
        self.queue_frame = ctk.CTkScrollableFrame(self.main_frame, corner_radius=10, fg_color=("gray96", "#1E1E20"))
        self.queue_frame.grid(row=4, column=0, padx=20, pady=(6, 8), sticky="nsew")
        self.queue_frame.grid_columnconfigure(0, weight=1)

        # Empty state placeholder label
        self.empty_label = ctk.CTkLabel(
            self.queue_frame,
            text="📄 Drag & Drop PDF files here or click 'Add PDF Files...'\nto begin compressing",
            font=ctk.CTkFont(size=13),
            text_color="gray50",
            justify="center"
        )
        self.empty_label.pack(pady=60)

        # Row 5: Overall Progress Bar
        self.progress_bar = ctk.CTkProgressBar(self.main_frame, mode="determinate", progress_color=self.accent_color)
        self.progress_bar.grid(row=5, column=0, padx=20, pady=(4, 2), sticky="ew")
        self.progress_bar.set(0)

        # Row 6: Overall Status & ETA Label
        self.overall_status_label = ctk.CTkLabel(
            self.main_frame,
            text="Queue is empty",
            font=ctk.CTkFont(size=12),
            text_color="gray50"
        )
        self.overall_status_label.grid(row=6, column=0, padx=20, pady=(2, 6))

        # Row 7: Action Controls (Compress All, Cancel)
        self.action_controls_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.action_controls_frame.grid(row=7, column=0, padx=20, pady=(4, 8), sticky="ew")
        self.action_controls_frame.grid_columnconfigure(0, weight=3)
        self.action_controls_frame.grid_columnconfigure(1, weight=1)

        self.compress_all_button = ctk.CTkButton(
            self.action_controls_frame,
            text="🔒 Add Files to Compress",
            command=self.start_queue,
            height=42,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=("gray85", "#2D2D30"),
            text_color_disabled=("gray45", "gray70"),
            state="disabled"
        )
        self.compress_all_button.grid(row=0, column=0, padx=(0, 8), sticky="ew")

        self.cancel_button = ctk.CTkButton(
            self.action_controls_frame,
            text="⏹ Cancel",
            command=self.cancel_queue,
            height=42,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="transparent",
            border_width=1,
            border_color="#FF3B30",
            text_color="#FF3B30",
            hover_color=("gray85", "#3A1E20"),
            state="disabled"
        )
        self.cancel_button.grid(row=0, column=1, sticky="ew")

        # Row 8: Version Footer
        self.version_label = ctk.CTkLabel(
            self.main_frame,
            text="v1.2.0 • 100% On-Device & Private 🔒",
            font=ctk.CTkFont(size=11),
            text_color="gray50"
        )
        self.version_label.grid(row=8, column=0, padx=20, pady=(4, 10))

        # Start Real-Time macOS Appearance Monitoring
        self.after(1500, self.monitor_macos_theme)

        # Setup Drag & Drop
        try:
            for widget in [self, self.main_frame, self.toolbar_frame, self.queue_frame, self.empty_label]:
                widget.drop_target_register(DND_FILES)
                widget.dnd_bind('<<Drop>>', self.on_drop_files)
        except Exception as e:
            print("DnD setup error:", e)

        # Native macOS Dock / Finder open event
        try:
            self.createcommand("::tk::mac::OpenDocument", self.on_mac_open_document)
        except Exception:
            pass

    def monitor_macos_theme(self):
        new_accent = get_macos_accent_color()
        new_hover = get_macos_hover_color()
        if new_accent != self.accent_color:
            self.accent_color = new_accent
            self.hover_color = new_hover

            self.add_button.configure(border_color=self.accent_color, text_color=self.accent_color)
            self.progress_bar.configure(progress_color=self.accent_color)
            if self.compress_all_button.cget("state") == "normal":
                self.compress_all_button.configure(fg_color=self.accent_color, hover_color=self.hover_color)

            # Update option menus and active icons in rows
            for row in self.row_widgets.values():
                row.level_menu.configure(
                    fg_color=self.accent_color,
                    button_color=self.hover_color,
                    button_hover_color=self.hover_color
                )
                if row.item.status in ("done", "compressing"):
                    row.refresh()

        self.after(1500, self.monitor_macos_theme)

    def choose_global_output_folder(self):
        chosen = filedialog.askdirectory(title="Select Output Folder for Compressed PDFs")
        if chosen:
            self.global_output_folder = chosen
            folder_name = os.path.basename(chosen) or chosen
            display = folder_name if len(folder_name) <= 25 else folder_name[:22] + "..."
            self.output_label.configure(text=f"📂 Output: {display}")

    def reset_global_output_folder(self):
        self.global_output_folder = None
        self.output_label.configure(text="📂 Output: Same as input")

    def select_files(self):
        paths = filedialog.askopenfilenames(
            title="Select PDF Files",
            filetypes=[("PDF files", "*.pdf")]
        )
        if paths:
            self.add_files(list(paths))

    def on_drop_files(self, event):
        try:
            files = self.tk.splitlist(event.data)
            if files:
                self.add_files(list(files))
        except Exception as e:
            print("Drop event parsing error:", e)

    def on_mac_open_document(self, *args):
        if args:
            self.add_files(list(args))

    def add_files(self, paths: list[str]):
        existing_paths = {item.input_path for item in self.queue_items}
        duplicates = []
        added_count = 0

        for p in paths:
            if not p or not p.lower().endswith(".pdf") or not os.path.exists(p):
                continue

            if p in existing_paths:
                duplicates.append(os.path.basename(p))
                continue

            try:
                size = os.path.getsize(p)
            except Exception:
                size = 0

            item = QueueItem(
                id=str(uuid.uuid4()),
                input_path=p,
                output_folder=self.global_output_folder if self.global_output_folder else "",
                level="Medium",
                status="pending",
                original_size=size
            )
            self.queue_items.append(item)
            existing_paths.add(p)
            added_count += 1

        if duplicates:
            sample = ", ".join(duplicates[:2])
            suffix = f" (+{len(duplicates)-2} more)" if len(duplicates) > 2 else ""
            self._show_warning(f"⚠️ Already in queue: {sample}{suffix}")
        else:
            self._clear_warning()

        self._rebuild_queue_ui()
        self._update_overall_progress_ui()

    def _show_warning(self, msg: str):
        self.warning_label.configure(text=msg)
        self.warning_label.grid()

    def _clear_warning(self):
        self.warning_label.configure(text="")
        self.warning_label.grid_remove()

    def remove_item(self, item: QueueItem):
        if item in self.queue_items:
            self.queue_items.remove(item)
            self._rebuild_queue_ui()
            self._update_overall_progress_ui()

    def retry_item(self, item: QueueItem):
        item.status = "pending"
        item.error_msg = ""
        if item.id in self.row_widgets:
            self.row_widgets[item.id].refresh()
        self._update_overall_progress_ui()
        if not self._is_running:
            self.start_queue()

    def clear_all_items(self):
        if self._is_running:
            return
        self.queue_items.clear()
        self._clear_warning()
        self._rebuild_queue_ui()
        self._update_overall_progress_ui()

    def _rebuild_queue_ui(self):
        # Clear existing row widgets
        for row in self.row_widgets.values():
            row.pack_forget()
            row.destroy()
        self.row_widgets.clear()

        if not self.queue_items:
            self.empty_label.pack(pady=60)
        else:
            self.empty_label.pack_forget()
            for item in self.queue_items:
                row = QueueItemRow(self.queue_frame, self, item)
                row.pack(fill="x", padx=4, pady=3)
                self.row_widgets[item.id] = row

    def _update_overall_progress_ui(self):
        total = len(self.queue_items)
        if total == 0:
            self.progress_bar.set(0)
            self.overall_status_label.configure(text="Queue is empty", text_color="gray50")
            self.compress_all_button.configure(
                state="disabled",
                text="🔒 Add Files to Compress",
                fg_color=("gray85", "#2D2D30"),
                text_color_disabled=("gray45", "gray70")
            )
            self.cancel_button.configure(state="disabled")
            return

        pending = sum(1 for i in self.queue_items if i.status == "pending")
        done = sum(1 for i in self.queue_items if i.status == "done")
        errors = sum(1 for i in self.queue_items if i.status == "error")
        cancelled = sum(1 for i in self.queue_items if i.status == "cancelled")

        fraction = done / total if total > 0 else 0
        self.progress_bar.set(fraction)

        if self._is_running:
            self.compress_all_button.configure(
                state="disabled",
                text="⏳ Compressing Queue...",
                fg_color=("gray85", "#2D2D30"),
                text_color_disabled=("gray45", "gray70")
            )
            self.cancel_button.configure(state="normal")
            self.clear_all_button.configure(state="disabled")
        else:
            self.cancel_button.configure(state="disabled")
            self.clear_all_button.configure(state="normal")
            if pending > 0:
                self.compress_all_button.configure(
                    state="normal",
                    text=f"🚀 Compress {pending} File{'s' if pending > 1 else ''}",
                    fg_color=self.accent_color,
                    hover_color=self.hover_color,
                    text_color=("white", "black")
                )
            else:
                self.compress_all_button.configure(
                    state="disabled",
                    text="✨ All Files Done",
                    fg_color=("gray85", "#2D2D30"),
                    text_color_disabled=("gray45", "gray70")
                )

        if not self._is_running:
            if done == total and total > 0:
                self.overall_status_label.configure(
                    text=f"🎉 All {total} files compressed successfully!",
                    text_color=self.accent_color
                )
            elif errors > 0 or cancelled > 0:
                self.overall_status_label.configure(
                    text=f"{done}/{total} done • {errors} error(s) • {cancelled} cancelled • {pending} pending",
                    text_color="gray60"
                )
            else:
                self.overall_status_label.configure(
                    text=f"{done}/{total} files done • {pending} ready to compress",
                    text_color="gray60"
                )

    def _resolve_output_path(self, item: QueueItem) -> str:
        folder = item.output_folder if item.output_folder else os.path.dirname(item.input_path)
        base_name = os.path.basename(item.input_path)
        name, ext = os.path.splitext(base_name)

        target = os.path.join(folder, f"{name}_compressed{ext}")
        counter = 1
        while os.path.exists(target):
            target = os.path.join(folder, f"{name}_compressed_{counter}{ext}")
            counter += 1
        return target

    def start_queue(self):
        if self._is_running:
            return

        pending_items = [i for i in self.queue_items if i.status == "pending"]
        if not pending_items:
            return

        self._is_running = True
        self._queue_start_time = time.time()
        self._completed_count = 0
        self._total_in_batch = len(pending_items)

        self._update_overall_progress_ui()
        self._process_next()

    def _process_next(self):
        if not self._is_running:
            self._on_queue_finished()
            return

        # Find next pending item
        item = next((i for i in self.queue_items if i.status == "pending"), None)
        if not item:
            self._on_queue_finished()
            return

        self._current_item = item
        self._current_item_progress = 0.0
        item.status = "compressing"
        if item.id in self.row_widgets:
            self.row_widgets[item.id].refresh()

        # Update ETA status
        self._update_eta_status()

        # Resolve output destination
        item.output_path = self._resolve_output_path(item)

        # Launch process
        self._current_queue = multiprocessing.Queue()
        self._current_process = multiprocessing.Process(
            target=compress_worker,
            args=(item.input_path, item.output_path, item.level, self._current_queue)
        )
        self._current_process.start()

        self.after(100, self._check_current_process)

    def _update_eta_status(self):
        if not self._is_running:
            return

        total = len(self.queue_items)
        done = sum(1 for i in self.queue_items if i.status == "done")
        current_idx = done + 1
        elapsed = time.time() - self._queue_start_time

        if self._completed_count > 0:
            avg_per_file = elapsed / self._completed_count
            remaining_files = sum(1 for i in self.queue_items if i.status == "pending")
            eta_sec = int(avg_per_file * remaining_files)
            if eta_sec < 60:
                eta_str = f"~{eta_sec}s left"
            else:
                eta_str = f"~{eta_sec // 60}m {eta_sec % 60}s left"
            self.overall_status_label.configure(
                text=f"Compressing file {current_idx}/{total} ({eta_str})...",
                text_color=self.accent_color
            )
        else:
            self.overall_status_label.configure(
                text=f"Compressing file {current_idx}/{total} (calculating ETA...)...",
                text_color=self.accent_color
            )

    def _check_current_process(self):
        if not self._is_running or not self._current_item:
            return

        if self._current_queue and not self._current_queue.empty():
            status = self._current_queue.get()
            self._handle_item_result(status)
        elif self._current_process and self._current_process.is_alive():
            # Asymptotic smooth progress within current item's slice of the overall bar
            self._current_item_progress = self._current_item_progress + (0.95 - self._current_item_progress) * 0.03
            total = len(self.queue_items)
            done = sum(1 for i in self.queue_items if i.status == "done")
            if total > 0:
                overall_fraction = (done + self._current_item_progress) / total
                self.progress_bar.set(overall_fraction)
            self.after(100, self._check_current_process)
        else:
            # Process terminated without putting SUCCESS in queue
            self._handle_item_result("ERROR: Process terminated unexpectedly")

    def _handle_item_result(self, result: str):
        item = self._current_item
        if not item:
            return

        if result == "SUCCESS":
            item.status = "done"
            self._current_item_progress = 1.0
            try:
                item.compressed_size = os.path.getsize(item.output_path)
                if item.original_size > 0:
                    item.savings_pct = max(0.0, (1 - (item.compressed_size / item.original_size)) * 100)
            except Exception:
                item.compressed_size = item.original_size
                item.savings_pct = 0.0
        else:
            item.status = "error"
            item.error_msg = result[7:] if result.startswith("ERROR: ") else result

        self._completed_count += 1

        if item.id in self.row_widgets:
            self.row_widgets[item.id].refresh()

        self._current_process = None
        self._current_queue = None
        self._current_item = None

        self._update_overall_progress_ui()
        self.after(200, self._process_next)

    def cancel_current_item(self):
        if self._current_process and self._current_process.is_alive():
            self._current_process.terminate()

        if self._current_item:
            self._current_item.status = "cancelled"
            if self._current_item.id in self.row_widgets:
                self.row_widgets[self._current_item.id].refresh()

        self._current_process = None
        self._current_queue = None
        self._current_item = None

        self._update_overall_progress_ui()
        if self._is_running:
            self.after(200, self._process_next)

    def cancel_queue(self):
        self._is_running = False
        if self._current_process and self._current_process.is_alive():
            self._current_process.terminate()

        if self._current_item:
            self._current_item.status = "cancelled"
            if self._current_item.id in self.row_widgets:
                self.row_widgets[self._current_item.id].refresh()

        self._current_process = None
        self._current_queue = None
        self._current_item = None

        self._on_queue_finished()

    def _on_queue_finished(self):
        self._is_running = False
        self._update_overall_progress_ui()
        self._send_macos_notification()

    def _send_macos_notification(self):
        done = sum(1 for i in self.queue_items if i.status == "done")
        errors = sum(1 for i in self.queue_items if i.status == "error")
        if done == 0 and errors == 0:
            return

        msg = f"{done} file(s) compressed"
        if errors > 0:
            msg += f", {errors} error(s)"

        try:
            subprocess.run([
                "osascript", "-e",
                f'display notification "{msg}" with title "iCrushPDF 💘" sound name "Glass"'
            ], check=False)
        except Exception as e:
            print("Notification error:", e)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    app = App()
    app.mainloop()
