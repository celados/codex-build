use std::sync::Arc;

use tokio::sync::Mutex;

use super::UnifiedExecProcessManager;
use super::head_tail_buffer::HeadTailBuffer;
use super::process::UnifiedExecProcess;
use super::process_manager::finish_deferred_network_approval_after_process_exit_for_session;
use crate::session::async_completion::AsyncCompletion;
use crate::session::session::Session;
use crate::tools::network_approval::DeferredNetworkApproval;

pub(super) fn spawn_background_completion(
    session: Arc<Session>,
    process: Arc<UnifiedExecProcess>,
    process_id: i32,
    command: String,
    transcript: Arc<Mutex<HeadTailBuffer>>,
    network_approval: Option<DeferredNetworkApproval>,
) {
    tokio::spawn(async move {
        process.cancellation_token().cancelled().await;
        process.output_drained_notify().cancelled().await;

        // write_stdin uses the same lock before claiming terminal state. Holding it through the
        // mailbox insert makes one consumer win without a remove-before-delivery loss window.
        let _interaction_guard = process.interaction_lock().lock_owned().await;
        if process.terminal_result_claimed() {
            return;
        }

        let network_failure = finish_deferred_network_approval_after_process_exit_for_session(
            Some(&session),
            network_approval,
        )
        .await
        .err();
        let failure = network_failure.or_else(|| process.failure_message());
        let (output, output_truncated) = {
            let transcript = transcript.lock().await;
            (
                String::from_utf8_lossy(&transcript.to_bytes_with_omission_marker()).into_owned(),
                transcript.omitted_bytes() > 0,
            )
        };
        let completion = AsyncCompletion::shell(
            process_id,
            command,
            process.exit_code(),
            failure,
            output,
            output_truncated,
        );
        session
            .deliver_async_completion(completion, process.terminal_result_claim())
            .await;

        remove_process_if_same(&session.services.unified_exec_manager, process_id, &process).await;
    });
}

async fn remove_process_if_same(
    manager: &UnifiedExecProcessManager,
    process_id: i32,
    process: &Arc<UnifiedExecProcess>,
) {
    let mut store = manager.process_store.lock().await;
    if store
        .processes
        .get(&process_id)
        .is_some_and(|entry| Arc::ptr_eq(&entry.process, process))
    {
        store.remove(process_id);
    }
}
