import customtkinter as ctk
from tkinter import filedialog
import fitz  # PyMuPDF
import os
import subprocess
import multiprocessing
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

# Set appearance mode and color theme
ctk.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

class App(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self):
        super().__init__()
        try:
            self.TkdndVersion = TkinterDnD._require(self)
        except Exception as e:
            print("TkinterDnD init error:", e)

        # configure window
        self.title("iCrushPDF")
        self.geometry(f"{500}x{440}")
        self.resizable(False, False)

        # state variables
        self.selected_file_path = None
        self.compressed_file_path = None

        # configure grid layout (1x1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Main frame
        self.main_frame = ctk.CTkFrame(self, corner_radius=15)
        self.main_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)

        # Title Label
        self.title_label = ctk.CTkLabel(self.main_frame, text="💘 iCrushPDF", font=ctk.CTkFont(size=24, weight="bold"))
        self.title_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        # Apply macOS accent colors
        self.accent_color = get_macos_accent_color()
        self.hover_color = get_macos_hover_color()

        # File selection button (Outlined for better contrast/less glare)
        self.select_button = ctk.CTkButton(self.main_frame, text="📁 Select or Drag PDF Here", command=self.select_file, height=40, font=ctk.CTkFont(size=14), fg_color="transparent", border_width=2, border_color=self.accent_color, text_color=self.accent_color, hover_color=("gray90", "gray20"))
        self.select_button.grid(row=1, column=0, padx=20, pady=10)

        # Selected file label
        self.file_label = ctk.CTkLabel(self.main_frame, text="Drop a PDF file anywhere on this window", font=ctk.CTkFont(size=12), text_color="gray")
        self.file_label.grid(row=2, column=0, padx=20, pady=(0, 10))

        # Compression level label
        self.level_label = ctk.CTkLabel(self.main_frame, text="Compression Level:", font=ctk.CTkFont(size=14))
        self.level_label.grid(row=3, column=0, padx=20, pady=(10, 0))

        # Compression Segmented Control
        self.compression_level = ctk.StringVar(value="Medium")
        self.level_control = ctk.CTkSegmentedButton(self.main_frame, values=["Low", "Medium", "High"], variable=self.compression_level, selected_color=self.accent_color, selected_hover_color=self.hover_color)
        self.level_control.grid(row=4, column=0, padx=20, pady=10)

        # Compress Button (Starts disabled with clean neutral system gray instead of bright accent)
        self.compress_button = ctk.CTkButton(self.main_frame, text="🔒 Select a PDF to Begin", command=self.compress_pdf, fg_color=("gray85", "#2D2D30"), text_color_disabled=("gray45", "gray70"), height=40, font=ctk.CTkFont(size=14, weight="bold"))
        self.compress_button.grid(row=5, column=0, padx=20, pady=(10, 10))
        self.compress_button.configure(state="disabled")

        # Progress Bar (hidden initially)
        self.progress_bar = ctk.CTkProgressBar(self.main_frame, mode="determinate", width=300, progress_color=self.accent_color)
        self.progress_bar.grid(row=6, column=0, padx=20, pady=(0, 10))
        self.progress_bar.grid_remove()

        # Result label
        self.result_label = ctk.CTkLabel(self.main_frame, text="", font=ctk.CTkFont(size=13))
        self.result_label.grid(row=7, column=0, padx=20, pady=5)

        # Reveal button (hidden initially)
        self.reveal_button = ctk.CTkButton(self.main_frame, text="📂 Reveal in Finder", command=self.reveal_in_finder, fg_color="transparent", border_width=1, text_color=("gray10", "#DCE4EE"), height=30)
        self.reveal_button.grid(row=8, column=0, padx=20, pady=(0, 10))
        self.reveal_button.grid_remove()

        # Footer / Version label
        self.version_label = ctk.CTkLabel(self.main_frame, text="v1.1.0 • 100% On-Device & Private 🔒", font=ctk.CTkFont(size=11), text_color="gray50")
        self.version_label.grid(row=9, column=0, padx=20, pady=(5, 10))

        # Start real-time monitoring of macOS Appearance Accent Color changes
        self.after(1500, self.monitor_macos_theme)

        # Setup Drag & Drop support on window and widgets
        try:
            for widget in [self, self.main_frame, self.select_button, self.file_label]:
                widget.drop_target_register(DND_FILES)
                widget.dnd_bind('<<Drop>>', self.on_drop_files)
        except Exception as e:
            print("DnD setup error:", e)

        # Native macOS Dock icon & Finder Open Document integration
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
            
            # Update all colored UI components in real-time
            self.select_button.configure(border_color=self.accent_color, text_color=self.accent_color)
            self.level_control.configure(selected_color=self.accent_color, selected_hover_color=self.hover_color)
            self.progress_bar.configure(progress_color=self.accent_color)
            if self.compress_button.cget("state") == "normal":
                self.compress_button.configure(fg_color=self.accent_color, hover_color=self.hover_color, text_color=("white", "black"))
            
            # Update text color of labels if they are currently displaying success or ready statuses
            if "Ready!" in self.file_label.cget("text"):
                self.file_label.configure(text_color=self.accent_color)
            if "Success!" in self.result_label.cget("text"):
                self.result_label.configure(text_color=self.accent_color)
                
        self.after(1500, self.monitor_macos_theme)

    def process_selected_file(self, file_path):
        if not file_path or not file_path.lower().endswith(".pdf"):
            self.file_label.configure(text="⚠️ Please drop a valid PDF file (.pdf)!", text_color="red")
            return

        self.selected_file_path = file_path
        filename = os.path.basename(file_path)
        if len(filename) > 40:
            filename = filename[:37] + "..."
        
        try:
            original_size = os.path.getsize(file_path) / (1024 * 1024)
            self.file_label.configure(text=f"📄 {filename} ({original_size:.2f} MB) — Ready!", text_color=self.accent_color)
            self.compress_button.configure(state="normal", text="🚀 Compress PDF Now", fg_color=self.accent_color, hover_color=self.hover_color, text_color=("white", "black"))
            self.result_label.configure(text="")
            self.reveal_button.grid_remove()
        except Exception as e:
            self.file_label.configure(text=f"⚠️ Error reading file size: {e}", text_color="red")

    def select_file(self):
        file_path = filedialog.askopenfilename(
            title="Select a PDF",
            filetypes=[("PDF files", "*.pdf")]
        )
        if file_path:
            self.process_selected_file(file_path)

    def on_drop_files(self, event):
        try:
            files = self.tk.splitlist(event.data)
            if files:
                self.process_selected_file(files[0])
        except Exception as e:
            print("Drop event parsing error:", e)

    def on_mac_open_document(self, *args):
        if args:
            self.process_selected_file(args[0])

    def compress_pdf(self):
        if not self.selected_file_path:
            return

        level_str = self.compression_level.get()
        original_size = os.path.getsize(self.selected_file_path)

        # Define output path
        dir_name = os.path.dirname(self.selected_file_path)
        base_name = os.path.basename(self.selected_file_path)
        name, ext = os.path.splitext(base_name)
        
        self.compressed_file_path = os.path.join(dir_name, f"{name}_compressed{ext}")

        # Update UI state to disabled neutral gray while compressing
        self.compress_button.configure(state="disabled", text="⏳ Compressing... Please Wait", fg_color=("gray85", "#2D2D30"), text_color_disabled=("gray45", "gray70"))
        self.result_label.configure(text="⚙️ Optimizing fonts and compressing images...", text_color="gray")
        self.reveal_button.grid_remove()
        
        # Show and reset progress bar
        self.progress_bar.set(0)
        self.current_progress = 0.0
        self.progress_bar.grid()
        self.update_idletasks()  # Force Tkinter to render the progress bar immediately

        # Run compression in a separate PROCESS so PyMuPDF does not block the UI (GIL freeze)
        self.queue = multiprocessing.Queue()
        self.process = multiprocessing.Process(target=compress_worker, args=(self.selected_file_path, self.compressed_file_path, level_str, self.queue))
        self.process.start()

        # Check status every 100 milliseconds without blocking
        self.after(100, self.check_compression_status, original_size)

    def check_compression_status(self, original_size):
        if not self.queue.empty():
            status = self.queue.get()
            if status == "SUCCESS":
                # Jump to 100%
                self.progress_bar.set(1.0)
                self.update_idletasks()
                
                # Wait a tiny bit so the user sees 100% before it disappears
                self.after(300, lambda: self._show_success(original_size))
            else:
                self.progress_bar.grid_remove()
                error_msg = status[7:]
                self.result_label.configure(text=f"❌ Error: {error_msg}", text_color="#FF3B30")
                self.compress_button.configure(state="normal", text="🔄 Try Again", fg_color=self.accent_color, hover_color=self.hover_color, text_color=("white", "black"))
        else:
            if self.process.is_alive():
                # Asymptotic progress bar (Zeno's progress bar)
                # Approaches 95% but never reaches it, fast at first, slow later
                self.current_progress = self.current_progress + (0.95 - self.current_progress) * 0.03
                self.progress_bar.set(self.current_progress)
                self.after(100, self.check_compression_status, original_size)
            else:
                # Process ended without sending output
                self.progress_bar.grid_remove()
                self.result_label.configure(text="❌ Error: Compression process terminated abruptly.", text_color="#FF3B30")
                self.compress_button.configure(state="normal", text="🔄 Try Again", fg_color=self.accent_color, hover_color=self.hover_color, text_color=("white", "black"))

    def _show_success(self, original_size):
        self.progress_bar.grid_remove()
        new_size = os.path.getsize(self.compressed_file_path)
        orig_mb = original_size / (1024 * 1024)
        new_mb = new_size / (1024 * 1024)
        savings = (1 - (new_size / original_size)) * 100
        if savings < 0:
            savings = 0
        self.result_label.configure(text=f"🎉 Success! Reduced from {orig_mb:.2f} MB to {new_mb:.2f} MB (-{savings:.1f}%)", text_color=self.accent_color)
        self.reveal_button.grid()
        self.compress_button.configure(state="normal", text="✨ Compress Again", fg_color=self.accent_color, hover_color=self.hover_color, text_color=("white", "black"))
        self.file_label.configure(text=f"✅ Done! Select another file or change level.", text_color="gray")

    def reveal_in_finder(self):
        if self.compressed_file_path and os.path.exists(self.compressed_file_path):
            # MacOS specific command to reveal in finder
            subprocess.run(["open", "-R", self.compressed_file_path])

if __name__ == "__main__":
    multiprocessing.freeze_support()
    app = App()
    app.mainloop()
