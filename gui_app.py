import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import webbrowser
import os
from PIL import Image, ImageTk # For PNG logo
from cleaner_logic import Cleaner

class CleanerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Retrobytes.tech disk tool cleaner")
        self.root.geometry("600x700") # Adjusted for more content
        self.root.resizable(False, False)

        # Initialize Cleaner logic
        # The confirm_callback will be set to self.show_confirmation_dialog
        self.cleaner = Cleaner(status_callback=self.log_status, confirm_callback=self.show_confirmation_dialog)

        # Check permissions and drive before fully initializing GUI
        # This might trigger an admin prompt and exit/restart the script
        if not self.cleaner.ensure_permissions_and_drive():
            # If elevation failed or not on C drive, show message and exit
            # The actual exit due to elevation restart happens in cleaner_logic
            # This is a fallback message if it returns false without exiting (e.g. C drive issue)
            messagebox.showerror("Error", "Failed to meet prerequisites (Admin rights or C: drive). Exiting.")
            self.root.destroy()
            return

        # Style
        self.style = ttk.Style()
        self.style.theme_use('clam') # A clean, modern theme

        self.style.configure("TButton", padding=6, relief="flat", background="#0078D4", foreground="white")
        self.style.map("TButton",
            background=[('active', '#005A9E')],
            foreground=[('active', 'white')]
        )
        self.style.configure("TCheckbutton", padding=5, background="#f0f0f0")
        self.style.configure("TFrame", background="#f0f0f0")
        self.style.configure("TLabel", background="#f0f0f0", font=('Segoe UI', 10))
        self.style.configure("Header.TLabel", font=('Segoe UI', 14, 'bold'))
        self.style.configure("Link.TLabel", foreground="blue", font=('Segoe UI', 10, 'underline'))

        self.root.configure(bg="#f0f0f0")

        # Main frame
        main_frame = ttk.Frame(self.root, padding="10 10 10 10")
        main_frame.pack(expand=True, fill=tk.BOTH)

        # --- Logo and Title ---
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(pady=(0, 20), fill=tk.X)

        # Logo display is now optional. If logo.png is not present or causes error, it will be skipped.
        self.logo_image = None
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            logo_path = os.path.join(script_dir, "logo.png")
            if os.path.exists(logo_path):
                pil_image = Image.open(logo_path)
                pil_image = pil_image.resize((64, 64), Image.LANCZOS)
                self.logo_image = ImageTk.PhotoImage(pil_image)
                logo_label = ttk.Label(header_frame, image=self.logo_image, style="TLabel")
                logo_label.pack(side=tk.LEFT, padx=(0, 10))
            else:
                # No placeholder text if logo is simply absent
                self.log_status("[-] logo.png not found. Skipping logo display.")
        except Exception as e:
            self.log_status(f"[!] Error loading logo.png: {e}. Skipping logo display.")
            # No placeholder text on error either

        title_label = ttk.Label(header_frame, text="Retrobytes.tech disk tool cleaner", style="Header.TLabel")
        title_label.pack(side=tk.LEFT)

        # --- Cleaning Options ---
        options_frame = ttk.LabelFrame(main_frame, text="Cleaning Options", padding="10 10 10 10")
        options_frame.pack(fill=tk.X, pady=10)

        self.clean_user_temp_var = tk.BooleanVar(value=True)
        self.clean_windows_temp_var = tk.BooleanVar(value=True)
        self.clean_prefetch_var = tk.BooleanVar(value=True)
        self.clean_update_cache_var = tk.BooleanVar(value=True)

        ttk.Checkbutton(options_frame, text="Clean User Temp Files", variable=self.clean_user_temp_var, style="TCheckbutton").pack(anchor=tk.W)
        ttk.Checkbutton(options_frame, text="Clean Windows Temp Files", variable=self.clean_windows_temp_var, style="TCheckbutton").pack(anchor=tk.W)
        ttk.Checkbutton(options_frame, text="Clean Prefetch Files", variable=self.clean_prefetch_var, style="TCheckbutton").pack(anchor=tk.W)
        ttk.Checkbutton(options_frame, text="Clean Windows Update Cache", variable=self.clean_update_cache_var, style="TCheckbutton").pack(anchor=tk.W)

        # --- GPU Driver Cleanup ---
        gpu_frame = ttk.LabelFrame(main_frame, text="GPU Driver Management", padding="10 10 10 10")
        gpu_frame.pack(fill=tk.X, pady=10)

        self.gpu_drivers_button = ttk.Button(gpu_frame, text="Scan and Remove Old GPU Drivers", command=self.run_gpu_cleanup)
        self.gpu_drivers_button.pack(pady=5, fill=tk.X)

        # --- Action Buttons ---
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X, pady=20)

        self.run_button = ttk.Button(action_frame, text="Run Selected Cleanup", command=self.run_cleanup)
        self.run_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0,5))

        self.exit_button = ttk.Button(action_frame, text="Exit", command=self.root.quit)
        self.exit_button.pack(side=tk.RIGHT, expand=False, padx=(5,0)) # Changed side and expand

        self.about_button = ttk.Button(action_frame, text="About", command=self.show_about_window)
        self.about_button.pack(side=tk.RIGHT, expand=False, padx=(5,0)) # Added About button


        # --- Status/Log Area ---
        log_frame = ttk.LabelFrame(main_frame, text="Status Log", padding="10 10 10 10")
        log_frame.pack(expand=True, fill=tk.BOTH, pady=10)

        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=10, font=('Segoe UI', 9), relief=tk.SOLID, borderwidth=1)
        self.log_text.pack(expand=True, fill=tk.BOTH)
        self.log_text.configure(state='disabled') # Make it read-only initially

        # --- Website Link ---
        link_label = ttk.Label(main_frame, text="www.RetroBytes.Tech", style="Link.TLabel", cursor="hand2")
        link_label.pack(pady=(10,0))
        link_label.bind("<Button-1>", lambda e: webbrowser.open_new_tab("http://www.RetroBytes.Tech"))

        self.log_status("[*] Advanced Cleaner GUI initialized.")
        self.log_status("[*] Ensure the application is run as Administrator for full functionality.")
        if self.cleaner._is_admin():
            self.log_status("[+] Running with Administrator privileges.")
        else:
            self.log_status("[!] NOT running with Administrator privileges. Some operations may fail or UAC prompt might appear.")


    def log_status(self, message):
        self.log_text.configure(state='normal')
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END) # Scroll to the end
        self.log_text.configure(state='disabled')
        self.root.update_idletasks() # Ensure GUI updates

    def show_confirmation_dialog(self, title, message):
        return messagebox.askyesno(title, message, parent=self.root)

    def run_cleanup(self):
        self.log_status("\n[*] Starting selected cleanup operations...")

        if self.clean_user_temp_var.get():
            self.cleaner.clean_user_temp()
        if self.clean_windows_temp_var.get():
            self.cleaner.clean_windows_temp()
        if self.clean_prefetch_var.get():
            self.cleaner.clean_prefetch()
        if self.clean_update_cache_var.get():
            self.cleaner.clean_windows_update_cache()

        self.log_status("\n[✓] Selected cleanup operations complete.")
        messagebox.showinfo("Complete", "Selected cleanup operations have finished.", parent=self.root)

    def run_gpu_cleanup(self):
        self.log_status("\n[*] Initiating GPU driver cleanup...")
        # The confirmation is handled by the cleaner logic via confirm_callback
        self.cleaner.clean_gpu_drivers()
        self.log_status("\n[✓] GPU driver cleanup process finished.")
        # No separate messagebox here as logs and cleaner's own confirmation handle it

    def show_about_window(self):
        about_window = tk.Toplevel(self.root)
        about_window.title("About Advanced Cleaner")
        about_window.geometry("350x200")
        about_window.resizable(False, False)
        about_window.configure(bg="#f0f0f0")
        # Make it modal (optional, but common for about dialogs)
        about_window.grab_set()
        about_window.transient(self.root)

        about_frame = ttk.Frame(about_window, padding="15 15 15 15")
        about_frame.pack(expand=True, fill=tk.BOTH)

        app_name_label = ttk.Label(about_frame, text="Retrobytes.tech disk tool cleaner", style="Header.TLabel", font=('Segoe UI', 12, 'bold'))
        app_name_label.pack(pady=(0,10))

        created_by_label = ttk.Label(about_frame, text="Created by: Brent@RetroBytes.Tech", style="TLabel")
        created_by_label.pack(pady=5)

        paypal_link_text = "Support Development (PayPal)"
        paypal_url = "https://www.paypal.com/ncp/payment/8G356LHEZAC4G"

        paypal_label = ttk.Label(about_frame, text=paypal_link_text, style="Link.TLabel", cursor="hand2")
        paypal_label.pack(pady=10)
        paypal_label.bind("<Button-1>", lambda e: webbrowser.open_new_tab(paypal_url))

        separator = ttk.Separator(about_frame, orient='horizontal')
        separator.pack(fill='x', pady=10)

        ok_button = ttk.Button(about_frame, text="OK", command=about_window.destroy, style="TButton")
        ok_button.pack(pady=(5,0))

        # Center the about window on the root window
        self.root.update_idletasks() # Ensure root window dimensions are up to date
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (about_window.winfo_width() // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (about_window.winfo_height() // 2)
        about_window.geometry(f"+{x}+{y}")


if __name__ == '__main__':
    # This check is now primarily handled inside Cleaner and then by CleanerApp's init
    # cleaner_for_init_check = Cleaner()
    # if not cleaner_for_init_check.ensure_permissions_and_drive():
    #     # If ensure_permissions_and_drive() returned False (e.g. user cancelled UAC, or not C drive)
    #     # and didn't exit (because it wasn't a successful elevation restart)
    #     # then we shouldn't start the GUI.
    #     # The cleaner_logic itself handles the exit/restart for elevation.
    #     # If it gets here and it's false, it means elevation failed or other critical check failed.
    #     print("[!] Prerequisites not met. GUI will not start.")
    #     # No need to manually exit here if ensure_permissions_and_drive already handled it
    #     # or if CleanerApp constructor will handle it.
    # else:
    #     # This 'else' implies that either we are admin, or elevation was successful & script restarted.
    #     # OR that the check for some reason passed without admin (e.g. on non-Windows)
    #     # The CleanerApp class itself will re-verify.
    root = tk.Tk()
    app = CleanerApp(root)
    if not app.root.winfo_exists(): # Check if root window was destroyed due to error in init
        sys.exit(1) # Ensure script exits if GUI couldn't start
    root.mainloop()
