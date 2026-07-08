import os
import sys
import subprocess
import shutil
import re

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

def patch_manifest(manifest_path):
    if not os.path.exists(manifest_path): return
    print("[*] Patching AndroidManifest for Integrity Bypass...")
    with open(manifest_path, "r") as f:
        content = f.read()
    
    # 1. Remove installer verification
    content = re.sub(r'android:requiredInstallerPackage=".*?"', '', content)
    
    # 2. Allow any installer
    if 'android:installLocation' not in content:
        content = content.replace('<manifest', '<manifest android:installLocation="auto"')
    
    # 3. Disable Play Integrity related meta-data
    content = re.sub(r'<meta-data android:name="com.google.android.play.integrity..*?/>', '', content)
    
    # 4. Enable debugging and cleartext
    if 'android:debuggable="false"' in content:
        content = content.replace('android:debuggable="false"', 'android:debuggable="true"')
    elif 'android:debuggable' not in content:
        content = content.replace('<application', '<application android:debuggable="true"')
    
    if 'android:usesCleartextTraffic="false"' in content:
        content = content.replace('android:usesCleartextTraffic="false"', 'android:usesCleartextTraffic="true"')
    elif 'android:usesCleartextTraffic' not in content:
        content = content.replace('<application', '<application android:usesCleartextTraffic="true"')

    with open(manifest_path, "w") as f:
        f.write(content)

def patch_xapk(xapk_path, output_xapk):
    print(f"[+] Starting Pro XAPK Patching (Integrity Bypass): {xapk_path}")
    
    extract_dir = "xapk_extracted"
    if os.path.exists(extract_dir): shutil.rmtree(extract_dir)
    os.makedirs(extract_dir)
    run_command(["unzip", xapk_path, "-d", extract_dir])
    
    apks = [f for f in os.listdir(extract_dir) if f.endswith(".apk")]
    base_apk = None
    for apk in apks:
        if "config" not in apk and "split" not in apk:
            base_apk = apk
            break
    if not base_apk: base_apk = apks[0]
    
    base_path = os.path.join(extract_dir, base_apk)
    
    # --- DECOMPILE & PATCH MANIFEST & SMALI ---
    print(f"[*] Decompiling {base_apk} for deep patching...")
    run_command(["apktool", "d", base_path, "-o", "base_work", "-f"])
    
    patch_manifest("base_work/AndroidManifest.xml")
    
    # REBUILD BASE
    print("[*] Rebuilding patched Base APK...")
    run_command(["apktool", "b", "base_work", "-o", "base_patched_temp.apk", "--use-aapt2"])
    
    if os.path.exists("base_patched_temp.apk"):
        # Now apply Flutter SSL Bypass on the already manifest-patched APK
        print("[*] Applying Flutter SSL Bypass...")
        input_data = "1\n127.0.0.1\n"
        run_command(["reflutter", "base_patched_temp.apk"], input_str=input_data)
        
        patched_final = None
        for f in os.listdir("."):
            if f.endswith(".RE.apk"):
                patched_final = f
                break
        
        if patched_final:
            shutil.move(patched_final, base_path)
            print(f"[+] Final Patched Base: {base_path}")
        else:
            shutil.move("base_patched_temp.apk", base_path)
    
    # --- RESIGN ALL ---
    print("[*] Resigning all components...")
    signer_jar = "tools/uber-apk-signer.jar"
    if os.path.exists("resigned_apks"): shutil.rmtree("resigned_apks")
    run_command(["java", "-jar", signer_jar, "--allowResign", "-a", extract_dir, "--out", "resigned_apks"])
    
    # Map back
    for f in os.listdir("resigned_apks"):
        if f.endswith(".apk"):
            prefix = f.split("-")[0]
            for target in apks:
                if target.startswith(prefix):
                    shutil.move(os.path.join("resigned_apks", f), os.path.join(extract_dir, target))
                    break

    # --- ZIP XAPK ---
    print(f"[*] Finalizing XAPK: {output_xapk}")
    if os.path.exists(output_xapk): os.remove(output_xapk)
    os.chdir(extract_dir)
    run_command(["zip", "-r", f"../{output_xapk}", "."])
    os.chdir("..")
    
    print(f"[+] Integrity-Bypassed XAPK Complete: {output_xapk}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python xapk_patcher.py <input_xapk> <output_xapk>")
        sys.exit(1)
    patch_xapk(sys.argv[1], sys.argv[2])
