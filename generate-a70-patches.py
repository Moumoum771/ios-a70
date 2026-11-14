import subprocess
import os
import sys

REPO_ROOT = os.path.abspath(".")
TEST_XNU = os.path.abspath("test-xnu")
PATCH_DIR = os.path.abspath("xnu/patches")

def run(cmd, cwd=TEST_XNU, input_data=None):
    res = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, input=input_data)
    if res.returncode != 0:
        print(f"FAILED: {' '.join(cmd)}")
        print(res.stderr)
        raise RuntimeError(res.stderr)
    return res.stdout

def get_patch_from_commit(patch_name, commit="646570b"):
    cmd = ["git", "show", f"{commit}:xnu/patches/{patch_name}"]
    res = subprocess.run(cmd, cwd=REPO_ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Could not get {patch_name} from {commit}")
    return res.stdout

def apply_patch_string(patch_str):
    run(["git", "apply", "--whitespace=nowarn"], input_data=patch_str)

def save_patch_file(patch_name):
    diff = run(["git", "diff", "HEAD"])
    out_path = os.path.join(PATCH_DIR, patch_name)
    with open(out_path, "w", newline="\n") as f:
        f.write(diff)
    print(f"Generated {patch_name} ({len(diff)} bytes)")

def commit_step(msg):
    run(["git", "add", "-A"])
    run(["git", "commit", "-m", msg])

print("Resetting test-xnu to Pure 0081 (7c2db94)...")
run(["git", "reset", "--hard", "7c2db94"])
run(["git", "clean", "-fd"])

# ==========================================
# Patch 0082
# ==========================================
print("\n--- Patch 0082 ---")
path = os.path.join(TEST_XNU, "bsd/dev/sweet_keys.c")
with open(path, "r") as f: c = f.read()
c = c.replace("sweet_keys_init(void)\n{\n\tint enabled = 1;",
              "sweet_keys_init(void)\n{\n\tint enabled = 1;\t/* Galaxy A70: PM6150 / PM6150L layout supported */")
with open(path, "w") as f: f.write(c)

path = os.path.join(TEST_XNU, "bsd/dev/sweet_touch.c")
with open(path, "r") as f: c = f.read()
c = c.replace("sweet_touch_init(void)\n{\n\tint enabled = 1;",
              "sweet_touch_init(void)\n{\n\t/*\n\t * Galaxy A70: touch init enabled for IST40xx / Sec-TS on SM6150.\n\t */\n\tint enabled = 1;")
with open(path, "w") as f: f.write(c)

path = os.path.join(TEST_XNU, "bsd/dev/sweet_usb.c")
with open(path, "r") as f: c = f.read()
c = c.replace("sweet_usb_probe(void)\n{\n\tint enabled = 1;",
              "sweet_usb_probe(void)\n{\n\tint enabled = 1;\t/* Galaxy A70: DWC3 on SM6150 */")
with open(path, "w") as f: f.write(c)

path = os.path.join(TEST_XNU, "osfmk/arm64/arm_vm_init.c")
with open(path, "r") as f: c = f.read()
c = c.replace("\tsweet_early_relocate(SWEET_EARLY_FB_VA);\n#endif",
              "\t/* Galaxy A70: splash at 0x9c000000, 32MB aligned (offset 0 into L2 block). */\n\tsweet_early_relocate(SWEET_EARLY_FB_VA + (0x9c000000ULL & (ARM_TT_L2_SIZE - 1)));\n#endif")
with open(path, "w") as f: f.write(c)

path = os.path.join(TEST_XNU, "osfmk/arm64/start.s")
with open(path, "r") as f: c = f.read()
c = c.replace("\t/* Stage 0: white 64x32 band, no stack or page tables needed. */\n\tMOV64\tx0, (0x9c000000 + 2368 * 4320)",
              "\t/* Stage 0: white 64x32 band, no stack or page tables needed. */\n\t/* Galaxy A70: splash at 0x9c000000, 1080x2400, stride 4320. */\n\tMOV64\tx0, (0x9c000000 + 2368 * 4320)")
c = c.replace("\t * V=P L2 page is bootstrap_pagetables + 2*PGBYTES.\n\t */",
              "\t * V=P L2 page is bootstrap_pagetables + 2*PGBYTES.\n\t * Galaxy A70: splash at 0x9c000000, size 0x00f00000 (15 MiB),\n\t * fits completely within a single 32MB L2 block (0x9c000000-0x9e000000).\n\t */")
with open(path, "w") as f: f.write(c)

path = os.path.join(TEST_XNU, "osfmk/arm64/sweet_early.c")
with open(path, "r") as f: c = f.read()
c = c.replace("static volatile uint32_t *early_fb = (volatile uint32_t *)(uintptr_t)0x9c000000;",
              "/*\n * Galaxy A70: splash at 0x9c000000, 1080x2400, stride 4320.\n * Fits completely in 32MB L2 block 0x9c000000-0x9e000000.\n */\nstatic volatile uint32_t *early_fb = (volatile uint32_t *)(uintptr_t)0x9c000000;")
with open(path, "w") as f: f.write(c)

save_patch_file("0082-s9-galaxy-s9-bringup.patch")
commit_step("0082 A70 bringup")

# ==========================================
# Patch 0083
# ==========================================
print("\n--- Patch 0083 ---")
p0083 = get_patch_from_commit("0083-s9-iphone-x-canvas-on-larger-panel.patch")
apply_patch_string(p0083)
save_patch_file("0083-s9-iphone-x-canvas-on-larger-panel.patch")
commit_step("0083 iPhone X canvas on larger panel")

# ==========================================
# Patch 0084
# ==========================================
print("\n--- Patch 0084 ---")
path = os.path.join(TEST_XNU, "bsd/dev/sweet_keys.c")
with open(path, "r") as f: c = f.read()
c = c.replace("#define KEYS_GPIO_RT     0xc110u",
              "/* Galaxy A70: volume-up is PM6150L GPIO8 (SID 4, peripheral 0xc7, PPID 0x4c7) */\n#define KEYS_GPIO_RT     0xc710u")
c = c.replace("sweet_keys_init(void)\n{\n\tint enabled = 1;\t/* Galaxy A70: PM6150 / PM6150L layout supported */",
              "sweet_keys_init(void)\n{\n\tint enabled = 1;\t/* Galaxy A70: PM6150 PON (SID 0) + PM6150L GPIO8 (SID 4) */")
c = c.replace("keys_gpio_apid = keys_find_apid(0x4c1, count);",
              "keys_gpio_apid = keys_find_apid(0x4c7, count);")
c = c.replace("bool mok = keys_read(keys_gpio_apid, 0xc140, &mode);",
              "bool mok = keys_read(keys_gpio_apid, 0xc740, &mode);")
c = c.replace("bool eok = keys_read(keys_gpio_apid, 0xc146, &en);",
              "bool eok = keys_read(keys_gpio_apid, 0xc746, &en);")
c = c.replace("bool sok = keys_read(keys_gpio_apid, 0xc105, &subtype);",
              "bool sok = keys_read(keys_gpio_apid, 0xc705, &subtype);")
c = c.replace("gpio4-apid=%u", "gpio8-apid=%u")
with open(path, "w") as f: f.write(c)

path = os.path.join(TEST_XNU, "iokit/Kernel/arm/SweetFramebuffer.cpp")
with open(path, "r") as f: c = f.read()
target_fb = """\t\t\tsweet_console_muted = 1;
\t\t}
\t}"""
replace_fb = """\t\t\tsweet_console_muted = 1;
\t\t\t/*
\t\t\t * Galaxy A70: clear console borders if canvas is smaller than panel
\t\t\t */
\t\t\tif (fOffX < 0 || fOffY < 0) {
\t\t\t\tfor (uint32_t y = 0; y < fHeight; y++) {
\t\t\t\t\tbzero((void *)(fPixels + (uint64_t)y * fRowBytes), (size_t)fWidth * 4);
\t\t\t\t}
\t\t\t}
\t\t}
\t}"""
assert target_fb in c, "SweetFramebuffer.cpp target not found in 0084"
c = c.replace(target_fb, replace_fb, 1)
with open(path, "w") as f: f.write(c)

save_patch_file("0084-s9-keys-and-clean-borders.patch")
commit_step("0084 Keys and clean borders")

# ==========================================
# Patch 0085
# ==========================================
print("\n--- Patch 0085 ---")
p0085 = get_patch_from_commit("0085-s9-sec-ts-touch.patch")
apply_patch_string(p0085)
save_patch_file("0085-s9-sec-ts-touch.patch")
commit_step("0085 sec-ts touch")

# ==========================================
# Patch 0086
# ==========================================
print("\n--- Patch 0086 ---")
p0086 = get_patch_from_commit("0086-s9-scale-canvas-to-panel.patch")
apply_patch_string(p0086)
save_patch_file("0086-s9-scale-canvas-to-panel.patch")
commit_step("0086 Scale canvas to panel")

# ==========================================
# Patch 0087
# ==========================================
print("\n--- Patch 0087 ---")
p0087 = get_patch_from_commit("0087-s9-stretch-canvas-by-default.patch")
apply_patch_string(p0087)
save_patch_file("0087-s9-stretch-canvas-by-default.patch")
commit_step("0087 Stretch canvas by default")

# ==========================================
# Patch 0088
# ==========================================
print("\n--- Patch 0088 ---")
p0088 = get_patch_from_commit("0088-s9-sec-ts-bitbang-touch.patch")
path = os.path.join(TEST_XNU, "bsd/dev/sweet_touch.c")
with open(path, "r") as f: c = f.read()
a70_touch_str = """\t/*
\t * Galaxy A70: touch init enabled for IST40xx / Sec-TS on SM6150.
\t */
\tint enabled = 1;"""
s9_touch_str = """\t/*
\t * Galaxy S9: off unless asked. This is the Redmi's Goodix GT9896 path and
\t * it votes RPMh "ldoc11" to 3.2 V, a rail that means something else on SDM845.
\t */
\tint enabled = 0;"""
assert a70_touch_str in c, "A70 touch string not found in sweet_touch.c"
c = c.replace(a70_touch_str, s9_touch_str)
with open(path, "w") as f: f.write(c)

apply_patch_string(p0088)

with open(path, "r") as f: c = f.read()
c = c.replace("/* Galaxy S9: off unless asked (boot-arg sweettouch=1). */\n\tint enabled = 0;",
              "/* Galaxy A70: touch init enabled for IST40xx / Sec-TS on SM6150. */\n\tint enabled = 1;")
with open(path, "w") as f: f.write(c)

save_patch_file("0088-s9-sec-ts-bitbang-touch.patch")
commit_step("0088 sec-ts bitbang touch")

# ==========================================
# Patch 0089
# ==========================================
print("\n--- Patch 0089 ---")
p0089 = get_patch_from_commit("0089-s9-cpu-clocks-and-cached-panel.patch")
apply_patch_string(p0089)
path = os.path.join(TEST_XNU, "iokit/Kernel/arm/SweetCPU.cpp")
with open(path, "r") as f: c = f.read()
c = c.replace("uint32_t on = 1, gold_mhz = 2649;",
              "uint32_t on = 0, gold_mhz = 2000;\n\t/* On SM6150 (A70), keep ABL clocks by default unless sweetcpu=1 explicitly requested */")
with open(path, "w") as f: f.write(c)

save_patch_file("0089-s9-cpu-clocks-and-cached-panel.patch")
commit_step("0089 CPU clocks and cached panel")

# ==========================================
# Patch 0090
# ==========================================
print("\n--- Patch 0090 ---")
p0090 = get_patch_from_commit("0090-s9-usb-cold-start-jailbreak-recovery-reboot.patch")
apply_patch_string(p0090)
path = os.path.join(TEST_XNU, "bsd/kern/sweet_amfi.c")
with open(path, "r") as f: c = f.read()
c = c.replace("#define SP_IMEM_PA              0x146bf000u", "#define SP_IMEM_PA              0x146aa000u")
with open(path, "w") as f: f.write(c)

path = os.path.join(TEST_XNU, "bsd/dev/sweet_usb.c")
with open(path, "r") as f: c = f.read()
c = c.replace("#define S9_RSC_PA               0x179e0000u", "#define S9_RSC_PA               0x18220000u")
c = c.replace("#define S9_TCS_PA               0x179e0d00u", "#define S9_TCS_PA               0x18220d00u")
with open(path, "w") as f: f.write(c)

save_patch_file("0090-s9-usb-cold-start-jailbreak-recovery-reboot.patch")
commit_step("0090 USB cold start jailbreak recovery reboot")

# ==========================================
# Patch 0091
# ==========================================
print("\n--- Patch 0091 ---")
p0091 = get_patch_from_commit("0091-s9-ram-3gb-exclude-carveout-holes.patch")
apply_patch_string(p0091)
save_patch_file("0091-s9-ram-3gb-exclude-carveout-holes.patch")
commit_step("0091 RAM 3GB exclude carveout holes")

# ==========================================
# Patch 0092
# ==========================================
print("\n--- Patch 0092 ---")
p0092 = get_patch_from_commit("0092-s9-perf-fast-cores-aks-wrap-vsync-rate.patch")
apply_patch_string(p0092)
path = os.path.join(TEST_XNU, "osfmk/kern/sched_prim.c")
with open(path, "r") as f: c = f.read()
c = c.replace("sweetfast=MASK names the fast cores (default 0xf0, 0 = stock behaviour):",
              "sweetfast=MASK names the fast cores (default 0xc0, 0 = stock behaviour):")
c = c.replace("static cpumap_t sweet_fast_map = 0xf0;",
              "static cpumap_t sweet_fast_map = 0xc0;")
with open(path, "w") as f: f.write(c)

save_patch_file("0092-s9-perf-fast-cores-aks-wrap-vsync-rate.patch")
commit_step("0092 Perf fast cores aks wrap vsync rate")

# ==========================================
# Patch 0093
# ==========================================
print("\n--- Patch 0093 ---")
p0093 = get_patch_from_commit("0093-s9-canvas-from-adt-fast-row-dup-fps.patch")
apply_patch_string(p0093)
save_patch_file("0093-s9-canvas-from-adt-fast-row-dup-fps.patch")
commit_step("0093 Canvas from ADT fast row dup fps")

# ==========================================
# Patch 0094
# ==========================================
print("\n--- Patch 0094 ---")
p0094 = get_patch_from_commit("0094-s9-touch-thread-on-slow-core.patch")
apply_patch_string(p0094)
save_patch_file("0094-s9-touch-thread-on-slow-core.patch")
commit_step("0094 Touch thread on slow core")

# ==========================================
# Patch 0095
# ==========================================
print("\n--- Patch 0095 ---")
p0095 = get_patch_from_commit("0095-s9-panel-60hz-autorefresh-every-te.patch")
apply_patch_string(p0095)
save_patch_file("0095-s9-panel-60hz-autorefresh-every-te.patch")
commit_step("0095 Panel 60hz autorefresh every te")

# ==========================================
# Patch 0096
# ==========================================
print("\n--- Patch 0096 ---")
p0096 = get_patch_from_commit("0096-s9-zero-copy-scanout-swapwait-dirty-rows.patch")
apply_patch_string(p0096)
path = os.path.join(TEST_XNU, "iokit/Kernel/arm/SweetFramebuffer.cpp")
with open(path, "r") as f: c = f.read()
c = c.replace("#define S9_SPLASH_PA            0x9d400000ULL   /* cont_splash_region, 36 MiB; TIMA follows */\n#define S9_SPLASH_END           0x9f800000ULL\n#define S9_FBCON_SIZE           0x1100000ULL    /* the panel buffer (mkadt.py FB_SIZE) */",
              "#define S9_SPLASH_PA            0x9c000000ULL   /* A70 cont_splash_region, 15 MiB */\n#define S9_SPLASH_END           0x9cf00000ULL\n#define S9_FBCON_SIZE           0x00a00000ULL    /* panel buffer 1080x2400x4 */")
c = c.replace("bool ok = fPhys == S9_SPLASH_PA && fWidth == 1440 && fHeight == 2960 && (fLogicalW & 1) == 0;",
              "bool ok = fPhys == S9_SPLASH_PA && fWidth == 1080 && fHeight == 2400 && (fLogicalW & 1) == 0;")
with open(path, "w") as f: f.write(c)

save_patch_file("0096-s9-zero-copy-scanout-swapwait-dirty-rows.patch")
commit_step("0096 Zero copy scanout swapwait dirty rows")

# ==========================================
# Patch 0097
# ==========================================
print("\n--- Patch 0097 ---")
p0097 = get_patch_from_commit("0097-s9-swapwait-poll-fullclean-underruns-gesture.patch")
# Adjust context for S9_SPLASH_PA
old_ctx = """ #define S9_SPLASH_PA            0x9d400000ULL   /* cont_splash_region, 36 MiB; TIMA follows */
 #define S9_SPLASH_END           0x9f800000ULL
 #define S9_FBCON_SIZE           0x1100000ULL    /* the panel buffer (mkadt.py FB_SIZE) */"""
new_ctx = """ #define S9_SPLASH_PA            0x9c000000ULL   /* A70 cont_splash_region, 15 MiB */
 #define S9_SPLASH_END           0x9cf00000ULL
 #define S9_FBCON_SIZE           0x00a00000ULL    /* panel buffer 1080x2400x4 */"""
assert old_ctx in p0097, "Context not found in p0097"
p0097 = p0097.replace(old_ctx, new_ctx)
apply_patch_string(p0097)
save_patch_file("0097-s9-swapwait-poll-fullclean-underruns-gesture.patch")
commit_step("0097 Swapwait poll fullclean underruns gesture")

# ==========================================
# Patch 0098
# ==========================================
print("\n--- Patch 0098 ---")
p0098 = get_patch_from_commit("0098-s9-parallelism-fastmap-memvote-knobs-fb-threads-a55.patch")
p0098 = p0098.replace("-static cpumap_t sweet_fast_map = 0xf0;", "-static cpumap_t sweet_fast_map = 0xc0;")
p0098 = p0098.replace("cpumap_t sweet_fast_map = 0xf0;         /* also sysctl kern.sweetfast (bsd/dev/sweet_touch.c) */",
                      "cpumap_t sweet_fast_map = 0xc0;         /* also sysctl kern.sweetfast (A70: cores 6-7) */")
apply_patch_string(p0098)
save_patch_file("0098-s9-parallelism-fastmap-memvote-knobs-fb-threads-a55.patch")
commit_step("0098 Parallelism fastmap memvote knobs fb threads a55")

# ==========================================
# Patch 0099
# ==========================================
print("\n--- Patch 0099 ---")
p0099 = get_patch_from_commit("0099-s9-battery-max77705-idle-l1-surface-map-dirty-stats.patch")
apply_patch_string(p0099)
save_patch_file("0099-s9-battery-max77705-idle-l1-surface-map-dirty-stats.patch")
commit_step("0099 Battery max77705 idle L1 surface map dirty stats")

# ==========================================
# Patch 0100
# ==========================================
print("\n--- Patch 0100 ---")
p0100 = get_patch_from_commit("0100-s9-battery-watchdog-adapter-thread-names.patch")
apply_patch_string(p0100)
save_patch_file("0100-s9-battery-watchdog-adapter-thread-names.patch")
commit_step("0100 Battery watchdog adapter thread names")

# ==========================================
# Patch 0101
# ==========================================
print("\n--- Patch 0101 ---")
p0101 = get_patch_from_commit("0101-s9-cpu-freq-sysctl.patch")
old_line = " \tuint32_t on = 1, gold_mhz = 2649;"
new_line = " \tuint32_t on = 0, gold_mhz = 2000;\n \t/* On SM6150 (A70), keep ABL clocks by default unless sweetcpu=1 explicitly requested */"
assert old_line in p0101, "old_line not found in p0101"
p0101 = p0101.replace("@@ -178,15 +217,18 @@", "@@ -178,16 +217,19 @@")
p0101 = p0101.replace(old_line, new_line)
apply_patch_string(p0101)
save_patch_file("0101-s9-cpu-freq-sysctl.patch")
commit_step("0101 CPU freq sysctl")

print("\nSUCCESS! ALL 20 PATCHES GENERATED AND COMMITTED!")
