# Limpia logs del backend SynapseCode
# Mantiene solo los ultimos 5 archivos de cada tipo

$LOG_DIR = "D:\proyectos\SynapseCode\logs"
$MAX_FILES = 5

Get-ChildItem $LOG_DIR -Filter "*.log*" | Group-Object { $_.Name -replace '\.\d+$' } | ForEach-Object {
    $files = $_.Group | Sort-Object LastWriteTime -Descending
    if ($files.Count -gt $MAX_FILES) {
        $files[$MAX_FILES..($files.Count-1)] | ForEach-Object {
            Remove-Item $_.FullName -Force
            Write-Host "Eliminado: $($_.Name)"
        }
    }
}
Write-Host "Logs limpios. Mantenidos $MAX_FILES por tipo."
