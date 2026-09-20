# Release review

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
- Bar integration depends on compatible Omarchy QML source. Preflight rejects unknown
  source layouts. Local clones do not automatically acquire upstream bar updates.
- Floating slots are reconciled on events, not locked against manual dragging.
- The marketplace must flag manual setup. Publication and submission status are tracked in the GitHub repository and marketplace issue.
