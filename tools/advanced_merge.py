import os
import sys
import subprocess
import shutil
import re

def run_command(command):
    print(f"[*] Executing: {' '.join(command)}")
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[-] Command failed: {result.stderr}")
    return result

def merge_apks(extracted_dir, output_apk):
    print(f"[+] Starting Pro Merge in {extracted_dir}")
    
    apks = [f for f in os.listdir(extracted_dir) if f.endswith(".apk")]
    base_apk = None
    config_apks = []
    
    # Identify base (the one with the manifest and code)
    for apk in apks:
        if "config" not in apk and "split" not in apk:
            base_apk = apk
            break
    if not base_apk:
        base_apk = apks[0]
        config_apks = apks[1:]
    else:
        config_apks = [a for a in apks if a != base_apk]

    print(f"[+] Base APK: {base_apk}")
    print(f"[+] Config APKs: {config_apks}")

    # Decompile base
    run_command(["apktool", "d", os.path.join(extracted_dir, base_apk), "-o", "base_decompiled", "-f"])
    
    # Merge contents from all configs
    for config in config_apks:
        config_path = os.path.join(extracted_dir, config)
        print(f"[*] Processing config: {config}")
        run_command(["apktool", "d", config_path, "-o", "temp_config", "-f"])
        
        # 1. Merge Libs (Architectures)
        if os.path.exists("temp_config/lib"):
            print(f"   [+] Merging libs...")
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
        
        # 2. Merge Assets
        if os.path.exists("temp_config/assets"):
            print(f"   [+] Merging assets...")
            if not os.path.exists("base_decompiled/assets"):
                os.makedirs("base_decompiled/assets")
            for item in os.listdir("temp_config/assets"):
                src_item = os.path.join("temp_config/assets", item)
                dst_item = os.path.join("base_decompiled/assets", item)
                if os.path.isdir(src_item):
                    if os.path.exists(dst_item):
                        # Merge subdirectories if they exist
                        for sub_item in os.listdir(src_item):
                            s = os.path.join(src_item, sub_item)
                            d = os.path.join(dst_item, sub_item)
                            if os.path.isdir(s):
                                if os.path.exists(d): shutil.rmtree(d)
                                shutil.copytree(s, d)
                            else:
                                shutil.copy2(s, d)
                    else:
                        shutil.copytree(src_item, dst_item)
                else:
                    shutil.copy2(src_item, dst_item)

        # 3. Merge Resources (res) - Carefully
        if os.path.exists("temp_config/res"):
            print(f"   [+] Merging resources...")
            for res_dir in os.listdir("temp_config/res"):
                src_res = os.path.join("temp_config/res", res_dir)
                dst_res = os.path.join("base_decompiled/res", res_dir)
                if not os.path.exists(dst_res):
                    shutil.copytree(src_res, dst_res)
                else:
                    for res_file in os.listdir(src_res):
                        shutil.copy2(os.path.join(src_res, res_file), os.path.join(dst_res, res_file))
        
        shutil.rmtree("temp_config")

    # --- PRO COMPATIBILITY & SECURITY BYPASS ---
    manifest_path = "base_decompiled/AndroidManifest.xml"
    if os.path.exists(manifest_path):
        print("[+] Patching AndroidManifest for compatibility & integrity bypass...")
        with open(manifest_path, "r") as f:
            content = f.read()
        
        # 1. Disable Split APK requirements
        content = content.replace('android:isSplitRequired="true"', 'android:isSplitRequired="false"')
        content = re.sub(r'<meta-data android:name="com.android.vending.splits.*?>', '', content)
        content = re.sub(r'<meta-data android:name="com.android.vending.derived.apk.*?>', '', content)
        
        # 2. Fix SDK Versions for wider compatibility
        # Ensure minSdk is reasonable (e.g., 21 or 24)
        content = re.sub(r'android:minSdkVersion="\d+"', 'android:minSdkVersion="24"', content)
        
        # 3. Enable Debugging & Network Trust
        if 'android:debuggable="false"' in content:
            content = content.replace('android:debuggable="false"', 'android:debuggable="true"')
        elif 'android:debuggable' not in content:
            content = content.replace('<application', '<application android:debuggable="true"')
        
        # 4. Allow cleartext traffic (for proxying)
        if 'android:usesCleartextTraffic="false"' in content:
            content = content.replace('android:usesCleartextTraffic="false"', 'android:usesCleartextTraffic="true"')
        elif 'android:usesCleartextTraffic' not in content:
            content = content.replace('<application', '<application android:usesCleartextTraffic="true"')

        with open(manifest_path, "w") as f:
            f.write(content)

    # Rebuild
    print("[+] Rebuilding final APK...")
    # Use -p to keep resources if possible, but for merging, full build is safer
    run_command(["apktool", "b", "base_decompiled", "-o", output_apk, "--use-aapt2"])
    
    if os.path.exists(output_apk):
        print(f"[+] Pro Merge complete: {output_apk}")
        return True
    return False

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python advanced_merge.py <extracted_dir> <output_apk>")
        sys.exit(1)
    merge_apks(sys.argv[1], sys.argv[2])
