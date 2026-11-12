# iOS on Samsung Galaxy A70 (SM-A705, a70q, SM6150) - Engineering Notes

Reference:
- `ios-s9`: Samsung Galaxy S9 (SM-G9600, SDM845, starqlte)
- `ios-sweet`: Xiaomi Redmi Note 10 Pro (SM7150, sweet)
- Device Tree: `dtb/a70q.dtb` and `dtb/a70q.dts` (Samsung A70Q Rev0.6, board-id 0x22 0x0e, msm-id 0x163 0x00)

---

## 1. Hardware Architecture & Facts (from a70q.dts)

| Component | Galaxy A70 (a70q, SM6150) | Galaxy S9 (starqlte, SDM845) | Comparison / Details |
|---|---|---|---|
| **SoC** | Qualcomm Snapdragon 675 (SM6150) | Snapdragon 845 (SDM845) | Kryo 460 vs Kryo 385 |
| **CPU Cluster** | 8 cores: 6x Cortex-A55 + 2x Cortex-A76 | 8 cores: 4x Cortex-A55 + 4x Cortex-A75 | 6 silver (0-5) + 2 gold (6-7) |
| **CPU Frequencies**| Little: 1.804 GHz, Big: 2.0 GHz | Little: 1.766 GHz, Big: 2.803 GHz | Clocks in `cpus` node |
| **PSCI** | PSCI 1.0 via SMC (`enable-method = "psci"`) | PSCI 1.0 via SMC | Core power control via CPU_ON |
| **Timer / Interrupts** | GICv3: GICD `0x17a00000`, GICR `0x17a60000` (stride `0x20000`), VTimer INTID 19 | GICD `0x17a00000`, GICR `0x17a60000`, VTimer INTID 19 | Identical GICv3 layout |
| **Watchdog** | `0x17c10000` (`wdt@17c10000`) | `0x17980000` (`wdt@17980000`) | A70 WDT base is 0x17c10000 |
| **RAM Total** | 6 GiB LPDDR4x | 4 GiB LPDDR4x | Bank 0: 2 GiB (`0x80000000`), Bank 1: ~3.95 GiB (`0x100000000`) |
| **RAM for iOS** | `0x100000000` + `0xfcb00000` (~3.95 GiB) | `0xa6000000` (~3.1 GiB with carveout holes) | A70 upper bank has ZERO carveout holes! |
| **Display Panel** | Samsung S6E3FC2 AMS670TA01 (6.7" Super AMOLED) | Samsung S6E3HA8 AMB577PX01 (5.8" Super AMOLED) | 1080x2400 FHD+ vs 1440x2960 WQHD+ |
| **Display Mode** | Command Mode (`dsi_cmd_mode`) | Command Mode (`dsi_cmd_mode`) | Both use TE line + DPU autorefresh |
| **Splash Buffer** | `0x9c000000`, size `0x00f00000` (15 MiB) | `0x9d400000`, size `0x02400000` (36 MiB) | Fits in a single 32MB L2 MMU block |
| **Storage (UFS)** | `0x01d84000` (UFSHCI 2.1) | `0x01d84000` (UFSHCI 2.1) | Identical controller address |
| **PMIC** | Qualcomm PM6150 + PM6150L | Qualcomm PM8998 | SPMI arbiter v5 |
| **Hardware Keys** | Power & Vol-: PM6150 PON (`0x800`/`0x810`)<br>Vol+: PM6150L GPIO8 (SID 4/5, phandle `0x294`) | Power & Vol-: PM8998 PON<br>Vol+: PM8998 GPIO6 | Vol+ on PM6150L GPIO8 |
| **Touchscreen** | Imagis IST40xx (`touchscreen@50` on GENI I2C1 `0x884000`, IRQ GPIO 89) | Samsung S6SY761 (`sec_ts` on I2C SE11 `0xa8c000`) | I2C address 0x50 on 0x884000 |
| **Bootloader** | Samsung ABL (boot.img v0 with Image.gz + DTB appended) | Samsung ABL (boot.img v0 with Image.gz + DTB appended) | Flash via TWRP `dd` or Odin |

---

## 2. Inconsistencies Ported from S9 to A70

1. **Memory Map (`tools/mkadt.py` & `a70/tools/mkadt.py`):**
   - **S9:** S9 had only 4 GB total RAM (`0x80000000 + 0xfe1c0000`). To give iOS > 1.95 GB, it spanned across `0xa6000000` and excluded protected carveout holes (IPA, SPSS).
   - **A70:** Galaxy A70 has 6 GB of RAM. The FDT memory node defines:
     `<0x00 0x80000000 0x00 0x80000000 0x01 0x00 0x00 0xfcb00000>`
     Every single Qualcomm carveout (hyp, xbl, smem, modem, qseecom, tima, ramoops) is located in the low bank (< 4 GB).
     The upper bank at `0x100000000` with size `0xfcb00000` (~3.95 GiB) is completely contiguous, pure DRAM.
     Configured `PHYS_BASE = 0x100000000`, `MEM_SIZE = 0xfcb00000`, and `panic_base = 0x1fca00000`.

