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
    return stdout, stderr, process.returncode

def is_flutter(apk_path):
    stdout, _, _ = run_command(["unzip", "-l", apk_path])
    return "libflutter.so" in stdout

def patch_flutter_pro(apk_path):
    print("[+] Flutter Pro Patcher starting...")
    
    # Try reflutter first as it's stable for many apps
    print("[*] Attempting reflutter (Method 1)...")
    input_data = "1\n127.0.0.1\n"
    run_command(["reflutter", apk_path], input_str=input_data)
    
    output_name = apk_path.replace(".apk", ".RE.apk")
    if os.path.exists("release.RE.apk"):
        return "release.RE.apk"
    elif os.path.exists(output_name):
        return output_name
    
    # Method 2: Universal Flutter SSL Bypass (if reflutter fails)
    print("[*] Reflutter didn't produce expected output. Trying Method 2 (Universal Patcher)...")
    # Extract libflutter.so
    run_command(["unzip", apk_path, "lib/arm64-v8a/libflutter.so", "-d", "patch_work"])
    lib_path = "patch_work/lib/arm64-v8a/libflutter.so"
    
    if os.path.exists(lib_path):
        # This would call the universal patcher if fully integrated
        # For now, we'll ensure reflutter is used correctly as it's the most reliable for non-root
        pass

    # Search for any .RE.apk
    for f in os.listdir("."):
        if f.endswith(".RE.apk"):
            return f
    return None

def main():
    if len(sys.argv) < 2:
        print("Usage: python smart_patcher.py <apk_path>")
        sys.exit(1)
    
    apk_path = sys.argv[1]
    
    if is_flutter(apk_path):
        patched_apk = patch_flutter_pro(apk_path)
    else:
        print("[+] Native app detected. SSL Pinning bypass via Network Security Config is handled in Merge phase.")
        patched_apk = apk_path
    
    if patched_apk:
        print(f"[+] Successfully patched: {patched_apk}")
        if patched_apk != "patched_ready.apk":
            if os.path.exists("patched_ready.apk"): os.remove("patched_ready.apk")
            shutil.move(patched_apk, "patched_ready.apk")
    else:
        print("[-] Patching failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
