use chrono::{Local, NaiveDate, Utc};
use fs2::FileExt;
use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, HashMap, HashSet};
use std::fs::{self, File, OpenOptions};
use std::io::Write;
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SessionRecord {
    #[serde(rename = "sessionId")]
    pub session_id: String,
    pub cycle: i64,
    #[serde(rename = "sessionStartedAt")]
    pub session_started_at: String,
    #[serde(rename = "sessionCompletedAt")]
    pub session_completed_at: String,
    #[serde(rename = "workTimeMinutes")]
    pub work_time_minutes: f64,
    #[serde(rename = "workTimeSeconds")]
    pub work_time_seconds: i64,
    #[serde(rename = "breakTimeMinutes")]
    pub break_time_minutes: f64,
    #[serde(rename = "breakTimeSeconds")]
    pub break_time_seconds: i64,
    #[serde(rename = "plannedWorkSeconds")]
    pub planned_work_seconds: i64,
    #[serde(rename = "plannedBreakSeconds")]
    pub planned_break_seconds: i64,
    #[serde(rename = "workEndedBy")]
    pub work_ended_by: String,
    #[serde(rename = "breakEndedBy")]
    pub break_ended_by: String,
    #[serde(rename = "sessionNote", default)]
    pub session_note: Option<String>,
    #[serde(rename = "productivityRating", default)]
    pub productivity_rating: Option<i64>,
    #[serde(rename = "sessionInterruptedBySleep", default)]
    pub session_interrupted_by_sleep: Option<bool>,
    #[serde(rename = "interactionLog", default)]
    pub interaction_log: serde_json::Value,
    #[serde(rename = "syncStatus", default = "default_sync_status")]
    pub sync_status: String,
}

