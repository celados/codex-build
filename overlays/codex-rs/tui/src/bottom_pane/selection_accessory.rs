use crate::app_event_sender::AppEventSender;

pub(crate) type SelectionAction = Box<dyn Fn(&AppEventSender) + Send + Sync>;

pub(crate) struct SelectionAccessoryOption {
    label: String,
    actions: Vec<SelectionAction>,
}

impl SelectionAccessoryOption {
    pub(crate) fn new(label: impl Into<String>, actions: Vec<SelectionAction>) -> Self {
        Self {
            label: label.into(),
            actions,
        }
    }
}

pub(crate) struct SelectionAccessory {
    options: Vec<SelectionAccessoryOption>,
    selected_idx: usize,
}

#[derive(Clone, Copy)]
pub(crate) enum SelectionAccessoryStep {
    Previous,
    Next,
}

impl SelectionAccessory {
    pub(crate) fn new(options: Vec<SelectionAccessoryOption>, selected_idx: usize) -> Option<Self> {
        (!options.is_empty()).then(|| Self {
            selected_idx: selected_idx.min(options.len() - 1),
            options,
        })
    }

    pub(crate) fn cycle(&mut self, step: SelectionAccessoryStep) {
        self.selected_idx = match step {
            SelectionAccessoryStep::Previous => self
                .selected_idx
                .checked_sub(1)
                .unwrap_or(self.options.len() - 1),
            SelectionAccessoryStep::Next => (self.selected_idx + 1) % self.options.len(),
        };
    }

    pub(crate) fn display(&self, focused: bool) -> String {
        if !focused {
            return self.options[self.selected_idx].label.clone();
        }

        self.options
            .iter()
            .enumerate()
            .map(|(idx, option)| {
                if idx == self.selected_idx {
                    option.label.to_uppercase()
                } else {
                    option.label.clone()
                }
            })
            .collect::<Vec<_>>()
            .join(" · ")
    }

    pub(crate) fn selected_actions(&self) -> &[SelectionAction] {
        &self.options[self.selected_idx].actions
    }
}

#[cfg(test)]
#[path = "selection_accessory_tests.rs"]
mod tests;
