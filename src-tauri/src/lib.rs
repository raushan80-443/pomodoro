mod audio;
mod storage;
mod timer;

use chrono::Utc;
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};
use tauri::{AppHandle, Emitter, Manager, State, Window};
use timer::{AppStateSnapshot, Phase, PomodoroEngine, SUSPEND_GAP_SECONDS};
use uuid::Uuid;

struct AppContext {
    engine: Mutex<PomodoroEngine>,
    _lock_file: Option<std::fs::File>,
}

#[tauri::command]
fn get_state(state: State<Arc<AppContext>>) -> AppStateSnapshot {
    let engine = state.engine.lock().unwrap();
    engine.snapshot()
}

#[tauri::command]
fn get_stats(state: State<Arc<AppContext>>) -> storage::SummaryStats {
    let engine = state.engine.lock().unwrap();
    let current_work = if engine.phase == Phase::Work {
        engine.actual_work_seconds
    } else {
        0
    };
    storage::compute_stats(current_work)
}

#[tauri::command]
fn jump_to_break(window: Window, state: State<Arc<AppContext>>) -> AppStateSnapshot {
    let mut engine = state.engine.lock().unwrap();
    engine.jump_to_break();
    let _ = window.set_fullscreen(false);
    let _ = window.set_always_on_top(true);
    let _ = window.set_focus();
    let _ = window.center();
    audio::play_beep();
    engine.snapshot()
}

#[tauri::command]
fn submit_note(window: Window, note: String, state: State<Arc<AppContext>>) -> AppStateSnapshot {
    let mut engine = state.engine.lock().unwrap();
    engine.submit_note_and_start_break(note);
    let _ = window.set_fullscreen(true);
    let _ = window.set_always_on_top(true);
    let _ = window.set_focus();
    engine.snapshot()
}

#[tauri::command]
fn set_rating(rating: i64, state: State<Arc<AppContext>>) -> Result<(), String> {
    if !(1..=5).contains(&rating) {
        return Err("Rating must be between 1 and 5".to_string());
    }
    let mut engine = state.engine.lock().unwrap();
    engine.productivity_rating = Some(rating);
    Ok(())
}

#[tauri::command]
fn adjust_break(delta_seconds: i64, state: State<Arc<AppContext>>) -> i64 {
    let mut engine = state.engine.lock().unwrap();
    let new_val = (engine.remaining_seconds + delta_seconds).max(60);
    engine.remaining_seconds = new_val;
    new_val
}

#[tauri::command]
fn adjust_next_work(delta_seconds: i64, state: State<Arc<AppContext>>) -> i64 {
    let mut engine = state.engine.lock().unwrap();
    let new_val = (engine.planned_work_seconds + delta_seconds).max(60);
    engine.planned_work_seconds = new_val;
    new_val
}

#[tauri::command]
fn log_water(state: State<Arc<AppContext>>) -> usize {
    let mut engine = state.engine.lock().unwrap();
    engine.hydration_cups += 1;
    engine.hydration_cups
}

#[tauri::command]
fn resume_work(window: Window, state: State<Arc<AppContext>>) -> Result<AppStateSnapshot, String> {
    let mut engine = state.engine.lock().unwrap();
    if engine.productivity_rating.is_none() {
        return Err("Productivity rating is mandatory before resuming work".to_string());
    }

    let record = storage::SessionRecord {
        session_id: Uuid::new_v4().to_string(),
        cycle: engine.cycle,
        session_started_at: engine.session_started_at.clone(),
        session_completed_at: Utc::now().to_rfc3339(),
        work_time_minutes: (engine.actual_work_seconds as f64 / 60.0 * 100.0).round() / 100.0,
        work_time_seconds: engine.actual_work_seconds,
        break_time_minutes: (engine.actual_break_seconds as f64 / 60.0 * 100.0).round() / 100.0,
        break_time_seconds: engine.actual_break_seconds,
        planned_work_seconds: engine.planned_work_seconds,
        planned_break_seconds: engine.planned_break_seconds,
        work_ended_by: "timer".to_string(),
        break_ended_by: "userResume".to_string(),
        session_note: if engine.session_note.is_empty() { None } else { Some(engine.session_note.clone()) },
        productivity_rating: engine.productivity_rating,
        session_interrupted_by_sleep: Some(false),
        interaction_log: serde_json::json!([]),
        sync_status: "pending".to_string(),
    };
    let _ = storage::append_session(record);

    engine.resume_next_work_cycle();
    let _ = window.set_fullscreen(false);
    let _ = window.set_always_on_top(false);
    let _ = window.center();

    Ok(engine.snapshot())
}