2. **Framebuffer & Display Engine (`a70/shim/fb.h`):**
   - **S9:** Base `0x9d400000`, 1440x2960, stride 5760.
   - **A70:** Base `0x9c000000` (`cont_splash_region@9c000000`), 1080x2400, stride 4320. Size `0x00f00000` (15 MiB).

3. **Watchdog APSS (`a70/shim/plat.c`):**
   - **S9:** `wdt@17980000`.
   - **A70:** `wdt@17c10000` (from `a70q.dts`).

4. **SMP Topology & Core Frequencies:**
   - **S9:** 4 silver (A55 @ 1.766 GHz) + 4 gold (A75 @ 2.803 GHz). Threshold `core >= 4`.
   - **A70:** 6 silver (A55 @ 1.804 GHz) + 2 gold (A76 @ 2.0 GHz). Threshold `core >= 6`.

5. **Console File Names on Windows:**
   - **S9:** Files named `con.c` and `con.h` caused Git checkout failures on Windows due to DOS reserved device names (`CON`).
   - **A70:** Cleanly renamed to `console.c` and `console.h`.

6. **MMU 16K Page Table (`a70/shim/mmu.c`):**
   - **S9:** Splash at `0x9d400000` spilled past the 32MB L2 boundary into TIMA at `0x9f800000`.
   - **A70:** Splash at `0x9c000000` (15 MB) fits completely inside the single 32MB block `0x9c000000` - `0x9e000000`, avoiding any collision.

---

## 3. Ported Files Log

The following files have been created and ported for the Samsung Galaxy A70:
1. `tools/mkadt.py`: Ported ADT generator to A70 (SM6150, 6+2 cores, 1080x2400, 0x9c000000 FB, 0x100000000 DRAM).
2. `a70/tools/mkadt.py`: Standalone A70 ADT generator.
3. `a70/tools/adt.py`: ADT binary serialization helper.
4. `a70/tools/mkpayload.py`: Packs XNU kernel + A70 ADT + boot arguments into boot payload.
5. `a70/tools/extract-stock-dtbs.py`: Unpacks stock DTBs from boot.img.
6. `a70/tools/flash-twrp.sh`: Flashes boot image directly via TWRP with sha256 readback verification.
7. `a70/tools/flash-userdata.sh`: Flashes iOS root image to userdata via TWRP.
8. `a70/tools/twrp-check.sh`: Verifies boot partition against built image.
9. `a70/tools/sweet-log-pull.sh`: Extracts persistent kernel logs from recovery.
10. `a70/tools/sweet-log.py`: Decodes raw persistent log ring.
11. `a70/shim/hw.h`: Register access primitives and barrier macros.
12. `a70/shim/fb.h`: Framebuffer definitions ported to 1080x2400 AMOLED at `0x9c000000`.
13. `a70/shim/fb.c`: Framebuffer drawing routines.
14. `a70/shim/font.h`: 8x16 bitmap console font.
15. `a70/shim/console.h`: Console header (resolves Windows `CON` reserved name).
16. `a70/shim/console.c`: Console text renderer scaled for 1080x2400 panel.
17. `a70/shim/plat.h`: Platform functions (SMC, timer, watchdog, reboot).
18. `a70/shim/plat.c`: Platform routines ported to A70 watchdog at `0x17c10000`.
19. `a70/shim/mmu.h`: 16K granule MMU header.
20. `a70/shim/mmu.c`: EL1 stage-1 MMU setup with 15MB splash at `0x9c000000`.
21. `a70/shim/mdss.h`: DPU SDE display controller header.
22. `a70/shim/mdss.c`: DPU SDE hardware probe on SM6150 at `0x0ae00000`.
23. `a70/shim/ufs.h`: UFS probe header.
24. `a70/shim/ufs.c`: UFS 2.1 read-only probe on A70 at `0x01d84000`.
25. `a70/shim/ramlog.h`: Flight recorder in ramoops header.
26. `a70/shim/ramlog.c`: Flight recorder at `0xa1340000` (A70 ramoops console zone).
27. `a70/shim/fdt.h` & `fdt.c`: Device tree parser for ABL boot arguments and chosen nodes.
28. `a70/shim/lib.c`: String and memory support functions.
29. `a70/shim/shim.ld`: Linker script.
30. `a70/shim/start.S`: ARM64 entry point and exception vectors for Samsung ABL.
31. `a70/shim/loader.h` & `loader.c`: XNU Mach-O loader and boot_args builder.
32. `a70/shim/screen.h` & `screen.c`: Milestone 1 visual diagnostic screen scaled for 1080x2400.
33. `a70/shim/m1.c`: Milestone 1 shim (ABL continuous splash probe and screen test).
34. `a70/shim/m2.c`: Milestone 2 shim (6+2 CPU SMP via PSCI, GICv3 interrupts, 0x17c10000 watchdog).
35. `a70/shim/m3.c`: Milestone 3 shim (UFS read-only probe + 16K MMU test).
36. `a70/shim/m4.c`: Milestone 4 shim (XNU kernel launcher).
37. `a70/build.sh`: Automated build script packaging `boot.img` for Samsung Galaxy A70 ABL.
38. `dtb/a70q.dtb` & `dtb/a70q.dts`: Extracted and verified Samsung Galaxy A70 device tree files.
