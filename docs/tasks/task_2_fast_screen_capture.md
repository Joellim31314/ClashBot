# Task 2: Replace Slow ADB Screen Capture with Fast Capture Method

## Problem
The current screen capture in `bot/screen.py` uses `ppadb`'s `device.screencap()`, which:
1. Executes `adb shell screencap -p` on the emulator
2. Transfers a full **PNG** (lossless, ~2.5MB) over ADB TCP
3. Decodes the PNG in Python with PIL

This takes **200-500ms per frame**, hard-capping the pipeline at ~2-5 FPS even with instant detection. For a live overlay, we need **<50ms capture time** (~20+ FPS capture).

## Goal
Replace the ADB screencap with a faster capture method to reduce frame capture time from ~300ms to ~30-50ms.

---

## Environment Context

| Item | Value |
|------|-------|
| **OS** | Windows |
| **Python** | 3.14.2 |
| **Virtual env** | `c:\Users\Joel Lim\Desktop\ClashBot\venv` |
| **Emulator** | LDPlayer 9 (process: `Ld9BoxHeadless.exe`) |
| **Screen resolution** | 1080×2400 |
| **Current capture** | `ppadb` → `device.screencap()` → PIL Image |
| **Project root** | `c:\Users\Joel Lim\Desktop\ClashBot` |

## Files to Modify
- `c:\Users\Joel Lim\Desktop\ClashBot\bot\screen.py` (main capture module)
- `c:\Users\Joel Lim\Desktop\ClashBot\data\live_detection.py` (live overlay — uses `ScreenCapture`)
- `c:\Users\Joel Lim\Desktop\ClashBot\requirements.txt` (add new dependencies)

---

## Current Implementation

### `bot/screen.py` (full file, 43 lines):
```python
"""ADB screen capture module for ClashBot."""
import io
import logging
from PIL import Image
from ppadb.client import Client as AdbClient

import config

logger = logging.getLogger(__name__)


class ScreenCapture:
    """Captures screenshots from the Android emulator via ADB."""

    def __init__(self):
        self._client = AdbClient(host=config.ADB_HOST, port=config.ADB_PORT)
        self._device = None
        self._connect()

    def _connect(self):
        devices = self._client.devices()
        if devices:
            self._device = devices[0]
            logger.info("Connected to device: %s", self._device.serial)
        else:
            logger.warning("No ADB devices found. Is the emulator running?")

    def is_connected(self) -> bool:
        return self._device is not None

    def capture(self) -> Image.Image:
        if not self.is_connected():
            raise ConnectionError("No ADB device connected. Start the emulator first.")
        png_bytes = self._device.screencap()
        image = Image.open(io.BytesIO(png_bytes)).convert("RGB")
        logger.debug("Captured frame: %s", image.size)
        return image

    def reconnect(self):
        logger.info("Attempting ADB reconnection...")
        self._device = None
        self._connect()
```

### How `live_detection.py` uses it (lines 216-226):
```python
from bot.screen import ScreenCapture

screen = ScreenCapture()
if not screen.is_connected():
    print("ERROR: Cannot connect to emulator. Is LDPlayer running?")
    sys.exit(1)

# In the main loop:
img = screen.capture()  # Returns PIL Image — this is the slow part
```

---

## Recommended Approach: Windows D3D Desktop Capture (DXCam)

Since LDPlayer renders its window on the Windows desktop, we can capture the emulator window directly using GPU-accelerated Windows Desktop Duplication API. This bypasses ADB entirely.

### Why this approach:
- **No ADB overhead** — captures directly from the GPU framebuffer
- **~5-15ms per frame** (vs 200-500ms with ADB)
- **Works with any emulator** — captures whatever is on screen
- LDPlayer's window just needs to be visible (not minimized)

### Install dependency:
```powershell
pip install dxcam
```

> [!WARNING]
> `dxcam` requires the emulator window to be **visible on screen** (not minimized, not fully occluded). This is the main trade-off vs ADB (which works even with the window hidden).

### New `bot/screen.py` implementation:

