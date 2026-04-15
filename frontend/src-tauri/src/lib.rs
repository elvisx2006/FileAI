use tauri::Manager;
use tauri_plugin_shell::ShellExt;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
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
