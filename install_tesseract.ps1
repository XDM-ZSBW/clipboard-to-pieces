# PowerShell script to install Tesseract OCR on Windows
# Run as Administrator for best results

Write-Host "Installing Tesseract OCR for clipboard-to-pieces service..." -ForegroundColor Green
Write-Host "=========================================================" -ForegroundColor Green

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")

if (-not $isAdmin) {
    Write-Host "WARNING: Not running as Administrator. Some installation methods may fail." -ForegroundColor Yellow
    Write-Host "Consider running PowerShell as Administrator for automatic installation." -ForegroundColor Yellow
    Write-Host ""
}

# Function to check if Tesseract is already installed
function Test-Tesseract {
    try {
        $version = & tesseract --version 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Tesseract OCR already installed!" -ForegroundColor Green
            Write-Host "Version: $($version[0])" -ForegroundColor Cyan
            return $true
        }
    }
    catch {
        # Tesseract not found
    }
    return $false
}

# Check if already installed
if (Test-Tesseract) {
    Write-Host "Tesseract is ready to use!" -ForegroundColor Green
    exit 0
}

Write-Host "Tesseract OCR not found. Attempting installation..." -ForegroundColor Yellow

# Method 1: Try winget (Windows 10/11)
Write-Host "Trying winget installation..." -ForegroundColor Cyan
try {
    $wingetVersion = & winget --version 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Installing Tesseract via winget..." -ForegroundColor Cyan
        & winget install --id UB-Mannheim.TesseractOCR -e --accept-package-agreements --accept-source-agreements
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Tesseract installed successfully via winget!" -ForegroundColor Green
            if (Test-Tesseract) {
                Write-Host "Installation verified!" -ForegroundColor Green
                exit 0
            }
        }
    }
}
catch {
    Write-Host "winget not available or failed" -ForegroundColor Yellow
}

# Method 2: Try Chocolatey
Write-Host "Trying Chocolatey installation..." -ForegroundColor Cyan
try {
    $chocoVersion = & choco --version 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Installing Tesseract via Chocolatey..." -ForegroundColor Cyan
        & choco install tesseract -y
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Tesseract installed successfully via Chocolatey!" -ForegroundColor Green
            if (Test-Tesseract) {
                Write-Host "Installation verified!" -ForegroundColor Green
                exit 0
            }
        }
    }
}
catch {
    Write-Host "Chocolatey not available or failed" -ForegroundColor Yellow
}

# Method 3: Manual download instructions
Write-Host ""
Write-Host "❌ Automatic installation failed. Manual installation required:" -ForegroundColor Red
Write-Host ""
Write-Host "1. Download Tesseract OCR from:" -ForegroundColor Yellow
Write-Host "   https://github.com/UB-Mannheim/tesseract/wiki" -ForegroundColor Cyan
Write-Host ""
Write-Host "2. Run the installer with default settings" -ForegroundColor Yellow
Write-Host ""
Write-Host "3. Add Tesseract to PATH:" -ForegroundColor Yellow
Write-Host "   - Open System Properties > Environment Variables" -ForegroundColor White
Write-Host "   - Add 'C:\Program Files\Tesseract-OCR' to PATH" -ForegroundColor White
Write-Host "   - Or set TESSDATA_PREFIX='C:\Program Files\Tesseract-OCR\tessdata'" -ForegroundColor White
Write-Host ""
Write-Host "4. Restart your terminal and run the setup script again" -ForegroundColor Yellow
Write-Host ""

# Try to open the download page
try {
    Start-Process "https://github.com/UB-Mannheim/tesseract/wiki"
    Write-Host "Opening download page in your browser..." -ForegroundColor Green
}
catch {
    Write-Host "Could not open browser automatically" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Press any key to continue..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

exit 1




