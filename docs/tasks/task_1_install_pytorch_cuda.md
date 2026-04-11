# Task 1: Install PyTorch with CUDA Support (Highest Priority)

## Problem
PyTorch is installed as **CPU-only** (`torch 2.10.0+cpu`), meaning both YOLO detectors in `live_detection.py` run entirely on CPU. This causes inference to take **~1-3 seconds per frame** instead of **~30-60ms on GPU**, making the live overlay feel like a slideshow.

## Goal
Replace the CPU-only PyTorch + torchvision with CUDA-enabled versions so YOLO inference runs on the GPU. This is the single biggest performance fix — expected **~10x speedup**.

---

## Environment Context

| Item | Value |
|------|-------|
| **OS** | Windows |
| **Python** | 3.14.2 (`C:\Users\Joel Lim\AppData\Local\Programs\Python\Python314\python.exe`) |
| **Virtual env** | `c:\Users\Joel Lim\Desktop\ClashBot\venv` |
| **GPU** | NVIDIA GeForce RTX 4050 Laptop GPU (6GB VRAM, Compute Capability 8.9) |
| **NVIDIA Driver** | 560.94 |
| **CUDA Version (driver)** | 12.6 |
| **Current torch** | `2.10.0` (CPU-only) |
| **Current torchvision** | `0.25.0` (CPU-only) |
| **ultralytics** | `8.4.22` |
| **Project root** | `c:\Users\Joel Lim\Desktop\ClashBot` |

## Current Packages (relevant)
```
torch                   2.10.0
torchvision             0.25.0
ultralytics             8.4.22
opencv-python           4.13.0.92
pillow                  12.1.0
```

> [!IMPORTANT]
> The `requirements.txt` pins `ultralytics==8.1.24` but `8.4.22` is actually installed. The YOLO models (`models/katacr/detector1_v0.7.13.pt`, `models/katacr/detector2_v0.7.13.pt`) are from the KataCR project. Make sure they still load correctly after the PyTorch upgrade.

---

## Step-by-Step Instructions

### Step 1: Activate the virtual environment
```powershell
cd c:\Users\Joel Lim\Desktop\ClashBot
.\venv\Scripts\Activate.ps1
```

### Step 2: Uninstall current CPU-only PyTorch
```powershell
pip uninstall torch torchvision torchaudio -y
```

### Step 3: Install PyTorch with CUDA 12.6 support
Go to https://pytorch.org/get-started/locally/ and select:
- PyTorch Build: Stable
- OS: Windows
- Package: pip
- Language: Python
- Compute Platform: CUDA 12.6

The command will look something like:
```powershell
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126
```

> [!WARNING]
> Python 3.14 is very new. If PyTorch doesn't have wheels for 3.14 + CUDA 12.6 yet, check the PyTorch website for available combinations. You may need to try:
> - CUDA 12.4 (`cu124`) instead of 12.6
> - A nightly build: `pip install --pre torch torchvision --index-url https://download.pytorch.org/whl/nightly/cu126`
> - If no 3.14 wheels exist at all, the user may need to create a Python 3.12 or 3.13 venv instead.

### Step 4: Verify installation
```powershell
python -c "import torch; print('CUDA available:', torch.cuda.is_available()); print('Device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'FAIL - CPU only'); print('Torch version:', torch.__version__)"
```

**Expected output:**
```
CUDA available: True
Device: NVIDIA GeForce RTX 4050 Laptop GPU
Torch version: 2.x.x+cu12x
```

### Step 5: Verify YOLO models still load
```powershell
python -c "from ultralytics import YOLO; m = YOLO('models/katacr/detector1_v0.7.13.pt'); print('Loaded:', len(m.names), 'classes'); print('Device:', next(m.model.parameters()).device)"
```

### Step 6: Quick GPU inference test
```powershell
python -c "
from ultralytics import YOLO
from PIL import Image
import time

m = YOLO('models/katacr/detector1_v0.7.13.pt')
img = Image.new('RGB', (576, 896), (128, 128, 128))

# Warm up
m.predict(source=img, conf=0.35, verbose=False)

# Timed run
t0 = time.time()
for _ in range(10):
    m.predict(source=img, conf=0.35, verbose=False)
avg_ms = (time.time() - t0) / 10 * 1000
print(f'Average inference: {avg_ms:.0f}ms per frame')
print('Target: <100ms on GPU, >500ms means still on CPU')
"
```

---

## Code Change Required (if YOLO doesn't auto-detect GPU)

In `c:\Users\Joel Lim\Desktop\ClashBot\data\live_detection.py`, the `load_models()` function (line 111-117) currently doesn't specify a device. Ultralytics YOLO should auto-detect CUDA, but if it doesn't, modify the function:

**Current code (line 111-117):**
```python
def load_models():
    print("Loading KataCR detectors...")
    m1 = YOLO("models/katacr/detector1_v0.7.13.pt")
    m2 = YOLO("models/katacr/detector2_v0.7.13.pt")
    print(f"  detector1: {len(m1.names)} classes")
    print(f"  detector2: {len(m2.names)} classes")
    return m1, m2
```

**Modified code (only if GPU not auto-detected):**
```python
def load_models():
    print("Loading KataCR detectors...")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    m1 = YOLO("models/katacr/detector1_v0.7.13.pt")
    m2 = YOLO("models/katacr/detector2_v0.7.13.pt")
    # Move models to GPU
    m1.to(device)
    m2.to(device)
    print(f"  detector1: {len(m1.names)} classes (device: {device})")
    print(f"  detector2: {len(m2.names)} classes (device: {device})")
    return m1, m2
```

Also in `run_detection()` (line 135), pass `device` to predict:
```python
result = model.predict(source=arena, conf=conf, iou=0.45, verbose=False, device=device)[0]
```

---

## Verification Criteria
- [ ] `torch.cuda.is_available()` returns `True`
- [ ] `torch.cuda.get_device_name(0)` returns `NVIDIA GeForce RTX 4050 Laptop GPU`
- [ ] Both YOLO models load without errors
- [ ] Single-frame inference takes < 100ms (not > 500ms)
- [ ] `live_detection.py` runs and shows detections

## Rollback
If something breaks:
```powershell
pip uninstall torch torchvision torchaudio -y
pip install torch torchvision
```
This reinstalls the CPU-only version.
