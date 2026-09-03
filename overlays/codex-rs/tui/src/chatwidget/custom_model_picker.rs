//! Custom-build-owned model picker that commits a model and its effort as one choice.

use super::*;
use crate::bottom_pane::SelectionDescriptionLayout;
use crate::bottom_pane::selection_accessory::SelectionAccessory;
use crate::bottom_pane::selection_accessory::SelectionAccessoryOption;

pub(super) const CUSTOM_MODEL_SELECTION_VIEW_ID: &str = "custom-model-selection";

impl ChatWidget {
    pub(crate) fn open_custom_model_picker(&mut self) {
        if !self.is_session_configured() {
            self.add_info_message(
                "Model selection is disabled until startup completes.".to_string(),
                /*hint*/ None,
            );
            return;
        }

        // The session catalog is already hydrated before this action is enabled. Keeping the
        // picker cache-only prevents an async refresh from discarding per-row pending effort.
        let presets = match self.model_catalog.try_list_models() {
            Ok(models) => models,
            Err(_) => {
                self.add_info_message(
                    "Models are being updated; please try again in a moment.".to_string(),
                    /*hint*/ None,
                );
                return;
            }
        };
        self.open_custom_model_picker_with_presets(presets);
    }

    pub(super) fn open_custom_model_picker_with_presets(&mut self, presets: Vec<ModelPreset>) {
        let current_model = self.current_model().to_string();
        let current_effort = self.effective_reasoning_effort();
        let items = presets
            .into_iter()
            .filter(|preset| preset.show_in_picker)
            .map(|preset| {
                let is_current = preset.model == current_model;
                let direct_efforts = preset
                    .supported_reasoning_efforts
                    .iter()
                    .filter(|option| {
                        !Self::reasoning_effort_requires_confirmation(&preset, &option.effort)
                    })
                    .collect::<Vec<_>>();
                let preferred_effort = is_current
                    .then_some(current_effort.as_ref())
                    .flatten()
                    .unwrap_or(&preset.default_reasoning_effort);
                let selected_idx = direct_efforts
                    .iter()
                    .position(|option| &option.effort == preferred_effort)
                    .or_else(|| {
                        direct_efforts
                            .iter()
                            .position(|option| option.effort == preset.default_reasoning_effort)
                    })
                    .unwrap_or(0);
                let options = direct_efforts
                    .into_iter()
                    .map(|option| {
                        SelectionAccessoryOption::new(
                            Self::reasoning_effort_sentence_label(&option.effort),
                            self.custom_model_selection_actions(
                                preset.model.clone(),
                                Some(option.effort.clone()),
                            ),
                        )
                    })
                    .collect();
                let accessory = SelectionAccessory::new(options, selected_idx);
                let requires_child_picker = accessory.is_none();
                let actions = if requires_child_picker {
                    let preset = preset.clone();
                    vec![Box::new(move |tx: &AppEventSender| {
                        tx.send(AppEvent::OpenReasoningPopup {
                            model: preset.clone(),
                        });
                    }) as SelectionAction]
                } else {
                    Vec::new()
                };

                SelectionItem {
                    name: preset.model.clone(),
                    accessory,
                    description: requires_child_picker
                        .then(|| "Choose effort in the confirmation picker".to_string()),
                    is_current,
                    is_default: preset.is_default,
                    actions,
                    dismiss_on_select: !requires_child_picker,
                    dismiss_parent_on_child_accept: requires_child_picker,
                    search_value: Some(format!("{} {}", preset.model, preset.display_name)),
                    ..Default::default()
                }
            })
            .collect();

        let mut header = ColumnRenderable::new();
        header.push(Line::from("Model".bold()));
        if self.active_mode_kind() == ModeKind::Plan {
            header.push(Line::from(
                "Plan mode · effort applies to this mode only".dim(),
            ));
        }
        self.show_model_selection_view(SelectionViewParams {
            view_id: Some(CUSTOM_MODEL_SELECTION_VIEW_ID),
            footer_hint: Some(Line::from("enter confirm   ← → effort   esc")),
            items,
            is_searchable: true,
            search_placeholder: Some("Search models".to_string()),
            description_layout: SelectionDescriptionLayout::StackBelowWhenNarrow {
                min_description_width: 24,
            },
            header: Box::new(header),
            ..Default::default()
        });
    }

    fn custom_model_selection_actions(
        &self,
        model: String,
        effort: Option<ReasoningEffortConfig>,
    ) -> Vec<SelectionAction> {
        let warning = effort
            .as_ref()
            .and_then(|effort| self.ultra_reasoning_concurrency_warning(effort));
        let plan_mode = self.active_mode_kind() == ModeKind::Plan;
        vec![Box::new(move |tx| {
            tx.send(AppEvent::UpdateModel(model.clone()));
            if plan_mode {
                tx.send(AppEvent::UpdatePlanModeReasoningEffort(effort.clone()));
                tx.send(AppEvent::PersistPlanModeReasoningEffort(effort.clone()));
            } else {
                tx.send(AppEvent::UpdateReasoningEffort(effort.clone()));
                tx.send(AppEvent::PersistModelSelection {
                    model: model.clone(),
                    effort: effort.clone(),
                });
            }
            if let Some(warning) = warning.clone() {
                tx.send(AppEvent::InsertHistoryCell(Box::new(
                    history_cell::new_warning_event(warning),
                )));
            }
        })]
    }
}
