#!/usr/bin/env pwsh
# Development run script for the Photo Uploader FastAPI application

Write-Host "🖼️  Starting Photo Uploader FastAPI Application" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan

# Check if virtual environment exists
if (-not (Test-Path ".venv")) {
    Write-Host "Creating Python virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
if ($IsWindows) {
    & .\.venv\Scripts\Activate.ps1
} else {
    . .venv/bin/activate
}

# Install dependencies
Write-Host "Installing dependencies..." -ForegroundColor Yellow
python -m pip install --upgrade pip
pip install -r requirements.txt

# Check for environment configuration
if (-not (Test-Path ".env")) {
    Write-Host "Creating .env file from template..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "⚠️  Please update the .env file with your Azure configuration" -ForegroundColor Red
    Write-Host "   Run 'azd up' first to deploy infrastructure and get the values" -ForegroundColor Yellow
}

# Load environment variables from .env
if (Test-Path ".env") {
    Write-Host "Loading environment variables..." -ForegroundColor Yellow
    Get-Content ".env" | ForEach-Object {
        if ($_ -match "^([^#][^=]+)=(.*)$") {
            [Environment]::SetEnvironmentVariable($matches[1], $matches[2], "Process")
        }
    }
}

# Check Azure CLI authentication
Write-Host "Checking Azure CLI authentication..." -ForegroundColor Yellow
try {
    $azAccount = az account show --query "user.name" -o tsv 2>$null
    if ($azAccount) {
        Write-Host "✅ Authenticated as: $azAccount" -ForegroundColor Green
    } else {
        Write-Host "❌ Not authenticated with Azure CLI" -ForegroundColor Red
        Write-Host "   Please run: az login" -ForegroundColor Yellow
        exit 1
    }
} catch {
    Write-Host "❌ Azure CLI not found or not authenticated" -ForegroundColor Red
    Write-Host "   Please install Azure CLI and run: az login" -ForegroundColor Yellow
    exit 1
}

# Start the application
Write-Host ""
Write-Host "🚀 Starting FastAPI development server..." -ForegroundColor Green
Write-Host "   Access the app at: http://localhost:8000" -ForegroundColor Cyan
Write-Host "   API docs at: http://localhost:8000/api/docs" -ForegroundColor Cyan
Write-Host "   Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

Set-Location src
python start.py