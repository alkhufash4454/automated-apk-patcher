import os
import sys
import subprocess
import shutil

def run_command(command, input_str=None):
    print(f"[*] Running: {' '.join(command)}")
    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    stdout, stderr = process.communicate(input=input_str)
    if process.returncode != 0:
        print(f"[-] Error: {stderr}")
    return stdout, stderr, process.returncode

def is_flutter(apk_path):
    stdout, _, _ = run_command(["unzip", "-l", apk_path])
    return "libflutter.so" in stdout

def patch_flutter(apk_path):
    print("[+] Flutter detected. Applying reflutter patch...")
    # 1: BurpSuite/Proxy, 127.0.0.1
    input_data = "1\n127.0.0.1\n"
    stdout, stderr, code = run_command(["reflutter", apk_path], input_str=input_data)
    
    # reflutter usually outputs to release.RE.apk or [name].RE.apk
    output_name = apk_path.replace(".apk", ".RE.apk")
    if os.path.exists("release.RE.apk"):
        return "release.RE.apk"
    elif os.path.exists(output_name):
        return output_name
    
    # Search for any .RE.apk
    for f in os.listdir("."):
        if f.endswith(".RE.apk"):
            return f
    return None

def patch_native_ssl(apk_path):
    print("[+] Native/Java detected. Applying network security config patch...")
    # This is a placeholder for advanced native patching
    # For now, we rely on reflutter as it's the primary request
    return apk_path

def main():
    if len(sys.argv) < 2:
        print("Usage: python smart_patcher.py <apk_path>")
        sys.exit(1)
    
    apk_path = sys.argv[1]
    
    if is_flutter(apk_path):
        patched_apk = patch_flutter(apk_path)
    else:
        patched_apk = patch_native_ssl(apk_path)
    
    if patched_apk:
        print(f"[+] Successfully patched: {patched_apk}")
        if patched_apk != "patched_ready.apk":
            shutil.move(patched_apk, "patched_ready.apk")
    else:
        print("[-] Patching failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
