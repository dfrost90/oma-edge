# Release review

## 0.1.12 verification

- Failed-save selection and successful-save reselection have regression coverage.
- Profile serialization preserves slot IDs across reordering and workspace edits.
- A settled no-change pass performs four compositor queries and no file writes.
- Recovery records still precede the first mutation of a managed window.
- Deferred saves, responsive status requests, reservation timeouts, cancellation
  on workspace changes and partial multi-monitor rollback have automated coverage.
- The installed plugin passed desktop smoke checks and panel visual inspection.

## Fixed

- Installer previously adapted the bar before detecting a conflicting installation.
  Compatibility checks now precede changes; setup failures restore touched config files.
- State/config writes used predictable shared temporary names. They now use unique,
  private sibling files and clean them up on failure.
- Grouped profiles could carry conflicting layouts that the UI merged silently.
  Validation now requires identical monitor, layout and slot definitions within a group.
- Non-object profiles and slots now produce explicit validation errors.
- Window matching repeatedly scanned every client and could choose an ineligible
  fullscreen/grouped window ahead of a normal window. Candidates are indexed by
  class and eligibility before selection.
- Repeated compositor events could keep postponing reconciliation. A pending pass
  now keeps its deadline; partial event bytes are cleared on reconnect.
- QML process paths now decode file URLs so installation paths containing spaces work.
- Repeated workspace filtering is centralized and obsolete panel data removed.
- Bar adapter rendering/removal is reusable and tested for exact reversibility.
- Live smoke verification no longer assumes DP-1, a 3440px monitor or a 20% user config.

## Release limits

- A clean first installation in a separate Omarchy session remains a release checklist
  item. Reinstallation on the development desktop and rollback/reversibility tests pass.
- No physical multi-monitor hotplug test was available. Geometry has unit coverage.
- Reservation surfaces are tested with the standard horizontal Omarchy bar.
  Third-party bars that reserve space on the Overlay layer may behave differently.
- Floating slots are reconciled on events, not locked against manual dragging.
- The marketplace must flag manual setup. Publication and submission status are tracked in the GitHub repository and marketplace issue.
