/*
 * Samsung Galaxy A70 (SM6150) milestone 4: boot XNU. The ramdisk of the boot
 * image holds the SWEETXNU payload (tools/mkpayload.py: kernel + ADT + boot-args);
 * loader.c plays iBoot and jumps to it with the MMU off. The APSS watchdog stays off:
 * XNU does not feed it.
 */
#include <stdint.h>
#include "hw.h"
#include "fb.h"
#include "console.h"
#include "loader.h"
#include "plat.h"

#define RUN_SECONDS	90

static const char *stage;	/* set at runtime: no absolute pointers in data */

void exc_handler(uint64_t slot, uint64_t *regs)
{
	panic_screen(stage, slot, regs);
}

void shim_main(uint64_t dtb)
{
	/* A70: 0x9c000000, 1080x2400, stride 4320 */
	fb_default();
	con_clear(GREY);
	con_title("SHIM M4 (A70): XNU");
	con_hex2("SHIM", "dtb=", dtb, "img=", (uint32_t)(uintptr_t)shim_main);

	stage = "loader";
	const char *why = loader_boot(dtb);	/* returns only if it could not jump */
	con_str("LOADER", why);
	con_skip();
	con_str("", "Tire uma foto desta tela!");
	countdown_reboot(con_row(), RUN_SECONDS);
}
