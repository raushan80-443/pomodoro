// High-Performance Zero-Dependency Canvas Chart Renderer for Pomodoro

function setupCanvasDPI(canvas) {
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  canvas.width = rect.width * dpr;
  canvas.height = rect.height * dpr;
  const ctx = canvas.getContext('2d');
  ctx.scale(dpr, dpr);
  return { ctx, width: rect.width, height: rect.height };
}

// 1. Daily Focus Work Hours Line Chart
function drawDailyChart(canvasId, dataPoints) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || !dataPoints || dataPoints.length === 0) return;
  const { ctx, width, height } = setupCanvasDPI(canvas);

  const padLeft = 36, padRight = 14, padTop = 14, padBottom = 24;
  const chartW = width - padLeft - padRight;
  const chartH = height - padTop - padBottom;

  const maxVal = Math.max(...dataPoints.map(p => p.value), 4);
  const stepX = chartW / Math.max(dataPoints.length - 1, 1);

  // Background Grid Lines
  ctx.strokeStyle = '#1e293b';
  ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {
    const y = padTop + (chartH / 4) * i;
    ctx.beginPath();
    ctx.moveTo(padLeft, y);
    ctx.lineTo(width - padRight, y);
    ctx.stroke();

    const val = (maxVal * (4 - i) / 4).toFixed(1);
    ctx.fillStyle = '#64748b';
    ctx.font = '9px sans-serif';
    ctx.textAlign = 'right';
    ctx.fillText(`${val}h`, padLeft - 6, y + 3);
  }

  // Draw Path Points
  const coords = dataPoints.map((p, idx) => {
    const x = padLeft + idx * stepX;
    const y = padTop + chartH - (p.value / maxVal) * chartH;
    return { x, y };
  });

  // Gradient Fill Area
  const grad = ctx.createLinearGradient(0, padTop, 0, padTop + chartH);
  grad.addColorStop(0, 'rgba(56, 189, 248, 0.3)');
  grad.addColorStop(1, 'rgba(56, 189, 248, 0.0)');

  ctx.beginPath();
  ctx.moveTo(coords[0].x, padTop + chartH);
  coords.forEach(pt => ctx.lineTo(pt.x, pt.y));
  ctx.lineTo(coords[coords.length - 1].x, padTop + chartH);
  ctx.closePath();
  ctx.fillStyle = grad;
  ctx.fill();

  // Draw Line Stroke
  ctx.beginPath();
  ctx.strokeStyle = '#38bdf8';
  ctx.lineWidth = 2;
  coords.forEach((pt, i) => {
    if (i === 0) ctx.moveTo(pt.x, pt.y);
    else ctx.lineTo(pt.x, pt.y);
  });
  ctx.stroke();

  // Draw Date Markers on X-Axis
  ctx.fillStyle = '#64748b';
  ctx.font = '8px sans-serif';
  ctx.textAlign = 'center';
  const labelStep = Math.max(Math.floor(dataPoints.length / 4), 1);
  dataPoints.forEach((p, idx) => {
    if (idx % labelStep === 0 || idx === dataPoints.length - 1) {
      const shortDate = p.date.substring(5); // MM-DD
      ctx.fillText(shortDate, coords[idx].x, height - 6);
    }
  });
}

// 2. Productivity Rating Distribution Bar Chart
function drawRatingsChart(canvasId, ratingsObj) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || !ratingsObj) return;
  const { ctx, width, height } = setupCanvasDPI(canvas);

  const padLeft = 32, padRight = 14, padTop = 14, padBottom = 24;
  const chartW = width - padLeft - padRight;
  const chartH = height - padTop - padBottom;

  const stars = ['1 Star', '2 Star', '3 Star', '4 Star', '5 Star'];
  const values = stars.map(s => ratingsObj[s] || 0);
  const maxVal = Math.max(...values, 5);

  const barWidth = chartW / 5 - 12;

  // Grid lines
  ctx.strokeStyle = '#1e293b';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(padLeft, padTop + chartH);
  ctx.lineTo(width - padRight, padTop + chartH);
  ctx.stroke();

  stars.forEach((star, idx) => {
    const val = values[idx];
    const barH = (val / maxVal) * chartH;
    const x = padLeft + idx * (chartW / 5) + 6;
    const y = padTop + chartH - barH;

    // Bar Fill
    ctx.fillStyle = idx >= 3 ? '#f59e0b' : '#3b82f6';
    ctx.fillRect(x, y, barWidth, barH);

    // Value Label on top of bar
    if (val > 0) {
      ctx.fillStyle = '#f8fafc';
      ctx.font = '9px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(val, x + barWidth / 2, y - 4);
    }

    // Star Label on bottom
    ctx.fillStyle = '#94a3b8';
    ctx.font = '9px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(`${idx + 1}★`, x + barWidth / 2, height - 6);
  });
}

