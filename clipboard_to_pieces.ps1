 
 smog7108
 # PowerShell Clipboard to Pieces Service
# Fast iteration approach using Pieces CLI

param(
    [int]$CheckInterval = 2
)

# Configuration
$piecesDir = "$env:USERPROFILE\.clipboard-to-pieces"
$processedItems = @{}
$maxCacheSize = 100

# Create directory if it doesn't exist
if (!(Test-Path $piecesDir)) {
    New-Item -ItemType Directory -Path $piecesDir -Force | Out-Null
}

Write-Host "PowerShell Clipboard to Pieces Service" -ForegroundColor Green
Write-Host "Files will be saved to: $piecesDir" -ForegroundColor Yellow
Write-Host "Press Ctrl+C to stop the service" -ForegroundColor Yellow
Write-Host ""

function Get-ClipboardContent {
    try {
        # Try to get image from clipboard
        $image = Get-Clipboard -Format Image
        if ($image) {
            return "image", $image
        }
        
        # Try to get text from clipboard
        $text = Get-Clipboard -Format Text
        if ($text) {
            return "text", $text
        }
        
        return $null, $null
    }
    catch {
        return $null, $null
    }
}

function Save-ImageToFile {
    param($image, $filename)
    
    try {
        $filePath = Join-Path $piecesDir $filename
        $image.Save($filePath, [System.Drawing.Imaging.ImageFormat]::Png)
        return $filePath
    }
    catch {
        Write-Host "Error saving image: $_" -ForegroundColor Red
        return $null
    }
}

function Save-TextToFile {
    param($text, $filename)
    
    try {
        $filePath = Join-Path $piecesDir $filename
        $text | Out-File -FilePath $filePath -Encoding UTF8
        return $filePath
    }
    catch {
        Write-Host "Error saving text: $_" -ForegroundColor Red
        return $null
    }
}

function Import-ToPieces {
    param($filePath, $contentType)
    
    try {
        # Use Pieces CLI to import file
        $result = & pieces-cli import $filePath 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "SUCCESS: Imported to Pieces.app" -ForegroundColor Green
            return $true
        } else {
            Write-Host "Pieces CLI import failed: $result" -ForegroundColor Yellow
            return $false
        }
    }
    catch {
        Write-Host "Error importing to Pieces: $_" -ForegroundColor Red
        return $false
    }
}

function Process-Content {
    param($contentType, $content)
    
    $timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
    
    if ($contentType -eq "text") {
        $filename = "Text_$timestamp.txt"
        $filePath = Save-TextToFile -text $content -filename $filename
        
        if ($filePath) {
            Write-Host "Processing text content ($($content.Length) chars)..." -ForegroundColor Cyan
            Import-ToPieces -filePath $filePath -contentType $contentType
        }
    }
    elseif ($contentType -eq "image") {
        $filename = "Image_$timestamp.png"
        $filePath = Save-ImageToFile -image $content -filename $filename
        
        if ($filePath) {
            Write-Host "Processing image content..." -ForegroundColor Cyan
            Import-ToPieces -filePath $filePath -contentType $contentType
        }
    }
}

# Main service loop
try {
    while ($true) {
        $contentType, $content = Get-ClipboardContent
        
        if ($content) {
            # Create hash for duplicate detection
            $contentHash = [System.Security.Cryptography.MD5]::Create().ComputeHash([System.Text.Encoding]::UTF8.GetBytes($content.ToString()))
            $hashString = [System.BitConverter]::ToString($contentHash) -replace '-', ''
            
            # Check if we've processed this recently
            if ($processedItems.ContainsKey($hashString)) {
                $lastProcessed = $processedItems[$hashString]
                $timeDiff = (Get-Date) - $lastProcessed
                
                if ($timeDiff.TotalSeconds -lt 30) {
                    Start-Sleep $CheckInterval
                    continue
                }
            }
            
            # Update processed items
            $processedItems[$hashString] = Get-Date
            
            # Clean up old entries
            if ($processedItems.Count -gt $maxCacheSize) {
                $oldestKey = $processedItems.Keys | Sort-Object { $processedItems[$_] } | Select-Object -First 1
                $processedItems.Remove($oldestKey)
            }
            
            # Process the content
            Process-Content -contentType $contentType -content $content
        }
        
        Start-Sleep $CheckInterval
    }
}
catch {
    Write-Host "Service error: $_" -ForegroundColor Red
}
finally {
    Write-Host "Service stopped." -ForegroundColor Yellow
}


