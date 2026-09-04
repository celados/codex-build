use std::sync::Arc;
use std::time::Duration;

use codex_protocol::models::FunctionCallOutputPayload;
use codex_protocol::models::ResponseItem;

use super::TurnInput;
use super::session::Session;

const MAX_BACKGROUND_COMPLETION_OUTPUT_BYTES: usize = 32 * 1024;

#[derive(Debug)]
pub(crate) struct BackgroundCompletion {
    pub(crate) event_id: String,
    pub(crate) process_id: i32,
    pub(crate) command: String,
    pub(crate) cwd: String,
    pub(crate) exit_code: i32,
    pub(crate) timed_out: bool,
    pub(crate) duration: Duration,
    pub(crate) output: String,
}

impl BackgroundCompletion {
    fn into_turn_input(self) -> TurnInput {
        let (output, output_truncated) = truncate_utf8(&self.output);
        let output = serde_json::json!({
            "event_id": self.event_id,
            "process_id": self.process_id,
            "command": self.command,
            "cwd": self.cwd,
            "exit_code": self.exit_code,
            "timed_out": self.timed_out,
            "duration_ms": self.duration.as_millis(),
            "output": output,
            "output_truncated": output_truncated,
        })
        .to_string();

        TurnInput::FunctionCallOutput(ResponseItem::FunctionCallOutput {
            id: None,
            call_id: None,
            name: Some("background_task_completion".to_string()),
            namespace: None,
            output: FunctionCallOutputPayload::from_text(output),
            internal_chat_message_metadata_passthrough: None,
        })
    }
}

impl Session {
    pub(crate) async fn deliver_background_completion(
        self: &Arc<Self>,
        completion: BackgroundCompletion,
    ) {
        self.input_queue
            .enqueue_background_completion(completion.into_turn_input())
            .await;
        self.maybe_start_turn_for_pending_work().await;
    }
}

fn truncate_utf8(output: &str) -> (&str, bool) {
    if output.len() <= MAX_BACKGROUND_COMPLETION_OUTPUT_BYTES {
        return (output, false);
    }

    let mut end = MAX_BACKGROUND_COMPLETION_OUTPUT_BYTES;
    while !output.is_char_boundary(end) {
        end -= 1;
    }
    (&output[..end], true)
}

#[cfg(test)]
#[path = "background_completion_tests.rs"]
mod tests;
