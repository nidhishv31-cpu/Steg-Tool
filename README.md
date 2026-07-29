# Stegtool v2.0 — Advanced Steganography Suite

Stegtool is a professional-grade, high-performance steganography application built in Python. It allows users to hide secret text messages or files inside cover images (PNG/BMP) using secure algorithms.

## Features

- **Double-Hardened Security Mode**:
  - **KDF**: `scrypt` memory-hard key derivation ($N=2^{17}, r=8, p=1$) yielding a 512-bit key.
  - **Cipher**: Authenticated symmetric encryption using **AES-256-GCM**.
  - **Scattered Layout**: The password-derived KDF output seeds a deterministic index scatter, scattering bits randomly across image pixels.
- **Steganography Quality (LSB Matching)**:
  - Implements **$\pm 1$ LSB Matching** instead of force-setting bits. This preserves the natural pixel-value histogram and significantly improves resistance against chi-square and RS steganalysis.
- **Fast Performance**:
  - Uses vectorized `NumPy` array operations instead of looping over individual pixels.
  - Reads only the minimum required bits during extraction instead of decoding the entire image.
- **Minimalist Glassmorphic UI**:
  - Crisp high-DPI rendering.
  - 8 customization presets (Obsidian, Nord Ice, Cyberpunk Neon, Slate Light, etc.).
  - Non-blocking toast notifications.
- **No-Encryption Mode**:
  - Option to hide plain content sequentially for simple sharing.

## Installation & Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/Stegtool.git
   cd Stegtool
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**:
   ```bash
   python stegtool.py
   ```

## Compiling to Standalone Executable (.exe)

You can build the app into a single standalone Windows executable using PyInstaller:

```bash
pip install pyinstaller
python -m PyInstaller --clean Stegtool_v2.spec
```
The compiled output will be available in the `dist/` directory.

## License

This project is licensed under the MIT License.
