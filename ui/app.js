// Pomodoro Frontend Reactive State & Tauri Command Bridge

const invoke = (cmd, args = {}) => {
  if (window.__TAURI__ && window.__TAURI__.core && window.__TAURI__.core.invoke) {
    return window.__TAURI__.core.invoke(cmd, args);
  }
  if (window.__TAURI__ && window.__TAURI__.invoke) {
    return window.__TAURI__.invoke(cmd, args);
  }
  console.log(`[Mock Invoke] ${cmd}`, args);
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

// Local State
let appState = {
  phase: 'Work',
  remaining_seconds: 40 * 60,
  cycle: 1,
  productivity_rating: null,
  hydration_cups: 0,
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

function updateView(state) {
  appState = state;
  cycleBadge.textContent = `Cycle #${state.cycle}`;

  if (state.phase === 'Work') {
    workView.classList.remove('hidden');
    noteModal.classList.add('hidden');
    breakView.classList.add('hidden');
    workTimer.textContent = formatTime(state.remaining_seconds);
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
    nextWorkLabel.textContent = formatTime(state.planned_work_seconds);
  }
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

  // Rotate wellness cues for break
  const randStretch = STRETCH_CUES[Math.floor(Math.random() * STRETCH_CUES.length)];
  const randQuote = COACHING_CUES[Math.floor(Math.random() * COACHING_CUES.length)];
  stretchPromptText.textContent = randStretch;
  coachingQuoteText.textContent = randQuote;

  // Reset rating state
  appState.productivity_rating = null;
  starButtons.forEach(btn => btn.classList.remove('active'));
  ratingStatusText.className = 'rating-status-warning';
  ratingStatusText.textContent = '⚠️ MANDATORY: Select a 1-5 ★ rating to enable Resume / Exit';

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
  const state = await invoke('jump_to_break');
  if (state) {
    updateView(state);
    startNoteCountdown();
  }
});

// Hydration Logger (+1 Cup)
btnAddWater.addEventListener('click', async () => {
  const count = await invoke('log_water');
  if (count !== null) {
    waterCountText.textContent = `${count} Cups Logged 💧`;
  }
});

// Break Length Adjusters
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

// Star Rating Buttons
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
      ratingStatusText.textContent = `Rating: ${val} ★ (Unlocked ✓)`;
    } catch (err) {
      console.error(err);
    }
  });
});

function flashRatingWarning() {
  ratingStatusText.className = 'rating-status-warning';
  ratingStatusText.textContent = '⚠️ MANDATORY RATING REQUIRED! Click 1-5 ★ rating first!';
  starButtons.forEach(btn => btn.classList.add('flash-warning'));
  setTimeout(() => {
    starButtons.forEach(btn => btn.classList.remove('flash-warning'));
  }, 700);
}

// Action Buttons
btnResumeWork.addEventListener('click', async () => {
  if (!appState.productivity_rating) {
    flashRatingWarning();
    return;
  }
  try {
    const state = await invoke('resume_work');
    if (state) {
      updateView(state);
    }
  } catch (err) {
    flashRatingWarning();
  }
});

btnExitApp.addEventListener('click', async () => {
  if (appState.phase === 'Break' && !appState.productivity_rating) {
    flashRatingWarning();
    return;
  }
  try {
    await invoke('exit_app');
  } catch (err) {
    flashRatingWarning();
  }
});

// Polling / Tick Listener
setInterval(async () => {
  try {
    const state = await invoke('get_state');
    if (state) {
      // Check if phase changed to NotePrompt from timer expiration
      if (appState.phase !== 'NotePrompt' && state.phase === 'NotePrompt') {
        startNoteCountdown();
      }
      updateView(state);
    }
  } catch (err) {}
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
})();
