import subprocess
import glob
import os
import sys

patches = sorted(glob.glob("xnu/patches/*.patch"))

print(f"Total patches to test: {len(patches)}")

clean_dir = os.path.abspath("clean-xnu")

failed = []
applied = []

for patch in patches:
    patch_path = os.path.abspath(patch)
    patch_name = os.path.basename(patch)
    
    # Try git apply --check first
    # Note: git apply requires unix style path or relative path
    cmd = ["git", "-C", clean_dir, "apply", "--ignore-whitespace", patch_path]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode == 0:
        applied.append(patch_name)
        print(f"OK: {patch_name}")
    else:
        failed.append((patch_name, res.stderr.strip()))
        print(f"FAIL: {patch_name}")
        print(f"  Error: {res.stderr.strip()[:300]}")

print("\n=== SUMMARY ===")
print(f"Applied: {len(applied)}")
print(f"Failed: {len(failed)}")
if failed:
    print("\nFailed patches:")
    for name, err in failed:
        print(f"- {name}: {err.splitlines()[-1] if err else 'unknown error'}")
