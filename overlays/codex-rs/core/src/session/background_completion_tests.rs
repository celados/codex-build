use super::*;
use codex_protocol::models::ResponseItem;

#[test]
fn completion_output_is_bounded_on_a_utf8_boundary() {
    let completion = BackgroundCompletion {
        event_id: "event".to_string(),
        process_id: 7,
        command: "wait".to_string(),
        cwd: "/tmp".to_string(),
        exit_code: 0,
        timed_out: false,
        duration: Duration::from_millis(25),
        output: "你".repeat(MAX_BACKGROUND_COMPLETION_OUTPUT_BYTES),
    };

    let TurnInput::FunctionCallOutput(ResponseItem::FunctionCallOutput { output, .. }) =
        completion.into_turn_input()
    else {
        panic!("completion should render as a standalone function-call output");
    };
    let value: serde_json::Value = serde_json::from_str(output.text_content().unwrap()).unwrap();

    assert_eq!(value["output_truncated"], true);
    assert!(value["output"].as_str().unwrap().len() <= MAX_BACKGROUND_COMPLETION_OUTPUT_BYTES);
}