```python
"""Screen capture module for ClashBot — fast D3D or fallback ADB."""
import io
import logging
import time
from PIL import Image

import config

logger = logging.getLogger(__name__)


class ScreenCapture:
    """Captures screenshots from the emulator.
    
    Uses DXCam (Windows Desktop Duplication API) for fast capture when 
    available. Falls back to ADB screencap if DXCam is not installed 
    or the emulator window cannot be found.
    """

    def __init__(self, use_dxcam: bool = True):
        self._device = None       # ADB device (fallback)
        self._dxcam = None        # DXCam camera instance
        self._region = None       # (left, top, right, bottom) of emulator window
        self._use_dxcam = use_dxcam

        if use_dxcam:
            self._init_dxcam()
        
        if self._dxcam is None:
            logger.info("DXCam not available, falling back to ADB capture")
            self._init_adb()

    def _init_dxcam(self):
        """Try to set up DXCam screen capture."""
        try:
            import dxcam
            self._dxcam = dxcam.create()
            logger.info("DXCam capture initialized")
            # Find the LDPlayer window region
            self._region = self._find_emulator_window()
            if self._region is None:
                logger.warning("Could not find LDPlayer window, DXCam needs window region")
                self._dxcam = None
        except ImportError:
            logger.info("dxcam not installed — pip install dxcam")
        except Exception as e:
            logger.warning("DXCam init failed: %s", e)

    def _find_emulator_window(self):
        """Find the LDPlayer window rectangle using win32gui."""
        try:
            import win32gui
            
            def callback(hwnd, results):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    # LDPlayer window titles typically contain "LDPlayer"
                    if "LDPlayer" in title or "LDMultiPlayer" in title:
                        rect = win32gui.GetWindowRect(hwnd)
                        results.append(rect)
                return True
            
            results = []
            win32gui.EnumWindows(callback, results)
            
            if results:
                left, top, right, bottom = results[0]
                logger.info("Found emulator window: (%d, %d, %d, %d)", 
                           left, top, right, bottom)
                return (left, top, right, bottom)
            else:
                logger.warning("No LDPlayer window found")
                return None
        except ImportError:
            logger.warning("pywin32 not installed — pip install pywin32")
            return None

    def _init_adb(self):
        """Fall back to ADB capture."""
        try:
            from ppadb.client import Client as AdbClient
            client = AdbClient(host=config.ADB_HOST, port=config.ADB_PORT)
            devices = client.devices()
            if devices:
                self._device = devices[0]
                logger.info("ADB connected to: %s", self._device.serial)
            else:
                logger.warning("No ADB devices found")
        except Exception as e:
            logger.warning("ADB connection failed: %s", e)

    def is_connected(self) -> bool:
        return self._dxcam is not None or self._device is not None

    def capture(self) -> Image.Image:
        """Capture a frame. Uses DXCam if available, else ADB."""
        if self._dxcam is not None and self._region is not None:
            return self._capture_dxcam()
        elif self._device is not None:
            return self._capture_adb()
        else:
            raise ConnectionError("No capture method available")

    def _capture_dxcam(self) -> Image.Image:
        """Fast GPU-based capture via Desktop Duplication API."""
        frame = self._dxcam.grab(region=self._region)
        if frame is None:
            # DXCam returns None if no new frame; retry once
            time.sleep(0.01)
            frame = self._dxcam.grab(region=self._region)
        if frame is None:
            raise RuntimeError("DXCam returned no frame — is the window visible?")
        # DXCam returns BGR numpy array; convert to PIL RGB
        image = Image.fromarray(frame[:, :, ::-1])  # BGR → RGB
        # Resize to expected resolution if needed
        if image.size != (config.SCREEN_WIDTH, config.SCREEN_HEIGHT):
            image = image.resize((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), Image.LANCZOS)
        logger.debug("DXCam frame: %s", image.size)
        return image

    def _capture_adb(self) -> Image.Image:
        """Slow ADB fallback capture."""
        png_bytes = self._device.screencap()
        image = Image.open(io.BytesIO(png_bytes)).convert("RGB")
        logger.debug("ADB frame: %s", image.size)
        return image

    def reconnect(self):
        """Re-initialize capture."""
        logger.info("Attempting reconnection...")
        self._dxcam = None
        self._device = None
        self._region = None
        if self._use_dxcam:
            self._init_dxcam()
        if self._dxcam is None:
            self._init_adb()
```

### Dependencies to add to `requirements.txt`:
```
dxcam>=0.4.0
pywin32>=306
```

---

## Alternative Approach: scrcpy Stream (if DXCam doesn't work well)

scrcpy can stream the Android screen over a local socket with H.264 encoding, giving ~30 FPS with very low latency.

```powershell
pip install scrcpy-client[adb]
```

This is more complex to set up but works even when the emulator is minimized. Only pursue this if DXCam doesn't work for the user's setup.

---

## Important Constraints

1. **The `capture()` method must return a `PIL.Image.Image` in RGB mode** — the rest of the codebase depends on this (live_detection.py, main.py, debug_coords.py, etc.)
2. **The returned image must be 1080×2400** — all coordinates in `config.py` are calibrated for this resolution
3. **Keep ADB as a fallback** — the main bot loop in `main.py` uses `ScreenCapture` too, and it should keep working even without DXCam
4. **No changes to `live_detection.py`** are required — it just calls `screen.capture()` and gets a PIL Image back

## Verification

### Capture speed test:
```python
import time, sys
sys.path.insert(0, ".")
from bot.screen import ScreenCapture

s = ScreenCapture()
times = []
for _ in range(20):
    t0 = time.time()
    img = s.capture()
    times.append(time.time() - t0)

avg_ms = sum(times) / len(times) * 1000
print(f"Average capture: {avg_ms:.0f}ms")
print(f"Image size: {img.size}")
print(f"Target: <50ms with DXCam, 200-500ms with ADB fallback")
```

### Verification Criteria:
- [ ] `ScreenCapture()` initializes without errors
- [ ] `capture()` returns a PIL Image of size (1080, 2400)
- [ ] Capture time is < 50ms with DXCam (vs ~300ms with ADB)
- [ ] Falls back to ADB gracefully if DXCam not available
- [ ] `live_detection.py` still works without modification
- [ ] `main.py` still works without modification
