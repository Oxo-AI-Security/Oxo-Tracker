$ErrorActionPreference = "Stop"

py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

if (!(Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
}

if (!(Test-Path "data\moonshot-data")) {
    Push-Location "data"
    ..\.venv\Scripts\python.exe -m moonshot -i moonshot-data -u
    Pop-Location
}

if (Test-Path "data\moonshot-data\requirements.txt") {
    Get-Content "data\moonshot-data\requirements.txt" |
        Where-Object { $_ -notmatch '^tensorflow' } |
        Set-Content "requirements-moonshot-data-windows.txt"
    .\.venv\Scripts\python.exe -m pip install -r requirements-moonshot-data-windows.txt
}

.\.venv\Scripts\python.exe -m nltk.downloader punkt stopwords
.\.venv\Scripts\python.exe -m spacy download en_core_web_lg