#[tauri::command]
fn exit_app(window: Window, state: State<Arc<AppContext>>) -> Result<(), String> {
    let engine = state.engine.lock().unwrap();
    if engine.phase == Phase::Break && engine.productivity_rating.is_none() {
        return Err("Productivity rating is mandatory before exiting".to_string());
    }

    if engine.actual_work_seconds > 0 || engine.actual_break_seconds > 0 {
        let record = storage::SessionRecord {
            session_id: Uuid::new_v4().to_string(),
            cycle: engine.cycle,
            session_started_at: engine.session_started_at.clone(),
            session_completed_at: Utc::now().to_rfc3339(),
            work_time_minutes: (engine.actual_work_seconds as f64 / 60.0 * 100.0).round() / 100.0,
            work_time_seconds: engine.actual_work_seconds,
            break_time_minutes: (engine.actual_break_seconds as f64 / 60.0 * 100.0).round() / 100.0,
            break_time_seconds: engine.actual_break_seconds,
            planned_work_seconds: engine.planned_work_seconds,
            planned_break_seconds: engine.planned_break_seconds,
            work_ended_by: if engine.phase == Phase::Work { "userExit".to_string() } else { "timer".to_string() },
            break_ended_by: "userExit".to_string(),
            session_note: if engine.session_note.is_empty() { None } else { Some(engine.session_note.clone()) },
            productivity_rating: engine.productivity_rating,
            session_interrupted_by_sleep: Some(false),
            interaction_log: serde_json::json!([]),
            sync_status: "pending".to_string(),
        };
        let _ = storage::append_session(record);
    }

    window.app_handle().exit(0);
    Ok(())
}

#[tauri::command]
fn test_sound() -> bool {
    audio::play_beep()
}

fn start_background_timer(app_handle: AppHandle, context: Arc<AppContext>) {
    std::thread::spawn(move || {
        let mut last_tick = Instant::now();

        loop {
            std::thread::sleep(Duration::from_millis(1000));
            let now = Instant::now();
            let elapsed = now.duration_since(last_tick).as_secs() as i64;
            let sleep_gap_detected = elapsed > SUSPEND_GAP_SECONDS;
            last_tick = now;

            let mut should_emit = false;
            let mut switch_to_prompt = false;

            {
                let mut engine = context.engine.lock().unwrap();

                if sleep_gap_detected {
                    if engine.phase == Phase::Work && engine.actual_work_seconds > 0 {
                        let record = storage::SessionRecord {
                            session_id: Uuid::new_v4().to_string(),
                            cycle: engine.cycle,
                            session_started_at: engine.session_started_at.clone(),
                            session_completed_at: Utc::now().to_rfc3339(),
                            work_time_minutes: (engine.actual_work_seconds as f64 / 60.0 * 100.0).round() / 100.0,
                            work_time_seconds: engine.actual_work_seconds,
                            break_time_minutes: 0.0,
                            break_time_seconds: 0,
                            planned_work_seconds: engine.planned_work_seconds,
                            planned_break_seconds: 0,
                            work_ended_by: "systemSleep".to_string(),
                            break_ended_by: "notStarted".to_string(),
                            session_note: None,
                            productivity_rating: None,
                            session_interrupted_by_sleep: Some(true),
                            interaction_log: serde_json::json!([]),
                            sync_status: "pending".to_string(),
                        };
                        let _ = storage::append_session(record);
                        engine.resume_next_work_cycle();
                        should_emit = true;
                    }
                }

                if !engine.is_paused {
                    match engine.phase {
                        Phase::Work => {
                            if engine.remaining_seconds > 0 {
                                engine.remaining_seconds -= 1;
                                engine.actual_work_seconds += 1;
                                should_emit = true;

                                if engine.remaining_seconds == 60 && !engine.beep_1min_played {
                                    engine.beep_1min_played = true;
                                    audio::play_beep();
                                } else if engine.remaining_seconds <= 3 && engine.remaining_seconds > 0 {
                                    audio::play_countdown_alert();
                                }
                            } else {
                                engine.phase = Phase::NotePrompt;
                                engine.remaining_seconds = 10;
                                switch_to_prompt = true;
                                should_emit = true;
                                audio::play_beep();
                            }
                        }
                        Phase::NotePrompt => {
                            should_emit = true;
                        }
                        Phase::Break => {
                            if engine.remaining_seconds > 0 {
                                engine.remaining_seconds -= 1;
                                engine.actual_break_seconds += 1;
                                should_emit = true;

                                if engine.remaining_seconds == 20 && !engine.beep_20sec_played {
                                    engine.beep_20sec_played = true;
                                    audio::play_beep();
                                } else if engine.remaining_seconds <= 3 && engine.remaining_seconds > 0 {
                                    audio::play_countdown_alert();
                                }
                            } else {
                                should_emit = true;
                            }
                        }
                    }
                }
            }

            if switch_to_prompt {
                if let Some(w) = app_handle.get_webview_window("main") {
                    let _ = w.set_fullscreen(false);
                    let _ = w.set_always_on_top(true);
                    let _ = w.show();
                    let _ = w.set_focus();
                    let _ = w.center();
                }
            }

            if should_emit {
                let _ = app_handle.emit("tick", ());
            }
        }
    });
}

pub fn run() {
    let lock_file = storage::get_lock_file();
    if lock_file.is_none() {
        eprintln!("Pomodoro is already running. Skipping duplicate instance.");
        std::process::exit(0);
    }

    let context = Arc::new(AppContext {
        engine: Mutex::new(PomodoroEngine::new()),
        _lock_file: lock_file,
    });

    tauri::Builder::default()
        .manage(context.clone())
        .invoke_handler(tauri::generate_handler![
            get_state,
            get_stats,
            jump_to_break,
            submit_note,
            set_rating,
            adjust_break,
            adjust_next_work,
            log_water,
            resume_work,
            exit_app,
            test_sound
        ])
        .setup(move |app| {
            start_background_timer(app.handle().clone(), context);
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
