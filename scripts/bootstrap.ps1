$ErrorActionPreference = "Stop"

if (!(Test-Path ".venv\Scripts\python.exe")) {
    py -3.11 -m venv .venv
}
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt

if (!(Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
}

if (!(Test-Path "data\moonshot-data")) {
    New-Item -ItemType Directory -Path "data" -Force | Out-Null
    Push-Location "data"
    ..\.venv\Scripts\python.exe -m moonshot -i moonshot-data -u
    Pop-Location
}

.\.venv\Scripts\python.exe -m nltk.downloader punkt punkt_tab averaged_perceptron_tagger_eng stopwords

Write-Host "Desktop development backend is ready. Run npm install and npm run desktop:dev in frontend\."
