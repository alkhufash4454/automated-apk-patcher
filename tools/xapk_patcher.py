import os
import sys
import subprocess
import shutil
import json

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

def patch_xapk(xapk_path, output_xapk):
    print(f"[+] Starting XAPK Patching: {xapk_path}")
    
    # 1. Extract XAPK
    extract_dir = "xapk_extracted"
    if os.path.exists(extract_dir): shutil.rmtree(extract_dir)
    os.makedirs(extract_dir)
    run_command(["unzip", xapk_path, "-d", extract_dir])
    
    # 2. Find Base and Configs
    apks = [f for f in os.listdir(extract_dir) if f.endswith(".apk")]
    base_apk = None
    for apk in apks:
        # Usually the largest or the one without 'config' in name
        if "config" not in apk and "split" not in apk:
            base_apk = apk
            break
    if not base_apk: base_apk = apks[0]
    
    print(f"[+] Base APK found: {base_apk}")
    
    # 3. Patch Base APK (SSL Bypass / Flutter)
    base_path = os.path.join(extract_dir, base_apk)
    # We use reflutter on the base apk
    print("[*] Patching Base APK with reflutter...")
    input_data = "1\n127.0.0.1\n"
    run_command(["reflutter", base_path], input_str=input_data)
    
    # Find patched apk
    patched_base = None
    for f in os.listdir("."):
        if f.endswith(".RE.apk"):
            patched_base = f
            break
    
    if not patched_base:
        # Check inside extract_dir if reflutter worked there
        for f in os.listdir(extract_dir):
            if f.endswith(".RE.apk"):
                patched_base = os.path.join(extract_dir, f)
                break

    if patched_base:
        print(f"[+] Patched Base APK: {patched_base}")
        # Replace original base with patched one (keeping original name is crucial for XAPK)
        shutil.move(patched_base, base_path)
    else:
        print("[-] Warning: Reflutter didn't produce a patched file. Proceeding with original.")

    # 4. Resign ALL APKs (Crucial for XAPK consistency)
    print("[*] Resigning all APKs in the package...")
    signer_jar = "tools/uber-apk-signer.jar"
    run_command(["java", "-jar", signer_jar, "--allowResign", "-a", extract_dir, "--out", "resigned_apks"])
    
    # 5. Reassemble XAPK
    # Move resigned apks back to extract_dir with their original names
    for f in os.listdir("resigned_apks"):
        if f.endswith(".apk"):
            # uber-apk-signer adds suffixes, we need to map them back
            original_name = f.split("-aligned")[0] + ".apk"
            # If the mapping is complex, we just take the first part
            # For simplicity, we'll try to match the prefix
            for target in apks:
                if target.startswith(f.split("-")[0]):
                    shutil.move(os.path.join("resigned_apks", f), os.path.join(extract_dir, target))
                    break

    # 6. Zip back to XAPK
    print(f"[*] Reassembling XAPK into {output_xapk}...")
    if os.path.exists(output_xapk): os.remove(output_xapk)
    os.chdir(extract_dir)
    run_command(["zip", "-r", f"../{output_xapk}", "."])
    os.chdir("..")
    
    print(f"[+] XAPK Patching Complete: {output_xapk}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python xapk_patcher.py <input_xapk> <output_xapk>")
        sys.exit(1)
    patch_xapk(sys.argv[1], sys.argv[2])
