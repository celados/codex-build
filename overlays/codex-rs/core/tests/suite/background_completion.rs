#![cfg(not(target_os = "windows"))]

use codex_core::TurnInputRequest;
use codex_login::CodexAuth;
use codex_protocol::config_types::CollaborationMode;
use codex_protocol::config_types::ModeKind;
use codex_protocol::config_types::Settings;
use codex_protocol::models::PermissionProfile;
use codex_protocol::protocol::AskForApproval;
use codex_protocol::protocol::EventMsg;
use codex_protocol::protocol::ThreadSettingsOverrides;
use codex_protocol::user_input::UserInput;
use core_test_support::TempDirExt;
use core_test_support::responses;
use core_test_support::responses::ev_assistant_message;
use core_test_support::responses::ev_completed;
use core_test_support::responses::ev_function_call;
use core_test_support::responses::ev_response_created;
use core_test_support::test_codex::local_selections;
use core_test_support::test_codex::test_codex;
use core_test_support::test_codex::turn_permission_fields;
use core_test_support::wait_for_event;
use pretty_assertions::assert_eq;
use serde_json::Value;
use serde_json::json;

#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn opted_in_background_exec_completion_resumes_idle_thread() -> anyhow::Result<()> {
    let server = responses::start_mock_server().await;
    let test = test_codex()
        .with_model("test-gpt-5-codex")
        .with_auth(CodexAuth::create_dummy_chatgpt_auth_for_testing())
        .build_with_auto_env(&server)
        .await?;
    let gate = test.cwd.abs().join("background-completion-gate");
    let command = format!(
        "while [ ! -f '{}' ]; do sleep 0.05; done; printf COMPLETION_MARKER",
        gate.display()
    );
    let call_id = "background-exec";
    let command_args = json!({
        "cmd": command,
        "login": false,
        "yield_time_ms": 250,
        "on_exit": "resume_turn",
    })
    .to_string();
    let requests = responses::mount_sse_sequence(
        &server,
        vec![
            responses::sse(vec![
                ev_response_created("start"),
                ev_function_call(call_id, "exec_command", &command_args),
                ev_completed("start"),
            ]),
            responses::sse(vec![
                ev_assistant_message("waiting", "waiting for completion"),
                ev_completed("waiting"),
            ]),
            responses::sse(vec![
                ev_assistant_message("resumed", "completion handled"),
                ev_completed("resumed"),
            ]),
        ],
    )
    .await;

    let cwd = test.cwd.abs();
    let (sandbox_policy, permission_profile) =
        turn_permission_fields(PermissionProfile::Disabled, cwd.as_path());
    test.codex
        .start_or_steer_turn(
            TurnInputRequest::user_input(vec![UserInput::Text {
                text: "wait for the background command".to_string(),
                text_elements: Vec::new(),
            }])
            .with_thread_settings(ThreadSettingsOverrides {
                environments: Some(local_selections(cwd)),
                approval_policy: Some(AskForApproval::Never),
                sandbox_policy: Some(sandbox_policy),
                permission_profile,
                collaboration_mode: Some(CollaborationMode {
                    mode: ModeKind::Default,
                    settings: Settings {
                        model: test.session_configured.model.clone(),
                        reasoning_effort: None,
                        developer_instructions: None,
                    },
                }),
                ..Default::default()
            }),
        )
        .await?;
    wait_for_event(test.codex.as_ref(), |event| {
        matches!(event, EventMsg::TurnComplete(_))
    })
    .await;

    std::fs::write(&gate, "done")?;
    wait_for_event(test.codex.as_ref(), |event| {
        matches!(event, EventMsg::TurnComplete(_))
    })
    .await;

    let requests = requests.requests();
    assert_eq!(requests.len(), 3);
    let completions = requests[2]
        .inputs_of_type("function_call_output")
        .into_iter()
        .filter(|item| item["name"] == "background_task_completion")
        .collect::<Vec<_>>();
    assert_eq!(completions.len(), 1);
    assert!(completions[0].get("call_id").is_none());
    let payload: Value = serde_json::from_str(
        completions[0]["output"]
            .as_str()
            .expect("completion output should be text"),
    )?;
    assert_eq!(payload["event_id"], call_id);
    assert_eq!(payload["exit_code"], 0);
    assert_eq!(payload["output"], "COMPLETION_MARKER");

    Ok(())
}
