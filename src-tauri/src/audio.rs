use std::path::Path;
use std::process::Command;

pub fn play_beep() -> bool {
    let sound_files = [
        "/usr/share/sounds/freedesktop/stereo/bell.oga",
        "/usr/share/sounds/freedesktop/stereo/message.oga",
        "/usr/share/sounds/oxygen/stereo/dialog-information.ogg",
        "/usr/share/sounds/Oxygen-Sys-Special.ogg",
        "/usr/share/sounds/alsa/Front_Center.wav",
    ];

    for player in ["pw-play", "paplay", "aplay"] {
        for sound_file in &sound_files {
            if Path::new(sound_file).exists() {
                if let Ok(mut child) = Command::new(player)
                    .arg(sound_file)
                    .stdout(std::process::Stdio::null())
                    .stderr(std::process::Stdio::null())
                    .spawn()
                {
                    std::thread::spawn(move || {
                        let _ = child.wait();
                    });
                    return true;
                }
            }
        }
    }

    // Fallback: spd-say
    if let Ok(mut child) = Command::new("spd-say")
        .args(["-t", "female1", "beep"])
        .stdout(std::process::Stdio::null())
        .stderr(std::process::Stdio::null())
        .spawn()
    {
        std::thread::spawn(move || {
            let _ = child.wait();
        });
        return true;
    }

    // Fallback: Terminal Bell
    print!("\x07");
    true
}

pub fn play_countdown_alert() {
    print!("\x07");
}
