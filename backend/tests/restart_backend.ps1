$procId = (Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue).OwningProcess
if ($procId) {
    Stop-Process -Id $procId -Force
    Write-Host "Killed process $procId"
}
Start-Process cmd.exe -ArgumentList '/k "call venv\Scripts\activate.bat && set PYTHONPATH=. && python -m backend.main"' -WorkingDirectory 'd:\proyectos\Synapse'
Write-Host "Started new backend"
