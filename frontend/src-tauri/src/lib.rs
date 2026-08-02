use serde::{Deserialize, Serialize};
use std::{
    io::{Read, Write},
    net::{SocketAddr, TcpStream},
    sync::Mutex,
    time::Duration,
};
use tauri::{Manager, RunEvent, WindowEvent};
use tauri_plugin_shell::{
    process::{CommandChild, CommandEvent},
    ShellExt,
};
use uuid::Uuid;

const READY_PREFIX: &str = "OXO_DESKTOP_READY ";

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
struct DesktopBootstrap {
    api_base_url: String,
    token: String,
}

#[derive(Debug, Deserialize)]
struct ReadyPayload {
    host: String,
    port: u16,
}

#[derive(Default)]
struct DesktopState {
    bootstrap: Mutex<Option<DesktopBootstrap>>,
    child: Mutex<Option<CommandChild>>,
    startup_error: Mutex<Option<String>>,
}

#[tauri::command]
async fn desktop_bootstrap(
    state: tauri::State<'_, DesktopState>,
) -> Result<DesktopBootstrap, String> {
    for _ in 0..900 {
        if let Some(runtime) = state.bootstrap.lock().map_err(lock_error)?.clone() {
            return Ok(runtime);
        }
        if let Some(error) = state.startup_error.lock().map_err(lock_error)?.clone() {
            return Err(error);
        }
        tokio::time::sleep(Duration::from_millis(100)).await;
    }
    Err("Desktop API did not become ready within 90 seconds".into())
}

fn lock_error<T>(error: std::sync::PoisonError<T>) -> String {
    format!("Desktop runtime state is unavailable: {error}")
}

fn start_sidecar(app: &mut tauri::App) -> Result<(), Box<dyn std::error::Error>> {
    if connect_development_backend(app)
        .map_err(|error| std::io::Error::new(std::io::ErrorKind::Other, error))?
    {
        return Ok(());
    }

    let resource_root = app.path().resource_dir()?;
    // NSIS current-user installs live at %LOCALAPPDATA%\Oxo Tracker. Keep
    // mutable application data in Tauri's identifier-scoped directory so an
    // uninstall or reinstall never treats user data as application binaries.
    let app_home = app.path().app_local_data_dir()?;
    std::fs::create_dir_all(&app_home)?;

    let token = Uuid::new_v4().simple().to_string() + &Uuid::new_v4().simple().to_string();
    let challenge = Uuid::new_v4().simple().to_string();
    let version = app.package_info().version.to_string();
    let arguments = vec![
        "--token".to_string(),
        token.clone(),
        "--resource-root".to_string(),
        resource_root.to_string_lossy().into_owned(),
        "--app-home".to_string(),
        app_home.to_string_lossy().into_owned(),
        "--asset-version".to_string(),
        version,
    ];
    let (mut events, child) = app
        .shell()
        .sidecar("oxo-backend")?
        .args(arguments)
        .spawn()?;
    app.state::<DesktopState>()
        .child
        .lock()
        .map_err(lock_error)?
        .replace(child);

    let handle = app.handle().clone();
    tauri::async_runtime::spawn(async move {
        let mut ready = false;
        while let Some(event) = events.recv().await {
            match event {
                CommandEvent::Stdout(bytes) if !ready => {
                    let output = String::from_utf8_lossy(&bytes);
                    let Some(payload) = output.trim().strip_prefix(READY_PREFIX) else {
                        continue;
                    };
                    let parsed = match serde_json::from_str::<ReadyPayload>(payload) {
                        Ok(value) => value,
                        Err(error) => {
                            record_startup_error(
                                &handle,
                                format!("Invalid sidecar ready message: {error}"),
                            );
                            continue;
                        }
                    };
                    if parsed.host != "127.0.0.1" {
                        record_startup_error(&handle, "Sidecar did not bind to loopback".into());
                        continue;
                    }
                    let base_url = format!("http://127.0.0.1:{}", parsed.port);
                    let health_url = base_url.clone();
                    let health_token = token.clone();
                    let health_challenge = challenge.clone();
                    let health = tokio::task::spawn_blocking(move || {
                        verify_health(parsed.port, &health_token, &health_challenge)
                    })
                    .await;
                    match health {
                        Ok(Ok(())) => {
                            let runtime = DesktopBootstrap {
                                api_base_url: base_url,
                                token: token.clone(),
                            };
                            if let Ok(mut slot) = handle.state::<DesktopState>().bootstrap.lock() {
                                *slot = Some(runtime);
                            }
                            if let Some(window) = handle.get_webview_window("main") {
                                let _ = window.show();
                                let _ = window.set_focus();
                            }
                            ready = true;
                        }
                        Ok(Err(error)) => record_startup_error(
                            &handle,
                            format!("Sidecar health check failed at {health_url}: {error}"),
                        ),
                        Err(error) => record_startup_error(
                            &handle,
                            format!("Sidecar health check task failed: {error}"),
                        ),
                    }
                }
                CommandEvent::Stderr(bytes) => {
                    eprintln!("oxo-backend: {}", String::from_utf8_lossy(&bytes));
                }
                CommandEvent::Error(error) if !ready => {
                    record_startup_error(&handle, format!("Sidecar process error: {error}"));
                }
                CommandEvent::Terminated(status) if !ready => {
                    record_startup_error(
                        &handle,
                        format!("Sidecar exited during startup: {status:?}"),
                    );
                    break;
                }
                _ => {}
            }
        }
    });
    Ok(())
}

