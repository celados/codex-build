use std::sync::Arc;
use std::sync::atomic::AtomicBool;

use codex_protocol::models::FunctionCallOutputPayload;
use codex_protocol::models::ResponseItem;
use serde::Serialize;

use super::session::Session;
const MAX_ASYNC_COMPLETION_OUTPUT_BYTES: usize = 32 * 1024;

#[derive(Debug, Serialize)]
#[serde(tag = "status", rename_all = "snake_case")]
enum ShellOutcome {
    Exited { exit_code: Option<i32> },
    Failed { message: String },
}

#[derive(Debug)]
pub(crate) struct AsyncCompletion {
    session_id: i32,
    command: String,
    outcome: ShellOutcome,
    output: String,
    output_truncated: bool,
}

impl AsyncCompletion {
    pub(crate) fn shell(
        session_id: i32,
        command: String,
        exit_code: Option<i32>,
        failure: Option<String>,
        output: String,
        output_truncated: bool,
    ) -> Self {
        let outcome = failure.map_or(ShellOutcome::Exited { exit_code }, |message| {
            ShellOutcome::Failed { message }
        });
        Self {
            session_id,
            command,
            outcome,
            output,
            output_truncated,
        }
    }

    fn into_response_item(self) -> ResponseItem {
        let (output, truncated_for_delivery) = truncate_utf8_head_tail(&self.output);
        let payload = serde_json::json!({
            "source": "shell",
            "session_id": self.session_id,
            "command": self.command,
            "outcome": self.outcome,
            "output": output,
            "output_truncated": self.output_truncated || truncated_for_delivery,
        })
        .to_string();

        ResponseItem::FunctionCallOutput {
            id: None,
            call_id: None,
            name: Some("async_completion".to_string()),
            namespace: Some("codex_build".to_string()),
            output: FunctionCallOutputPayload::from_text(payload),
            internal_chat_message_metadata_passthrough: None,
        }
    }
}

impl Session {
    pub(crate) async fn deliver_async_completion(
        self: &Arc<Self>,
        completion: AsyncCompletion,
        terminal_result_claimed: &AtomicBool,
    ) {
        let delivered = self
            .input_queue
            .enqueue_standalone_output_once(
                completion.into_response_item(),
                terminal_result_claimed,
            )
            .await;
        if !delivered {
            return;
        }
        // Waking a new turn is independent of enqueueing the result. Keeping it on a separate
        // task also prevents the completed command's executor stack from owning the next turn.
        tokio::spawn(self.maybe_start_turn_for_pending_work());
    }
}

fn truncate_utf8_head_tail(output: &str) -> (String, bool) {
    if output.len() <= MAX_ASYNC_COMPLETION_OUTPUT_BYTES {
        return (output.to_string(), false);
    }

    const MARKER: &str = "\n[... async completion output truncated ...]\n";
    let content_budget = MAX_ASYNC_COMPLETION_OUTPUT_BYTES.saturating_sub(MARKER.len());
    let mut head_end = content_budget / 2;
    while !output.is_char_boundary(head_end) {
        head_end -= 1;
    }
    let mut tail_start = output.len().saturating_sub(content_budget - head_end);
    while !output.is_char_boundary(tail_start) {
        tail_start += 1;
    }

    (
        format!("{}{}{}", &output[..head_end], MARKER, &output[tail_start..]),
        true,
    )
}

#[cfg(test)]
#[path = "async_completion_tests.rs"]
mod tests;
