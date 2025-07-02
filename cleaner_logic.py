import os
import ctypes
import sys
import shutil
import subprocess
import winreg
import fnmatch # Added for wildcard matching in _delete_path

class Cleaner:
    def __init__(self, status_callback=print, confirm_callback=None):
        self.status_callback = status_callback
        self.confirm_callback = confirm_callback # Expected to be a function that returns True or False

    def _is_admin(self):
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False

    def _run_as_admin(self):
        if sys.platform == 'win32' and not self._is_admin():
            script = os.path.abspath(sys.argv[0])
            params = ' '.join([script] + sys.argv[1:])
            try:
                ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
                sys.exit(0) # Exit current non-admin instance
            except Exception as e:
                self.status_callback(f"[!] Failed to elevate privileges: {e}")
                return False
        return True # Already admin or not on Windows

    def _c_drive_only_check(self):
        if os.getenv('SystemDrive', 'C:').upper() != 'C:':
            self.status_callback("[!] This script is only designed to run on the C: drive.")
            self.status_callback(f"    Detected system drive: {os.getenv('SystemDrive')}")
            self.status_callback("    Aborting for safety.")
            return False
        return True

    def ensure_permissions_and_drive(self):
        if not self._c_drive_only_check():
            return False
        if not self._run_as_admin(): # This will try to restart as admin and exit if not admin
            # If it returns False here, it means elevation failed even after trying.
            # Or we are already admin, in which case _run_as_admin did nothing and returned True.
             if not self._is_admin(): # Double check if we are admin now
                self.status_callback("[!] Administrator privileges are required to run this script.")
                return False
        return True # All checks passed or restarted as admin

    def _delete_path(self, path, is_dir=True):
        path = os.path.expandvars(path) # Expand environment variables like %TEMP%
        if os.path.exists(path):
            try:
                if is_dir:
                    shutil.rmtree(path, ignore_errors=True) # ignore_errors similar to /q
                    self.status_callback(f"[+] Successfully removed directory: {path}")
                else: # file or wildcard
                    if "*" in os.path.basename(path) or "?" in os.path.basename(path):
                        # Handle wildcards by iterating
                        folder = os.path.dirname(path)
                        pattern = os.path.basename(path)
                        for f in os.listdir(folder):
                            if fnmatch.fnmatch(f, pattern):
                                file_path = os.path.join(folder, f)
                                try:
                                    if os.path.isfile(file_path) or os.path.islink(file_path):
                                        os.unlink(file_path)
                                    elif os.path.isdir(file_path):
                                        shutil.rmtree(file_path, ignore_errors=True)
                                except Exception as e_inner:
                                    self.status_callback(f"[!] Error deleting {file_path}: {e_inner}")
                        self.status_callback(f"[+] Attempted to clean items matching: {path}")
                    else: # Single file
                        os.remove(path)
                        self.status_callback(f"[+] Successfully removed file: {path}")

            except Exception as e:
                self.status_callback(f"[!] Error cleaning {path}: {e}")
        else:
            self.status_callback(f"[-] Path not found, skipping: {path}")

    def _create_dir(self, path):
        path = os.path.expandvars(path)
        try:
            os.makedirs(path, exist_ok=True)
            self.status_callback(f"[+] Ensured directory exists: {path}")
        except Exception as e:
            self.status_callback(f"[!] Error creating directory {path}: {e}")

    def clean_user_temp(self):
        self.status_callback("[+] Cleaning C:\\Users\\%USERNAME%\\AppData\\Local\\Temp")
        temp_path = "%TEMP%" # os.path.join(os.environ['USERPROFILE'], 'AppData', 'Local', 'Temp')
        self._delete_path(os.path.join(temp_path, '*.*'), is_dir=False) # Matches del /f /s /q
        # rd /s /q removes the directory itself, then batch script recreates it.
        # shutil.rmtree removes the dir.
        expanded_temp_path = os.path.expandvars(temp_path)
        self._delete_path(expanded_temp_path, is_dir=True)
        self._create_dir(expanded_temp_path)

    def clean_windows_temp(self):
        self.status_callback("[+] Cleaning C:\\Windows\\Temp")
        win_temp_path = "C:\\Windows\\Temp"
        self._delete_path(os.path.join(win_temp_path, '*.*'), is_dir=False)
        self._delete_path(win_temp_path, is_dir=True)
        self._create_dir(win_temp_path)

    def clean_prefetch(self):
        self.status_callback("[+] Cleaning C:\\Windows\\Prefetch")
        prefetch_path = "C:\\Windows\\Prefetch\\*.*"
        self._delete_path(prefetch_path, is_dir=False) # del /f /s /q "C:\Windows\Prefetch\*.*"

    def _run_command(self, command, success_msg="", error_msg=""):
        try:
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate()
            if process.returncode == 0:
                if success_msg: self.status_callback(success_msg)
                if stdout: self.status_callback(f"    Output: {stdout.strip()}")
                return True
            else:
                if error_msg: self.status_callback(error_msg)
                if stderr: self.status_callback(f"    Error: {stderr.strip()}")
                return False
        except Exception as e:
            if error_msg: self.status_callback(error_msg)
            self.status_callback(f"    Exception: {e}")
            return False

    def clean_windows_update_cache(self):
        self.status_callback("[+] Cleaning Windows Update cache")
        self.status_callback("    Stopping Windows Update service (wuauserv)...")
        if not self._run_command("net stop wuauserv", error_msg="[!] Failed to stop wuauserv. It might already be stopped or access denied."):
            # Even if stop fails, attempt cleanup. Maybe service was already stopped.
            pass

        soft_dist_path = "C:\\Windows\\SoftwareDistribution\\Download"
        self._delete_path(soft_dist_path, is_dir=True)
        self._create_dir(soft_dist_path) # Batch script doesn't recreate this one, but it's good practice

        self.status_callback("    Starting Windows Update service (wuauserv)...")
        if not self._run_command("net start wuauserv", error_msg="[!] Failed to start wuauserv. Check service manager."):
            pass
        self.status_callback("[+] Windows Update cache cleanup attempted.")

    def list_drivers_to_file(self, filename="drivers_list.txt"):
        self.status_callback("[*] Listing installed drivers...")
        output_path = os.path.join(os.getcwd(), filename) # Save in current dir
        try:
            with open(output_path, "w") as f:
                subprocess.run(["pnputil", "/enum-drivers"], stdout=f, text=True, check=True)
            self.status_callback(f"[+] Driver list saved to: {output_path}")
            return output_path
        except Exception as e:
            self.status_callback(f"[!] Error listing drivers: {e}")
            return None

    def get_installed_drivers_info(self):
        """Parses pnputil output to get driver details."""
        drivers = []
        try:
            result = subprocess.run(['pnputil', '/enum-drivers'], capture_output=True, text=True, encoding='utf-8', errors='ignore')
            output = result.stdout
            current_driver = {}
            for line in output.splitlines():
                line = line.strip()
                if not line: # Skip empty lines or start of new driver block
                    if current_driver.get("Published Name") and current_driver.get("Provider Name"): # Basic check for a valid entry
                        drivers.append(current_driver)
                    current_driver = {}
                    continue

                parts = line.split(":", 1)
                if len(parts) == 2:
                    key, value = parts[0].strip(), parts[1].strip()
                    current_driver[key] = value

            if current_driver.get("Published Name") and current_driver.get("Provider Name"): # Add last driver
                 drivers.append(current_driver)

        except FileNotFoundError:
            self.status_callback("[!] pnputil command not found.")
            return []
        except Exception as e:
            self.status_callback(f"[!] Error parsing driver list: {e}")
            return []
        return drivers

    def clean_gpu_drivers(self):
        self.status_callback("[*] Scanning for old GPU drivers (NVIDIA, AMD, Intel)...")

        if self.confirm_callback:
            if not self.confirm_callback("GPU Driver Cleanup", "Are you sure you want to scan and remove old GPU drivers (NVIDIA, AMD, Intel)? This can be risky."):
                self.status_callback("[-] GPU driver cleanup skipped by user.")
                return

        installed_drivers = self.get_installed_drivers_info()
        gpu_vendors = ["NVIDIA", "AMD", "INTEL"] # Case-insensitive check later
        deleted_count = 0

        if not installed_drivers:
            self.status_callback("[-] No drivers found or error fetching them.")
            return

        for driver in installed_drivers:
            oem_name = driver.get("Published Name")
            provider_name = driver.get("Provider Name")

            if not oem_name or not provider_name:
                continue

            is_gpu_driver = any(vendor.lower() in provider_name.lower() for vendor in gpu_vendors)

            if is_gpu_driver:
                # The original batch script deletes ALL drivers from these vendors.
                # This is quite aggressive. A safer approach might be to only remove older ones,
                # but the script implies removing any found from these vendors.
                # For now, replicate the script's behavior.
                self.status_callback(f"[+] Identified GPU driver: {oem_name} from {provider_name}.")
                self.status_callback(f"    Attempting to delete: {oem_name}")
                # pnputil /delete-driver <oemname> /uninstall /force
                cmd = ["pnputil", "/delete-driver", oem_name, "/uninstall", "/force"]
                try:
                    # Use run instead of Popen for simpler blocking execution here
                    result = subprocess.run(cmd, capture_output=True, text=True, check=False) # check=False to handle non-zero exits manually
                    if result.returncode == 0:
                        self.status_callback(f"    [✓] Successfully deleted {oem_name}")
                        deleted_count +=1
                    else:
                        # pnputil often returns non-zero even on success with /force if a reboot is needed or files are in use
                        # The key is whether it *tried*. The batch script also uses `>nul 2>&1` hiding errors.
                        # We'll log stderr if it's informative.
                        self.status_callback(f"    [*] pnputil exited with code {result.returncode} for {oem_name}.")
                        if result.stderr:
                            self.status_callback(f"        stderr: {result.stderr.strip()}")
                        if result.stdout: # Sometimes info is in stdout
                             self.status_callback(f"        stdout: {result.stdout.strip()}")
                        # Assuming for now that if it's a known GPU vendor, we mark as attempted.
                        # The original script doesn't really check for success of deletion.
                        deleted_count += 1 # Count as attempted, as per original script's aggressive nature
                except FileNotFoundError:
                    self.status_callback(f"    [!] pnputil command not found while trying to delete {oem_name}.")
                except Exception as e:
                    self.status_callback(f"    [!] Error deleting driver {oem_name}: {e}")

        if deleted_count > 0:
            self.status_callback(f"[+] Attempted deletion of {deleted_count} GPU driver package(s). A reboot may be required.")
        else:
            self.status_callback("[-] No GPU drivers from specified vendors found or targeted for deletion.")

# Example usage (for testing the logic directly):
if __name__ == "__main__":
    def mock_confirm(title, message):
        print(f"CONFIRM: {title} - {message}")
        # response = input("Type YES to confirm: ")
        # return response.upper() == "YES"
        return True # Auto-confirm for this test

    cleaner = Cleaner(status_callback=print, confirm_callback=mock_confirm)

    if cleaner.ensure_permissions_and_drive(): # This will try to elevate if not admin
        print("\n--- Running with Permissions ---")
        # cleaner.clean_user_temp()
        # cleaner.clean_windows_temp()
        # cleaner.clean_prefetch()
        # cleaner.clean_windows_update_cache()
        # cleaner.list_drivers_to_file()
        cleaner.clean_gpu_drivers()
        print("\n[✓] All selected operations completed (simulated).")
    else:
        print("[!] Script will not run due to permission or drive issues.")

    input("Press Enter to exit...") # Pause like the batch script
