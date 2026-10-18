// Pomodoro Frontend Reactive State & Tauri Command Bridge
// Optimized for Windows and Linux with 2-minute warning, daily skip limits, and live system monitoring

const invoke = (cmd, args = {}) => {
  if (window.__TAURI__ && window.__TAURI__.core && window.__TAURI__.core.invoke) {
    return window.__TAURI__.core.invoke(cmd, args);
  }
  if (window.__TAURI__ && window.__TAURI__.invoke) {
    return window.__TAURI__.invoke(cmd, args);
  }
  return Promise.resolve(null);
};

// UI Elements
const workView = document.getElementById('workView');
const noteModal = document.getElementById('noteModal');
const breakView = document.getElementById('breakView');

const workTimer = document.getElementById('workTimer');
const breakTimer = document.getElementById('breakTimer');
const cycleBadge = document.getElementById('cycleBadge');
const workStreakBadge = document.getElementById('workStreakBadge');
const streakBadge = document.getElementById('streakBadge');

const topNavSystemPill = document.getElementById('topNavSystemPill');
const workSystemPill = document.getElementById('workSystemPill');
const breakSystemBar = document.getElementById('breakSystemBar');
const twoMinToast = document.getElementById('twoMinToast');

const workSkipBadge = document.getElementById('workSkipBadge');
const workLockedBanner = document.getElementById('workLockedBanner');
const breakSkipCard = document.getElementById('breakSkipCard');
const breakSkipText = document.getElementById('breakSkipText');
const breakLockedAlert = document.getElementById('breakLockedAlert');
const breakResourceAlert = document.getElementById('breakResourceAlert');

const btnJumpBreak = document.getElementById('btnJumpBreak');
const sessionNoteInput = document.getElementById('sessionNoteInput');
const btnSubmitNote = document.getElementById('btnSubmitNote');
const noteCountdownSec = document.getElementById('noteCountdownSec');
const countdownStatus = document.getElementById('countdownStatus');
const countdownBar = document.getElementById('countdownBar');

const waterCountText = document.getElementById('waterCountText');
const btnAddWater = document.getElementById('btnAddWater');
const stretchPromptText = document.getElementById('stretchPromptText');
const coachingQuoteText = document.getElementById('coachingQuoteText');
const kpiSummaryText = document.getElementById('kpiSummaryText');

const breakLengthLabel = document.getElementById('breakLengthLabel');
const nextWorkLabel = document.getElementById('nextWorkLabel');
const btnBreakMinus = document.getElementById('btnBreakMinus');
const btnBreakPlus = document.getElementById('btnBreakPlus');
const btnWorkMinus = document.getElementById('btnWorkMinus');
const btnWorkPlus = document.getElementById('btnWorkPlus');

const ratingSection = document.getElementById('ratingSection');
const ratingStatusText = document.getElementById('ratingStatusText');
const starButtons = document.querySelectorAll('.star-btn');

const btnResumeWork = document.getElementById('btnResumeWork');
const btnExitApp = document.getElementById('btnExitApp');

// Daily Skip Configuration
const MAX_DAILY_SKIPS = 2;

function getDailySkipStorageKey() {
  const today = new Date().toISOString().slice(0, 10);
  return `pomodoro_daily_skips_${today}`;
}

function getDailySkipsUsed() {
  try {
    const val = localStorage.getItem(getDailySkipStorageKey());
    return val ? parseInt(val, 10) : 0;
  } catch (e) {
    return 0;
  }
}

function getSkipsRemaining() {
  return Math.max(0, MAX_DAILY_SKIPS - getDailySkipsUsed());
}

function recordDailySkip() {
  const nextUsed = getDailySkipsUsed() + 1;
  try {
    localStorage.setItem(getDailySkipStorageKey(), String(nextUsed));
  } catch (e) {}
  updateSkipUI();
  return nextUsed;
}

function showSkipLimitReachedAlert() {
  const msg = 'You have reached the limit and now nothing can be done after this. You have to wait.';
  if (workLockedBanner) {
    workLockedBanner.classList.remove('hidden');
    workLockedBanner.textContent = `🔒 ${msg}`;
  }
  if (breakLockedAlert) {
    breakLockedAlert.classList.remove('hidden');
    breakLockedAlert.textContent = `🔒 ${msg}`;
  }
  alert(`🔒 Daily Skip Limit Reached (2/2 Used)\n\n${msg}`);
}

