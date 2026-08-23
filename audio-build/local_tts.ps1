# Generate every pronunciation clip with the Japanese voice installed on this
# machine. No network, no quota, no Cloudflare. Safe to re-run: finished clips
# are skipped, so an interrupted run picks up where it stopped.
$ErrorActionPreference = "Stop"
$root  = "C:\JapaneseLearning\audio-build"
$out   = Join-Path $root "local_wav"
if (-not (Test-Path $out)) { New-Item -ItemType Directory -Path $out | Out-Null }

Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$s.SelectVoice("Microsoft Haruka Desktop")
$s.Rate = -1                     # a shade slower: these are being learned, not skimmed
$fmt = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(
    16000,
    [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen,
    [System.Speech.AudioFormat.AudioChannel]::Mono)

$jobs = Get-Content (Join-Path $root "tts_words.json") -Raw -Encoding UTF8 | ConvertFrom-Json
$made = 0; $skipped = 0; $blank = 0; $failed = 0
$i = 0
foreach ($j in $jobs) {
    $i++
    if (-not $j.text -or $j.text.Trim() -eq "") { $blank++; continue }
    $p = Join-Path $out ($j.name + ".wav")
    if ((Test-Path $p) -and (Get-Item $p).Length -gt 1024) { $skipped++; continue }
    try {
        $s.SetOutputToWaveFile($p, $fmt)
        $s.Speak($j.text)
        $s.SetOutputToNull()
        $made++
    } catch {
        $s.SetOutputToNull()
        $failed++
        Write-Output ("FAILED {0} : {1}" -f $j.text, $_.Exception.Message)
    }
    if ($i % 50 -eq 0) { Write-Output ("  {0}/{1} ..." -f $i, $jobs.Count) }
}
$s.Dispose()
Write-Output ("done: {0} made, {1} already there, {2} blank, {3} failed" -f $made, $skipped, $blank, $failed)
$tot = (Get-ChildItem $out -Filter *.wav | Measure-Object -Property Length -Sum).Sum
Write-Output ("{0} files, {1:N1} MB raw before trimming" -f (Get-ChildItem $out -Filter *.wav).Count, ($tot/1MB))
