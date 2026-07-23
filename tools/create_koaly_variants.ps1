$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$source = Join-Path $root "static\img\koaly_cutout.png"
$happy = Join-Path $root "static\img\koaly_happy.png"
$sad = Join-Path $root "static\img\koaly_sad.png"

Add-Type -AssemblyName System.Drawing

function New-StarPoints($cx, $cy, $outer, $inner) {
  $points = New-Object 'System.Collections.Generic.List[System.Drawing.PointF]'
  for ($i = 0; $i -lt 10; $i++) {
    $angle = (-90 + $i * 36) * [Math]::PI / 180
    $radius = if ($i % 2 -eq 0) { $outer } else { $inner }
    $points.Add([System.Drawing.PointF]::new(
      [single]($cx + [Math]::Cos($angle) * $radius),
      [single]($cy + [Math]::Sin($angle) * $radius)
    ))
  }
  return $points.ToArray()
}

function Save-Variant($target, $mood) {
  $src = [System.Drawing.Image]::FromFile($source)
  $bmp = New-Object System.Drawing.Bitmap($src.Width, $src.Height, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
  $graphics = [System.Drawing.Graphics]::FromImage($bmp)
  $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
  $graphics.Clear([System.Drawing.Color]::Transparent)

  if ($mood -eq "happy") {
    $graphics.FillEllipse((New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(90, 255, 221, 72))), 34, 30, 188, 188)
  } else {
    $graphics.FillEllipse((New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(80, 132, 180, 255))), 34, 34, 188, 188)
  }

  $graphics.DrawImage($src, 0, 0, $src.Width, $src.Height)

  if ($mood -eq "happy") {
    $smilePen = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(255, 54, 42, 48), 4)
    $shinePen = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(190, 255, 248, 250), 2)
    $graphics.DrawArc($smilePen, 106, 106, 44, 34, 18, 144)
    $graphics.DrawArc($shinePen, 108, 108, 40, 28, 22, 136)
    $graphics.FillEllipse((New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(145, 255, 128, 154))), 68, 108, 22, 15)
    $graphics.FillEllipse((New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(145, 255, 128, 154))), 166, 108, 22, 15)

    foreach ($star in @(
      @(32, 28, 9, 4, [System.Drawing.Color]::FromArgb(255, 255, 210, 46)),
      @(218, 42, 8, 4, [System.Drawing.Color]::FromArgb(255, 48, 203, 127)),
      @(224, 196, 8, 4, [System.Drawing.Color]::FromArgb(255, 255, 92, 106)),
      @(44, 204, 8, 4, [System.Drawing.Color]::FromArgb(255, 74, 144, 226))
    )) {
      $brush = New-Object System.Drawing.SolidBrush($star[4])
      $graphics.FillPolygon($brush, (New-StarPoints $star[0] $star[1] $star[2] $star[3]))
      $brush.Dispose()
    }

    $smilePen.Dispose()
    $shinePen.Dispose()
  } else {
    $pen = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(235, 47, 55, 78), 4)
    $graphics.DrawLine($pen, 82, 78, 106, 70)
    $graphics.DrawLine($pen, 150, 70, 174, 78)
    $graphics.DrawArc($pen, 108, 126, 40, 32, 202, 136)
    $tear = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(225, 83, 168, 246))
    $graphics.FillEllipse($tear, 166, 104, 12, 19)
    $graphics.FillEllipse($tear, 169, 116, 6, 9)
    $tear.Dispose()
    $pen.Dispose()
  }

  $bmp.Save($target, [System.Drawing.Imaging.ImageFormat]::Png)
  $graphics.Dispose()
  $bmp.Dispose()
  $src.Dispose()
}

Save-Variant $happy "happy"
Save-Variant $sad "sad"
Write-Output "Created koaly_happy.png and koaly_sad.png"
