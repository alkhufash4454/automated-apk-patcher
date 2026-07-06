import os
import sys
import subprocess
import shutil
import json

def run_command(command):
    print(f"[*] Executing: {' '.join(command)}")
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[-] Command failed: {result.stderr}")
    return result

def merge_apks(extracted_dir, output_apk):
    print(f"[+] Starting advanced merge in {extracted_dir}")
    
    # Identify base and config apks
    apks = [f for f in os.listdir(extracted_dir) if f.endswith(".apk")]
    base_apk = None
    config_apks = []
    
    for apk in apks:
        if "config" not in apk:
            base_apk = apk
        else:
            config_apks.append(apk)
    
    if not base_apk:
        base_apk = apks[0]
        config_apks = apks[1:]

    print(f"[+] Base APK: {base_apk}")
    print(f"[+] Config APKs: {config_apks}")

    # Decompile base
    run_command(["apktool", "d", os.path.join(extracted_dir, base_apk), "-o", "base_decompiled", "-f"])
    
    # Merge contents from configs
    for config in config_apks:
        config_path = os.path.join(extracted_dir, config)
        run_command(["apktool", "d", config_path, "-o", "temp_config", "-f"])
        
        # Merge libs
        if os.path.exists("temp_config/lib"):
            print(f"[+] Merging libs from {config}")
            if not os.path.exists("base_decompiled/lib"):
                os.makedirs("base_decompiled/lib")
            for arch in os.listdir("temp_config/lib"):
                src_arch = os.path.join("temp_config/lib", arch)
                dst_arch = os.path.join("base_decompiled/lib", arch)
                if not os.path.exists(dst_arch):
                    shutil.copytree(src_arch, dst_arch)
                else:
                    for lib in os.listdir(src_arch):
                        shutil.copy2(os.path.join(src_arch, lib), os.path.join(dst_arch, lib))
        
        # Merge assets
        if os.path.exists("temp_config/assets"):
            print(f"[+] Merging assets from {config}")
            if not os.path.exists("base_decompiled/assets"):
                os.makedirs("base_decompiled/assets")
            for item in os.listdir("temp_config/assets"):
                src_item = os.path.join("temp_config/assets", item)
                dst_item = os.path.join("base_decompiled/assets", item)
                if os.path.isdir(src_item):
                    if os.path.exists(dst_item):
                        shutil.rmtree(dst_item)
                    shutil.copytree(src_item, dst_item)
                else:
                    shutil.copy2(src_item, dst_item)
        
        shutil.rmtree("temp_config")

    # Fix Manifest (Remove split requirements)
    manifest_path = "base_decompiled/AndroidManifest.xml"
    if os.path.exists(manifest_path):
        with open(manifest_path, "r") as f:
            content = f.read()
        content = content.replace('android:isSplitRequired="true"', 'android:isSplitRequired="false"')
        # Remove split definitions
        import re
        content = re.sub(r'<meta-data android:name="com.android.vending.splits.*?>', '', content)
        with open(manifest_path, "w") as f:
            f.write(content)

    # Rebuild
    print("[+] Rebuilding merged APK...")
    run_command(["apktool", "b", "base_decompiled", "-o", output_apk, "--use-aapt2"])
    
    if os.path.exists(output_apk):
        print(f"[+] Merge complete: {output_apk}")
        return True
    return False

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python advanced_merge.py <extracted_dir> <output_apk>")
        sys.exit(1)
    merge_apks(sys.argv[1], sys.argv[2])
