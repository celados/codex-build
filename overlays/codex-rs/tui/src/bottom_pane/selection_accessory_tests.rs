use super::*;

#[test]
fn cycling_wraps_and_preserves_each_rows_local_state() {
    let mut first = SelectionAccessory::new(
        vec![
            SelectionAccessoryOption::new("low", Vec::new()),
            SelectionAccessoryOption::new("high", Vec::new()),
        ],
        0,
    )
    .unwrap();
    let second = SelectionAccessory::new(
        vec![
            SelectionAccessoryOption::new("medium", Vec::new()),
            SelectionAccessoryOption::new("max", Vec::new()),
        ],
        1,
    )
    .unwrap();

    first.cycle(SelectionAccessoryStep::Previous);

    assert_eq!(first.display(false), "high");
    assert_eq!(first.display(true), "low · HIGH");
    assert_eq!(second.display(false), "max");
}