#[cfg(debug_assertions)]
fn connect_development_backend(app: &mut tauri::App) -> Result<bool, String> {
    let base_url = std::env::var("OXO_DESKTOP_DEV_API_BASE_URL").map_err(|_| {
        "Desktop development backend is not configured. Run `npm run desktop:dev` from the frontend directory instead of invoking `tauri dev` directly."
            .to_string()
    })?;
    let token = std::env::var("OXO_DESKTOP_DEV_TOKEN")
        .map_err(|_| "Desktop development token is missing".to_string())?;
    let port = std::env::var("OXO_DESKTOP_DEV_PORT")
        .map_err(|_| "Desktop development port is missing".to_string())?
        .parse::<u16>()
        .map_err(|error| format!("Invalid desktop development port: {error}"))?;
    let expected_url = format!("http://127.0.0.1:{port}");
    if base_url != expected_url {
        return Err("Desktop development API must use the loopback address".into());
    }

    let challenge = Uuid::new_v4().simple().to_string();
    verify_health(port, &token, &challenge)
        .map_err(|error| format!("Development backend health check failed: {error}"))?;
    let runtime = DesktopBootstrap {
        api_base_url: base_url,
        token,
    };
    app.state::<DesktopState>()
        .bootstrap
        .lock()
        .map_err(lock_error)?
        .replace(runtime);
    if let Some(window) = app.get_webview_window("main") {
        let _ = window.show();
        let _ = window.set_focus();
    }
    Ok(true)
}

#[cfg(not(debug_assertions))]
fn connect_development_backend(_app: &mut tauri::App) -> Result<bool, String> {
    Ok(false)
}

fn record_startup_error(handle: &tauri::AppHandle, error: String) {
    if let Ok(mut slot) = handle.state::<DesktopState>().startup_error.lock() {
        *slot = Some(error);
    }
    if let Some(window) = handle.get_webview_window("main") {
        let _ = window.show();
        let _ = window.set_focus();
    }
}

fn verify_health(port: u16, token: &str, challenge: &str) -> Result<(), String> {
    let address = SocketAddr::from(([127, 0, 0, 1], port));
    let mut last_error = String::new();
    for _ in 0..160 {
        match TcpStream::connect_timeout(&address, Duration::from_millis(250)) {
            Ok(mut stream) => {
                let _ = stream.set_read_timeout(Some(Duration::from_secs(2)));
                let _ = stream.set_write_timeout(Some(Duration::from_secs(2)));
                let request = format!(
                    "GET /health?challenge={challenge} HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nX-Oxo-Desktop-Token: {token}\r\nConnection: close\r\n\r\n"
                );
                if let Err(error) = stream.write_all(request.as_bytes()) {
                    last_error = error.to_string();
                } else {
                    let mut response = String::new();
                    match stream.read_to_string(&mut response) {
                        Ok(_) if response.starts_with("HTTP/1.1 200") => {
                            let body = response.split("\r\n\r\n").nth(1).unwrap_or_default();
                            let payload: serde_json::Value = serde_json::from_str(body)
                                .map_err(|error| format!("Invalid health response: {error}"))?;
                            if payload.get("status").and_then(|value| value.as_str()) == Some("ok")
                                && payload.get("challenge").and_then(|value| value.as_str())
                                    == Some(challenge)
                            {
                                return Ok(());
                            }
                            last_error = "Health challenge did not match".into();
                        }
                        Ok(_) => last_error = "Health endpoint returned a non-200 response".into(),
                        Err(error) => last_error = error.to_string(),
                    }
                }
            }
            Err(error) => last_error = error.to_string(),
        }
        std::thread::sleep(Duration::from_millis(100));
    }
    Err(last_error)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| {
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.show();
                let _ = window.unminimize();
                let _ = window.set_focus();
            }
        }))
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_process::init())
        .manage(DesktopState::default())
        .invoke_handler(tauri::generate_handler![desktop_bootstrap])
        .setup(start_sidecar)
        .build(tauri::generate_context!())
        .expect("failed to build Oxo Tracker desktop application");

    app.run(|handle, event| {
        if matches!(
            &event,
            RunEvent::WindowEvent {
                label,
                event: WindowEvent::CloseRequested { .. },
                ..
            } if label == "main"
        ) {
            handle.exit(0);
        }
        if matches!(event, RunEvent::Exit | RunEvent::ExitRequested { .. }) {
            if let Ok(mut slot) = handle.state::<DesktopState>().child.lock() {
                if let Some(child) = slot.take() {
                    let _ = child.kill();
                }
            }
        }
    });
}
