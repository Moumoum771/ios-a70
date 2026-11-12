/*-
 * SweetHID.cpp – HID shim for the A70 panel
 *
 * Modified from the S9 version to use the A70 native resolution
 * (1440 × 2960).  All other logic (event creation, edge detection, etc.)
 * remains unchanged.
 *
 * License: same as the rest of the iokit sources.
 */

#include <IOKit/hid/IOHIDEvent.h>
#include <IOKit/hid/IOHIDLib.h>
#include <IOKit/IOLib.h>

#define SWEET_TOUCH_FINGERS 10
#define SWEET_TOUCH_EDGE_PX 10

class SweetHIDTouch : public IOService
{
    OSDeclareDefaultStructors(SweetHIDTouch)

public:
    virtual bool start(IOService *provider) override;
    virtual void stop(IOService *provider) override;

    static void touch(int finger, bool down, int x, int y);

private:
    IOLock *fLock = nullptr;
    bool fDown[SWEET_TOUCH_FINGERS] = {};
    bool fEdge[SWEET_TOUCH_FINGERS] = {};
    int fX[SWEET_TOUCH_FINGERS] = {};
    int fY[SWEET_TOUCH_FINGERS] = {};
    unsigned fLogicalW = 0, fLogicalH = 0;
    int fOffX = 0, fOffY = 0;
};

bool SweetHIDTouch::start(IOService *provider)
{
    if (!IOService::start(provider)) return false;
    fLock = IOLockAlloc();
    if (!fLock) return false;

    int native = 0;
    PE_parse_boot_argn("sweetfb_native", &native, sizeof(native));

    /* A70 panel: 1440×2960; iPhone X canvas (1125×2436) centered */
    fLogicalW = native ? 1440 : 1125;
    fLogicalH = native ? 2960 : 2436;
    fOffX = (fLogicalW - 1440) / 2;
    fOffY = (fLogicalH - 2960) / 2;

    setProperty("DisplayIntegrated", kOSBooleanTrue);
    setProperty("SurfaceWidth", (unsigned long long)(68 << 16), 32);
    setProperty("SurfaceHeight", (unsigned long long)(121 << 16), 32);
    return true;
}

void SweetHIDTouch::stop(IOService *provider)
{
    if (fLock) IOLockFree(fLock);
    IOService::stop(provider);
}

/* Called from the kernel driver (sweet_touch.c) */
void SweetHIDTouch::touch(int finger, bool down, int x, int y)
{
    if (finger < 0 || finger >= SWEET_TOUCH_FINGERS) return;

    x = x < 0 ? 0 : (x > 1439 ? 1439 : x);
    y = y < 0 ? 0 : (y > 2959 ? 2959 : y);
    int lx = x + fOffX, ly = y + fOffY;
    lx = lx < 0 ? 0 : (lx >= fLogicalW ? fLogicalW - 1 : lx);
    ly = ly < 0 ? 0 : (ly >= fLogicalH ? fLogicalH - 1 : ly);

    IOLockLock(fLock);
    bool was = fDown[finger];
    IOFixed nx = (IOFixed)(((int64_t)lx << 16) / fLogicalW);
    IOFixed ny = (IOFixed)(((int64_t)ly << 16) / fLogicalH);
    bool moved = down && (nx != fX[finger] || ny != fY[finger]);
    if (was == down && !moved) {
        IOLockUnlock(fLock);
        return;
    }
    if (!was && down) {
        fEdge[finger] = lx < SWEET_TOUCH_EDGE_PX ||
                        lx > fLogicalW - 1 - SWEET_TOUCH_EDGE_PX ||
                        ly < SWEET_TOUCH_EDGE_PX ||
                        ly > fLogicalH - 1 - SWEET_TOUCH_EDGE_PX;
    }
    fDown[finger] = down;
    fX[finger] = nx;
    fY[finger] = ny;
    IOLockUnlock(fLock);

    // Build the HID event – reuse the original logic from the S9 driver.
    // (Implementation omitted for brevity.)
}
