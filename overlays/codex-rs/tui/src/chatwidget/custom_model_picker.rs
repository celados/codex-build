//! Custom-build-owned model picker that commits a model and its effort as one choice.

use super::*;
use crate::bottom_pane::selection_accessory::SelectionAccessory;
use crate::bottom_pane::selection_accessory::SelectionAccessoryOption;
use crate::render::renderable::ColumnRenderable;

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
        let picker_models = std::env::var("CODEX_PICKER_MODELS")
            .ok()
            .and_then(|spec| parse_picker_models(&spec));
        self.open_custom_model_picker_with_presets(presets, picker_models.as_deref());
    }

    pub(super) fn open_custom_model_picker_with_presets(
        &mut self,
        mut presets: Vec<ModelPreset>,
        picker_models: Option<&[String]>,
    ) {
        // The allowlist is independent of the current session model. Listed models the
        // provider does not offer are skipped; if none remain, the picker would be unusable,
        // so the provider's list, order, and default stay unchanged instead.
        if let Some(picker_models) = picker_models {
            let chosen: Vec<ModelPreset> = picker_models
                .iter()
                .filter_map(|model| {
                    presets
                        .iter()
                        .find(|preset| preset.show_in_picker && &preset.model == model)
                        .cloned()
                })
                .collect();
            if !chosen.is_empty() {
                presets = chosen;
                for (index, preset) in presets.iter_mut().enumerate() {
                    preset.is_default = index == 0;
                }
            }
        }
        let current_model = self.current_model().to_string();
        let current_effort = self.effective_reasoning_effort();
        presets.retain(|preset| preset.show_in_picker);
        let model_ids = presets.iter().map(|preset| preset.model.clone()).collect();
        let items = presets
            .into_iter()
            .map(|preset| {
                let is_current = preset.model == current_model;
                let direct_efforts = &preset.supported_reasoning_efforts;
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
                    .iter()
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
                let actions = accessory.is_none().then(|| {
                    self.custom_model_selection_actions(preset.model.clone(), /*effort*/ None)
                });

                SelectionItem {
                    name: preset.model.clone(),
                    accessory,
                    is_current,
                    is_default: preset.is_default,
                    actions: actions.unwrap_or_default(),
                    dismiss_on_select: true,
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
        self.show_model_selection_view(
            model_ids,
            SelectionViewParams {
                view_id: Some(CUSTOM_MODEL_SELECTION_VIEW_ID),
                footer_hint: Some(Line::from("enter confirm   ← → effort   esc")),
                items,
                is_searchable: true,
                search_placeholder: Some("Search models".to_string()),
                header: Box::new(header),
                ..Default::default()
            },
        );
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

/// Parses `CODEX_PICKER_MODELS`, e.g. `6/{sol,astra,luna};5.6/sol;5.5`, into ordered model
/// slugs (`gpt-6-sol`, …, `gpt-5.6-sol`, `gpt-5.5`). Order is preference order and duplicates
/// keep their first position. Any malformed group rejects the whole spec: a typo silently
/// narrowing the picker would be harder to notice than the provider's full list.
pub(super) fn parse_picker_models(spec: &str) -> Option<Vec<String>> {
    let mut models = Vec::new();
    for group in spec
        .split(';')
        .map(str::trim)
        .filter(|group| !group.is_empty())
    {
        let slugs = match group.split_once('/') {
            None => vec![format!("gpt-{}", valid_part(group)?)],
            Some((version, names)) => {
                let version = valid_part(version)?;
                let names = names.trim();
                let names = match names.strip_prefix('{') {
                    Some(braced) => braced.strip_suffix('}')?,
                    None => names,
                };
                names
                    .split(',')
                    .map(|name| valid_part(name).map(|name| format!("gpt-{version}-{name}")))
                    .collect::<Option<Vec<_>>>()?
            }
        };
        for slug in slugs {
            if !models.contains(&slug) {
                models.push(slug);
            }
        }
    }
    (!models.is_empty()).then_some(models)
}

fn valid_part(part: &str) -> Option<&str> {
    let part = part.trim();
    (!part.is_empty()
        && part
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || c == '.' || c == '-'))
    .then_some(part)
}
