use tauri::Manager;
use tauri_plugin_shell::ShellExt;

/// Avoid Errno 48 (address already in use) when a stray backend or prior run still holds :8000.
fn free_backend_listen_port() {
    #[cfg(all(unix, not(target_os = "ios"), not(target_os = "android")))]
    {
        let _ = std::process::Command::new("sh")
            .arg("-c")
            .arg("lsof -ti :8000 | xargs kill -9 2>/dev/null; true")
            .status();
        std::thread::sleep(std::time::Duration::from_millis(300));
    }
    #[cfg(windows)]
    {
        let ps = concat!(
            "$c = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue; ",
            "if ($c) { $c | ForEach-Object { ",
            "Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue } }",
        );
        let _ = std::process::Command::new("powershell")
            .args(["-NoProfile", "-Command", ps])
            .status();
        std::thread::sleep(std::time::Duration::from_millis(300));
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            free_backend_listen_port();

            let shell = app.shell();
            let sidecar = shell
                .sidecar("fileai-backend")
                .expect("failed to create fileai-backend sidecar command");

            let (mut rx, _child) = sidecar
                .spawn()
                .expect("failed to spawn fileai-backend");

            tauri::async_runtime::spawn(async move {
                use tauri_plugin_shell::process::CommandEvent;
                while let Some(event) = rx.recv().await {
                    match event {
                        CommandEvent::Stdout(line) => {
                            let s = String::from_utf8_lossy(&line);
                            println!("[backend] {}", s);
                        }
                        CommandEvent::Stderr(line) => {
                            let s = String::from_utf8_lossy(&line);
                            eprintln!("[backend] {}", s);
                        }
                        CommandEvent::Terminated(payload) => {
                            eprintln!("[backend] terminated: {:?}", payload);
                        }
                        _ => {}
                    }
                }
            });

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