fn default_sync_status() -> String {
    "pending".to_string()
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LogData {
    #[serde(rename = "appName")]
    pub app_name: String,
    #[serde(rename = "createdAt")]
    pub created_at: String,
    #[serde(default)]
    pub events: Vec<SessionRecord>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChartPoint {
    pub date: String,
    pub value: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SummaryStats {
    pub today_sessions: usize,
    pub today_work_formatted: String,
    pub today_break_formatted: String,
    pub today_rating: String,
    pub total_sessions: usize,
    pub total_work_formatted: String,
    pub total_rating: String,
    pub top_day: String,
    pub streak_days: usize,
    pub timer_pct: f64,
    pub sleep_pct: f64,
    pub manual_pct: f64,
    pub daily_chart: Vec<ChartPoint>,
    pub cumulative_chart: Vec<ChartPoint>,
    pub ratings_distribution: HashMap<String, usize>,
    pub trigger_distribution: HashMap<String, usize>,
}

pub fn get_log_path() -> PathBuf {
    let candidates = [
        PathBuf::from("pomodoro_log.json"),
        PathBuf::from("../pomodoro_log.json"),
    ];
    for p in &candidates {
        if p.exists() {
            return p.clone();
        }
    }
    PathBuf::from("pomodoro_log.json")
}

pub fn get_lock_file() -> Option<File> {
    let lock_path = if let Ok(cache) = std::env::var("XDG_CACHE_HOME") {
        PathBuf::from(cache).join("pomodoro/pomodoro.lock")
    } else if let Ok(home) = std::env::var("HOME") {
        PathBuf::from(home).join(".cache/pomodoro/pomodoro.lock")
    } else {
        PathBuf::from("/tmp/pomodoro.lock")
    };

    if let Some(parent) = lock_path.parent() {
        let _ = fs::create_dir_all(parent);
    }

    if let Ok(file) = OpenOptions::new()
        .read(true)
        .write(true)
        .create(true)
        .open(&lock_path)
    {
        if file.try_lock_exclusive().is_ok() {
            return Some(file);
        }
    }
    None
}

pub fn load_log() -> LogData {
    let path = get_log_path();
    if path.exists() {
        if let Ok(content) = fs::read_to_string(&path) {
            if let Ok(data) = serde_json::from_str::<LogData>(&content) {
                return data;
            }
        }
    }
    LogData {
        app_name: "pomodoro".to_string(),
        created_at: Utc::now().to_rfc3339(),
        events: Vec::new(),
    }
}

pub fn save_log(data: &LogData) -> Result<(), String> {
    let path = get_log_path();
    let tmp_path = path.with_extension("json.tmp");

    let json_bytes = serde_json::to_vec_pretty(data)
        .map_err(|e| format!("Serialization error: {}", e))?;

    let mut file = File::create(&tmp_path)
        .map_err(|e| format!("Failed to create tmp file: {}", e))?;
    file.write_all(&json_bytes)
        .map_err(|e| format!("Failed to write tmp file: {}", e))?;
    file.sync_all()
        .map_err(|e| format!("Failed to sync tmp file: {}", e))?;

    fs::rename(&tmp_path, &path)
        .map_err(|e| format!("Atomic rename failed: {}", e))?;
    Ok(())
}

pub fn append_session(record: SessionRecord) -> Result<(), String> {
    let mut log = load_log();
    log.events.push(record);
    save_log(&log)
}

fn format_duration(seconds: i64) -> String {
    let mins = (seconds as f64 / 60.0).round() as i64;
    if mins < 60 {
        format!("{}m", mins)
    } else {
        let hrs = mins / 60;
        let rem = mins % 60;
        if rem == 0 {
            format!("{}h", hrs)
        } else {
            format!("{}h {}m", hrs, rem)
        }
    }
}

pub fn compute_stats(current_work_seconds: i64) -> SummaryStats {
    let log = load_log();
    let today_str = Local::now().format("%Y-%m-%d").to_string();

    let mut today_sessions = 0;
    let mut today_work_sec = current_work_seconds;
    let mut today_break_sec = 0;
    let mut today_ratings = Vec::new();

    let mut total_sessions = 0;
    let mut total_work_sec = current_work_seconds;
    let mut total_ratings = Vec::new();

    let mut daily_work: BTreeMap<String, i64> = BTreeMap::new();
    let mut trigger_counts: HashMap<String, usize> = HashMap::new();
    let mut rating_counts: HashMap<String, usize> = HashMap::new();

    for i in 1..=5 {
        rating_counts.insert(format!("{} Star", i), 0);
    }
    trigger_counts.insert("timer".to_string(), 0);
    trigger_counts.insert("systemSleep".to_string(), 0);
    trigger_counts.insert("userBreakNow".to_string(), 0);

    for ev in &log.events {
        total_sessions += 1;
        total_work_sec += ev.work_time_seconds;

        let end_reason = ev.work_ended_by.as_str();
        *trigger_counts.entry(end_reason.to_string()).or_insert(0) += 1;

        if let Some(r) = ev.productivity_rating {
            if r > 0 {
                total_ratings.push(r as f64);
                let key = format!("{} Star", r);
                *rating_counts.entry(key).or_insert(0) += 1;
            }
        }

        let date_str = if ev.session_started_at.len() >= 10 {
            &ev.session_started_at[0..10]
        } else {
            ""
        };

        if !date_str.is_empty() {
            *daily_work.entry(date_str.to_string()).or_insert(0) += ev.work_time_seconds;

            if date_str == today_str {
                today_sessions += 1;
                today_work_sec += ev.work_time_seconds;
                today_break_sec += ev.break_time_seconds;
                if let Some(r) = ev.productivity_rating {
                    if r > 0 {
                        today_ratings.push(r as f64);
                    }
                }
            }
        }
    }

    if current_work_seconds > 0 {
        today_sessions += 1;
        total_sessions += 1;
        *daily_work.entry(today_str.clone()).or_insert(0) += current_work_seconds;
    }

    // Top Day Calculation
    let mut top_day = "N/A".to_string();
    if let Some((top_date, max_secs)) = daily_work.iter().max_by_key(|(_, s)| *s) {
        if let Ok(parsed) = NaiveDate::parse_from_str(top_date, "%Y-%m-%d") {
            top_day = format!("{} ({})", format_duration(*max_secs), parsed.format("%b %d, %Y"));
        } else {
            top_day = format!("{} ({})", format_duration(*max_secs), top_date);
        }
    }

    // Streak Calculation
    let dates_set: HashSet<String> = daily_work.keys().cloned().collect();
    let mut streak = 0;
    let mut check_date = Local::now().date_naive();
    if !dates_set.contains(&check_date.format("%Y-%m-%d").to_string()) {
        check_date = check_date.pred_opt().unwrap_or(check_date);
    }
    while dates_set.contains(&check_date.format("%Y-%m-%d").to_string()) {
        streak += 1;
        if let Some(prev) = check_date.pred_opt() {
            check_date = prev;
        } else {
            break;
        }
    }

    // Trigger percentages
    let total_triggers: usize = trigger_counts.values().sum();
    let total_trig_f = if total_triggers > 0 { total_triggers as f64 } else { 1.0 };
    let timer_pct = ((*trigger_counts.get("timer").unwrap_or(&0) as f64) / total_trig_f * 100.0).round();
    let sleep_pct = ((*trigger_counts.get("systemSleep").unwrap_or(&0) as f64) / total_trig_f * 100.0).round();
    let manual_pct = ((*trigger_counts.get("userBreakNow").unwrap_or(&0) as f64) / total_trig_f * 100.0).round();

    let today_rating_str = if !today_ratings.is_empty() {
        let avg = today_ratings.iter().sum::<f64>() / today_ratings.len() as f64;
        format!("{:.1}★", avg)
    } else {
        "N/A".to_string()
    };

    let total_rating_str = if !total_ratings.is_empty() {
        let avg = total_ratings.iter().sum::<f64>() / total_ratings.len() as f64;
        format!("{:.1}★", avg)
    } else {
        "N/A".to_string()
    };

    // Chart points: Daily & Cumulative
    let mut daily_chart = Vec::new();
    let mut cumulative_chart = Vec::new();
    let mut running_cum_hours = 0.0;

    // Take the last 30 active days for responsive daily chart
    let daily_entries: Vec<(&String, &i64)> = daily_work.iter().collect();
    let start_idx = if daily_entries.len() > 40 { daily_entries.len() - 40 } else { 0 };

    for (d, sec) in &daily_entries[start_idx..] {
        let hrs = (**sec as f64 / 3600.0 * 10.0).round() / 10.0;
        daily_chart.push(ChartPoint {
            date: d.to_string(),
            value: hrs,
        });
    }

    for (d, sec) in daily_work.iter() {
        running_cum_hours += *sec as f64 / 3600.0;
        cumulative_chart.push(ChartPoint {
            date: d.clone(),
            value: (running_cum_hours * 10.0).round() / 10.0,
        });
    }

    SummaryStats {
        today_sessions,
        today_work_formatted: format_duration(today_work_sec),
        today_break_formatted: format_duration(today_break_sec),
        today_rating: today_rating_str,
        total_sessions,
        total_work_formatted: format_duration(total_work_sec),
        total_rating: total_rating_str,
        top_day,
        streak_days: streak,
        timer_pct,
        sleep_pct,
        manual_pct,
        daily_chart,
        cumulative_chart,
        ratings_distribution: rating_counts,
        trigger_distribution: trigger_counts,
    }
}