// 3. Work Session End Trigger Breakdown (Donut Chart)
function drawTriggersChart(canvasId, triggersObj) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || !triggersObj) return;
  const { ctx, width, height } = setupCanvasDPI(canvas);

  const items = [
    { label: 'Timer', val: triggersObj['timer'] || 0, color: '#10b981' },
    { label: 'Sleep', val: triggersObj['systemSleep'] || 0, color: '#f59e0b' },
    { label: 'Manual', val: triggersObj['userBreakNow'] || 0, color: '#60a5fa' },
  ];

  const total = items.reduce((acc, it) => acc + it.val, 0) || 1;
  const centerX = width * 0.35;
  const centerY = height * 0.5;
  const radius = Math.min(width, height) * 0.36;
  const innerRadius = radius * 0.55;

  let startAngle = -Math.PI / 2;

  items.forEach(item => {
    const sliceAngle = (item.val / total) * 2 * Math.PI;
    const endAngle = startAngle + sliceAngle;

    ctx.beginPath();
    ctx.arc(centerX, centerY, radius, startAngle, endAngle);
    ctx.arc(centerX, centerY, innerRadius, endAngle, startAngle, true);
    ctx.closePath();
    ctx.fillStyle = item.color;
    ctx.fill();

    startAngle = endAngle;
  });

  // Legend on right side
  const legX = width * 0.65;
  items.forEach((item, idx) => {
    const legY = centerY - 24 + idx * 24;

    ctx.fillStyle = item.color;
    ctx.fillRect(legX, legY, 10, 10);

    ctx.fillStyle = '#cbd5e1';
    ctx.font = '10px sans-serif';
    ctx.textAlign = 'left';
    const pct = Math.round((item.val / total) * 100);
    ctx.fillText(`${item.label} (${pct}%)`, legX + 16, legY + 9);
  });
}

// 4. Cumulative Focus Growth Area Chart
function drawCumulativeChart(canvasId, dataPoints) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || !dataPoints || dataPoints.length === 0) return;
  const { ctx, width, height } = setupCanvasDPI(canvas);

  const padLeft = 38, padRight = 14, padTop = 14, padBottom = 24;
  const chartW = width - padLeft - padRight;
  const chartH = height - padTop - padBottom;

  const maxVal = Math.max(...dataPoints.map(p => p.value), 10);
  const stepX = chartW / Math.max(dataPoints.length - 1, 1);

  // Background Grid
  ctx.strokeStyle = '#1e293b';
  ctx.lineWidth = 1;
  for (let i = 0; i <= 3; i++) {
    const y = padTop + (chartH / 3) * i;
    ctx.beginPath();
    ctx.moveTo(padLeft, y);
    ctx.lineTo(width - padRight, y);
    ctx.stroke();

    const val = Math.round(maxVal * (3 - i) / 3);
    ctx.fillStyle = '#64748b';
    ctx.font = '9px sans-serif';
    ctx.textAlign = 'right';
    ctx.fillText(`${val}h`, padLeft - 6, y + 3);
  }

  const coords = dataPoints.map((p, idx) => {
    const x = padLeft + idx * stepX;
    const y = padTop + chartH - (p.value / maxVal) * chartH;
    return { x, y };
  });

  // Area Fill
  const grad = ctx.createLinearGradient(0, padTop, 0, padTop + chartH);
  grad.addColorStop(0, 'rgba(139, 92, 246, 0.35)');
  grad.addColorStop(1, 'rgba(139, 92, 246, 0.0)');

  ctx.beginPath();
  ctx.moveTo(coords[0].x, padTop + chartH);
  coords.forEach(pt => ctx.lineTo(pt.x, pt.y));
  ctx.lineTo(coords[coords.length - 1].x, padTop + chartH);
  ctx.closePath();
  ctx.fillStyle = grad;
  ctx.fill();

  // Stroke
  ctx.beginPath();
  ctx.strokeStyle = '#a78bfa';
  ctx.lineWidth = 2;
  coords.forEach((pt, i) => {
    if (i === 0) ctx.moveTo(pt.x, pt.y);
    else ctx.lineTo(pt.x, pt.y);
  });
  ctx.stroke();

  // Total End Value Callout
  const lastPt = coords[coords.length - 1];
  const lastVal = dataPoints[dataPoints.length - 1].value;
  ctx.fillStyle = '#f59e0b';
  ctx.font = 'bold 10px sans-serif';
  ctx.textAlign = 'right';
  ctx.fillText(`${lastVal.toFixed(1)} hrs total`, width - padRight, padTop - 2);
}

window.charts = {
  drawDailyChart,
  drawRatingsChart,
  drawTriggersChart,
  drawCumulativeChart,
};
