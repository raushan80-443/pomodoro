use chrono::Utc;
use serde::{Deserialize, Serialize};

pub const DEFAULT_WORK_SECONDS: i64 = 40 * 60;
pub const DEFAULT_BREAK_SECONDS: i64 = 4 * 60;
pub const SUSPEND_GAP_SECONDS: i64 = 10;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum Phase {
    Work,
    NotePrompt,
    Break,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppStateSnapshot {
    pub phase: Phase,
    pub remaining_seconds: i64,
    pub planned_work_seconds: i64,
    pub actual_work_seconds: i64,
    pub planned_break_seconds: i64,
    pub actual_break_seconds: i64,
    pub cycle: i64,
    pub session_started_at: String,
    pub session_note: String,
    pub productivity_rating: Option<i64>,
    pub is_paused: bool,
    pub hydration_cups: usize,
}

pub struct PomodoroEngine {
    pub phase: Phase,
    pub remaining_seconds: i64,
    pub planned_work_seconds: i64,
    pub actual_work_seconds: i64,
    pub planned_break_seconds: i64,
    pub actual_break_seconds: i64,
    pub cycle: i64,
    pub session_started_at: String,
    pub session_note: String,
    pub productivity_rating: Option<i64>,
    pub is_paused: bool,
    pub hydration_cups: usize,
    pub beep_1min_played: bool,
    pub beep_20sec_played: bool,
}

impl PomodoroEngine {
    pub fn new() -> Self {
        Self {
            phase: Phase::Work,
            remaining_seconds: DEFAULT_WORK_SECONDS,
            planned_work_seconds: DEFAULT_WORK_SECONDS,
            actual_work_seconds: 0,
            planned_break_seconds: DEFAULT_BREAK_SECONDS,
            actual_break_seconds: 0,
            cycle: 1,
            session_started_at: Utc::now().to_rfc3339(),
            session_note: String::new(),
            productivity_rating: None,
            is_paused: false,
            hydration_cups: 0,
            beep_1min_played: false,
            beep_20sec_played: false,
        }
    }

    pub fn snapshot(&self) -> AppStateSnapshot {
        AppStateSnapshot {
            phase: self.phase,
            remaining_seconds: self.remaining_seconds,
            planned_work_seconds: self.planned_work_seconds,
            actual_work_seconds: self.actual_work_seconds,
            planned_break_seconds: self.planned_break_seconds,
            actual_break_seconds: self.actual_break_seconds,
            cycle: self.cycle,
            session_started_at: self.session_started_at.clone(),
            session_note: self.session_note.clone(),
            productivity_rating: self.productivity_rating,
            is_paused: self.is_paused,
            hydration_cups: self.hydration_cups,
        }
    }

    pub fn jump_to_break(&mut self) {
        self.phase = Phase::NotePrompt;
        self.remaining_seconds = 10;
    }

    pub fn submit_note_and_start_break(&mut self, note: String) {
        self.session_note = note;
        self.phase = Phase::Break;
        self.remaining_seconds = self.planned_break_seconds;
        self.productivity_rating = None;
        self.beep_20sec_played = false;
    }

    pub fn resume_next_work_cycle(&mut self) {
        self.cycle += 1;
        self.phase = Phase::Work;
        self.remaining_seconds = self.planned_work_seconds;
        self.actual_work_seconds = 0;
        self.actual_break_seconds = 0;
        self.session_started_at = Utc::now().to_rfc3339();
        self.session_note.clear();
        self.productivity_rating = None;
        self.beep_1min_played = false;
        self.beep_20sec_played = false;
    }
}