function updateSkipUI() {
  const left = getSkipsRemaining();
  const isLocked = (left <= 0);

  if (workSkipBadge) {
    workSkipBadge.textContent = isLocked ? '🔒 Daily Skip Limit Reached (2/2)' : `⚡ Daily Skips Left: ${left}/2`;
    workSkipBadge.className = isLocked ? 'skip-pill locked' : 'skip-pill';
  }

  if (workLockedBanner) {
    if (isLocked) {
      workLockedBanner.classList.remove('hidden');
    } else {
      workLockedBanner.classList.add('hidden');
    }
  }

  if (btnJumpBreak) {
    if (isLocked) {
      btnJumpBreak.disabled = true;
      btnJumpBreak.classList.add('btn-disabled');
      btnJumpBreak.textContent = '🔒 Locked (Limit Reached 2/2)';
    } else {
      btnJumpBreak.disabled = false;
      btnJumpBreak.classList.remove('btn-disabled');
      btnJumpBreak.textContent = `⚡ Go On Break Now (${left}/2 Skips Left)`;
    }
  }

  if (breakSkipText) {
    breakSkipText.textContent = isLocked
      ? '🔒 DAILY SKIP LIMIT REACHED (2/2 USED) • SCREEN LOCKED'
      : `⚡ Daily Early Continues / Skips: ${left} of 2 Remaining Today`;
  }

  if (breakLockedAlert) {
    if (isLocked && appState.phase === 'Break' && appState.remaining_seconds > 0) {
      breakLockedAlert.classList.remove('hidden');
    } else {
      breakLockedAlert.classList.add('hidden');
    }
  }

  if (btnResumeWork) {
    if (appState.phase === 'Break' && appState.remaining_seconds > 0) {
      if (isLocked) {
        btnResumeWork.disabled = true;
        btnResumeWork.classList.add('btn-disabled');
        btnResumeWork.textContent = '🔒 LOCKED: LIMIT REACHED — YOU HAVE TO WAIT';
      } else {
        btnResumeWork.disabled = false;
        btnResumeWork.classList.remove('btn-disabled');
        btnResumeWork.textContent = `⚡ RESUME WORK EARLY (${left}/2 Skips Left)`;
      }
    } else if (appState.remaining_seconds <= 0) {
      btnResumeWork.disabled = false;
      btnResumeWork.classList.remove('btn-disabled');
      btnResumeWork.textContent = '⚡ RESUME NEXT WORK SESSION (Break Complete ✓)';
    }
  }
}

// Local State
let appState = {
  phase: 'Work',
  remaining_seconds: 40 * 60,
  planned_work_seconds: 40 * 60,
  cycle: 1,
  productivity_rating: 4,
  hydration_cups: 0,
  warning_2min_shown: false,
};

let noteCountdown = 10;
let noteTimerPaused = false;
let noteInterval = null;

// Productivity & Wellness Cues
const STRETCH_CUES = [
  'Roll your shoulders back 5 times and gaze 20 feet away to relax eye muscles.',
  'Stand up, interlace your hands above your head, and stretch your spine upward.',
  'Perform a gentle neck roll: ear to shoulder on each side for 10 seconds.',
  'Rest your wrists: extend your arm forward and gently pull back your fingers.',
  'Take 3 slow deep breaths: 4s in, 4s hold, 6s exhale to reset your nervous system.',
];

const COACHING_CUES = [
  'Small daily focus blocks compound into massive lifelong mastery.',
  'Consistency beats intensity. You showed up today—that is what counts.',
  'Deep focus is a superpower in a world full of noisy distractions.',
  'Energy management is focus management. Rest without guilt.',
  'Every single pomodoro finished builds unstoppable momentum.',
];

