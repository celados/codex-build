use pretty_assertions::assert_eq;
use std::sync::atomic::AtomicBool;

use super::*;

#[test]
fn completion_output_is_bounded_on_a_utf8_boundary() {
    let completion = AsyncCompletion {
        session_id: 7,
        command: "wait".to_string(),
        outcome: ShellOutcome::Exited { exit_code: Some(0) },
        output: format!("HEAD{}TAIL", "你".repeat(MAX_ASYNC_COMPLETION_OUTPUT_BYTES)),
        output_truncated: false,
    };

    let ResponseItem::FunctionCallOutput { output, .. } = completion.into_response_item() else {
        panic!("completion should render as a standalone function-call output");
    };
    let value: serde_json::Value = serde_json::from_str(output.text_content().unwrap()).unwrap();

    assert_eq!(value["source"], "shell");
    assert_eq!(value["output_truncated"], true);
    assert!(value["output"].as_str().unwrap().len() <= MAX_ASYNC_COMPLETION_OUTPUT_BYTES);
    assert!(value["output"].as_str().unwrap().starts_with("HEAD"));
    assert!(value["output"].as_str().unwrap().ends_with("TAIL"));
}

#[tokio::test]
async fn terminal_result_is_enqueued_once() {
    let input_queue = crate::session::input_queue::InputQueue::new();
    let terminal_result_claimed = AtomicBool::new(false);
    let completion = || {
        AsyncCompletion::shell(
            7,
            "wait".to_string(),
            Some(0),
            None,
            "done".to_string(),
            false,
        )
        .into_response_item()
    };

    assert!(
        input_queue
            .enqueue_standalone_output_once(completion(), &terminal_result_claimed)
            .await
    );
    assert!(
        !input_queue
            .enqueue_standalone_output_once(completion(), &terminal_result_claimed)
            .await
    );
    assert_eq!(input_queue.drain_mailbox_input_items().await.0.len(), 1);
}