function formatTime(seconds) {
  const m = Math.floor(Math.max(0, seconds) / 60);
  const s = Math.max(0, seconds) % 60;
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

function show2MinWarningToast() {
  if (!twoMinToast) return;
  twoMinToast.classList.remove('hidden');
  setTimeout(() => {
    twoMinToast.classList.add('hidden');
  }, 5000);
}

function updateView(state) {
  appState = Object.assign(appState, state);
  cycleBadge.textContent = `Cycle #${state.cycle}`;

  if (state.phase === 'Work') {
    workView.classList.remove('hidden');
    noteModal.classList.add('hidden');
    breakView.classList.add('hidden');
    workTimer.textContent = formatTime(state.remaining_seconds);

    // 2-Minute warning check
    if (state.remaining_seconds <= 120 && !appState.warning_2min_shown) {
      appState.warning_2min_shown = true;
      show2MinWarningToast();
    }
  } else if (state.phase === 'NotePrompt') {
    workView.classList.add('hidden');
    noteModal.classList.remove('hidden');
    breakView.classList.add('hidden');
  } else if (state.phase === 'Break') {
    workView.classList.add('hidden');
    noteModal.classList.add('hidden');
    breakView.classList.remove('hidden');
    breakTimer.textContent = formatTime(state.remaining_seconds);
    breakLengthLabel.textContent = formatTime(state.remaining_seconds);
    nextWorkLabel.textContent = formatTime(state.planned_work_seconds || 40 * 60);
  }

  updateSkipUI();
}

// System Performance Metrics
async function updateSystemMetrics() {
  try {
    let metrics = await invoke('get_system_metrics');
    if (!metrics) {
      // Fallback display if running in pure browser preview
      metrics = {
        cpu_percent: 14.5,
        memory_percent: 46.2,
        memory_used_gb: 7.1,
        memory_total_gb: 15.3,
        network_status: 'Online (22ms)',
        is_high_usage: false,
      };
    }

    const sysText = `💻 CPU: ${Math.round(metrics.cpu_percent)}% • RAM: ${Math.round(metrics.memory_percent)}% (${metrics.memory_used_gb}/${metrics.memory_total_gb} GB) • 🌐 ${metrics.network_status}`;

    if (topNavSystemPill) topNavSystemPill.textContent = sysText;
    if (workSystemPill) workSystemPill.textContent = sysText;
    if (breakSystemBar) breakSystemBar.textContent = sysText;

    if (breakResourceAlert) {
      if (metrics.is_high_usage) {
        breakResourceAlert.classList.remove('hidden');
        breakResourceAlert.textContent = `⚠️ High System Resource Usage (CPU at ${Math.round(metrics.cpu_percent)}%, RAM at ${Math.round(metrics.memory_percent)}%). Please cancel or close heavy applications to avoid lag.`;
      } else {
        breakResourceAlert.classList.add('hidden');
      }
    }
  } catch (e) {}
}

// Fetch and Render Dashboard Charts
async function refreshDashboard() {
  try {
    const stats = await invoke('get_stats');
    if (!stats) return;

    streakBadge.textContent = `🔥 ${stats.streak_days} Days Streak`;
    workStreakBadge.textContent = `🔥 Consistency Streak: ${stats.streak_days} Days Active`;

    kpiSummaryText.textContent = `TOTAL FOCUS: ${stats.total_work_formatted}  |  SESSIONS: ${stats.total_sessions}  |  TOP DAY: ${stats.top_day}  |  ALL-TIME RATING: ${stats.total_rating}`;

    // Render Canvas Charts
    if (window.charts) {
      window.charts.drawDailyChart('canvasDaily', stats.daily_chart);
      window.charts.drawRatingsChart('canvasRatings', stats.ratings_distribution);
      window.charts.drawTriggersChart('canvasTriggers', stats.trigger_distribution);
      window.charts.drawCumulativeChart('canvasCumulative', stats.cumulative_chart);
    }
  } catch (err) {
    console.error('Error fetching stats:', err);
  }
}

// 10-Second Note Auto-Dismiss Countdown
function startNoteCountdown() {
  noteCountdown = 10;
  noteTimerPaused = false;
  countdownBar.style.width = '100%';
  noteCountdownSec.textContent = noteCountdown;
  countdownStatus.textContent = `⏱️ Auto-continuing in ${noteCountdown}s... (Start typing to pause)`;
  countdownStatus.style.color = 'var(--accent-amber)';

  if (noteInterval) clearInterval(noteInterval);

  noteInterval = setInterval(() => {
    if (noteTimerPaused) return;

    noteCountdown -= 1;
    noteCountdownSec.textContent = Math.max(0, noteCountdown);
    countdownBar.style.width = `${(noteCountdown / 10) * 100}%`;

    if (noteCountdown <= 0) {
      clearInterval(noteInterval);
      submitNoteNow();
    }
  }, 1000);
}

function pauseNoteCountdown() {
  if (!noteTimerPaused) {
    noteTimerPaused = true;
    countdownStatus.textContent = '✍️ Countdown paused — take your time writing!';
    countdownStatus.style.color = 'var(--accent-emerald)';
  }
}

async function submitNoteNow() {
  if (noteInterval) clearInterval(noteInterval);
  const noteText = sessionNoteInput.value.trim();
  sessionNoteInput.value = '';

  const randStretch = STRETCH_CUES[Math.floor(Math.random() * STRETCH_CUES.length)];
  const randQuote = COACHING_CUES[Math.floor(Math.random() * COACHING_CUES.length)];
  stretchPromptText.textContent = randStretch;
  coachingQuoteText.textContent = randQuote;

  // Streamlined focus rating defaults to 4
  appState.productivity_rating = 4;
  starButtons.forEach(btn => {
    const star = parseInt(btn.getAttribute('data-star'), 10);
    if (star === 4) btn.classList.add('active');
    else btn.classList.remove('active');
  });

  const newState = await invoke('submit_note', { note: noteText });
  if (newState) {
    updateView(newState);
    refreshDashboard();
  }
}

// Event Listeners
sessionNoteInput.addEventListener('keydown', pauseNoteCountdown);
sessionNoteInput.addEventListener('focus', pauseNoteCountdown);
sessionNoteInput.addEventListener('click', pauseNoteCountdown);

btnSubmitNote.addEventListener('click', submitNoteNow);

btnJumpBreak.addEventListener('click', async () => {
  const left = getSkipsRemaining();
  if (left <= 0) {
    showSkipLimitReachedAlert();
    return;
  }
  recordDailySkip();
  const state = await invoke('jump_to_break');
  if (state) {
    updateView(state);
    startNoteCountdown();
  }
});

btnAddWater.addEventListener('click', async () => {
  const count = await invoke('log_water');
  if (count !== null) {
    waterCountText.textContent = `${count} Cups Logged 💧`;
  }
});

btnBreakMinus.addEventListener('click', async () => {
  const newSec = await invoke('adjust_break', { deltaSeconds: -60 });
  if (newSec) breakLengthLabel.textContent = formatTime(newSec);
});

btnBreakPlus.addEventListener('click', async () => {
  const newSec = await invoke('adjust_break', { deltaSeconds: 60 });
  if (newSec) breakLengthLabel.textContent = formatTime(newSec);
});

btnWorkMinus.addEventListener('click', async () => {
  const newSec = await invoke('adjust_next_work', { deltaSeconds: -300 });
  if (newSec) nextWorkLabel.textContent = formatTime(newSec);
});

btnWorkPlus.addEventListener('click', async () => {
  const newSec = await invoke('adjust_next_work', { deltaSeconds: 300 });
  if (newSec) nextWorkLabel.textContent = formatTime(newSec);
});

// Star Rating Buttons (1-click intuitive update)
starButtons.forEach(btn => {
  btn.addEventListener('click', async () => {
    const val = parseInt(btn.getAttribute('data-star'), 10);
    try {
      await invoke('set_rating', { rating: val });
      appState.productivity_rating = val;

      starButtons.forEach(b => {
        const star = parseInt(b.getAttribute('data-star'), 10);
        if (star === val) b.classList.add('active');
        else b.classList.remove('active');
      });

      ratingStatusText.className = 'rating-status-unlocked';
      ratingStatusText.textContent = `Selected: 💻 Deep Work (✓)  •  Rating: ${val}★ (Confirmed ✓)`;
    } catch (err) {
      console.error(err);
    }
  });
});

// Resume Button with Daily Skip Gate
btnResumeWork.addEventListener('click', async () => {
  if (appState.phase === 'Break' && appState.remaining_seconds > 0) {
    const left = getSkipsRemaining();
    if (left <= 0) {
      showSkipLimitReachedAlert();
      return;
    }
    recordDailySkip();
  }

  try {
    const state = await invoke('resume_work');
    if (state) {
      updateView(state);
    }
  } catch (err) {
    console.error(err);
  }
});

btnExitApp.addEventListener('click', async () => {
  if (appState.phase === 'Break' && appState.remaining_seconds > 0) {
    const left = getSkipsRemaining();
    if (left <= 0) {
      showSkipLimitReachedAlert();
      return;
    }
  }
  try {
    await invoke('exit_app');
  } catch (err) {
    console.error(err);
  }
});

// 1-Second Polling & Metrics
setInterval(async () => {
  try {
    const state = await invoke('get_state');
    if (state) {
      if (appState.phase !== 'NotePrompt' && state.phase === 'NotePrompt') {
        startNoteCountdown();
      }
      updateView(state);
    }
  } catch (err) {}
  updateSystemMetrics();
}, 1000);

// Initial Boot
(async () => {
  try {
    const state = await invoke('get_state');
    if (state) {
      updateView(state);
    }
    refreshDashboard();
  } catch (err) {
    console.log('Running in browser preview mode');
  }
  updateSkipUI();
  updateSystemMetrics();
})();
