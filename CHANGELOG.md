# Changelog

## 0.1.12 — Restore theme colors and streamline reconciliation

- Preserve the selected profile and unsaved edits when applying settings fails.
- Extract profile transformations into a shared model and retain slot IDs across
  app reordering, weight changes and workspace edits.
- Split reconciliation into snapshot indexing, constraint tracking, profile and
  geometry planning, window updates, and recovery stages.
- Avoid the second compositor snapshot when nothing changes, and skip identical
  recovery journal writes while retaining records before window mutations.
- Apply monitor reservations together without blocking the event loop. Complete
  save replies after acknowledgement or rollback, while continuing to serve status.
- Qualify shell palette references so QML resolves Omarchy's Color singleton.
  Restore theme colors for custom labels, the header icon, layout preview and window picker.

## 0.1.11 — Avoid unsolicited clipboard reads

- Prevent Oma Edge controls from triggering native Qt clipboard reads on clipboard changes. Weight uses a 1–10 selector; window search accepts bounded keyboard input without paste or input-method composition.
- Add keyboard editing regression tests and an isolated, bounded Wayland clipboard reproducer.

## 0.1.10 — Navigate scrolling columns beside edge apps

- Replace the panel screenshot with a promotional preview built from a separate
  demo workspace containing only fictional content.
- Replace the grid glyph with a theme-aware work-area-and-edge-strip icon in
  both the bar and panel header.
- Fix horizontal focus getting stuck with a floating edge app beside scrolling
  columns. Preserve configured bindings and use column navigation only for tiled
  scrolling windows on monitors with an active strip reservation. Ordinary focus
  resumes automatically when the strip is disabled.

## 0.1.9 — Keep profile data out of process arguments

- Send panel requests through a private stdin pipe instead of command-line JSON,
  preventing saved window titles from appearing in process listings.
- Bound stdin requests to 1 MB and reject malformed JSON without echoing input.
- Cover private request transport and actual process arguments in regression tests.


## 0.1.8 — Fit apps on smaller screens

- Expand strip reservations to fit acknowledged app minimum widths, including
  scaled displays. Keep the saved width as the preferred minimum.
- Recalculate the strip when constrained apps close or assignments change.
- Show “No profiles” and “New profile” instead of the internal -1 index.
- Disable the profile selector when there are no saved profiles.

## 0.1.7 — Recover reservations after startup

- Retry loading reservation data when the runtime file is missing at login.
- Automatically retry failed reservations without requiring a shell restart.
- Reset the window picker after adding an app so the next selection works reliably.

- Preserve live window bindings for unchanged selections when adding, reordering,
  or resizing slots, even when the panel regenerates slot IDs.
- Retain identity-checked bindings across controller and compositor reloads.
- Keep terminal matching strict: a changed selection or reused window identity
  does not inherit the previous terminal binding.

## 0.1.6 — Bar-independent reservations

- Reserve strip space with the plugin's own input-transparent Overlay surfaces.
  The standard Top-layer bar stays full-width without a clone or bar patches.
- Keep the active bar selection during setup; remove legacy adapter blocks from
  saved user clones with backups. OmaChat can keep the standard bar's service access.
- Wait for actual compositor reservations before positioning apps, and recover
  current reservations from live surfaces after service/configuration reloads.
- Stop wrapping monitor rules; the Lua bridge only forwards layout-change events.

## 0.1.5 — Stable full-width bar

- Keep horizontal bars full-width and remove the full-width toggle.
- Separate bar drawing from its height reservation to eliminate the transient
  shrink when workspace strip reservations change. No state watcher or delayed
  margin compensation is needed.
- Upgrade older bar adapters reversibly when rerunning `python3 install.py`.
- Accept older profiles while dropping the obsolete `fullBar` setting.
- Live checks confirm stable bar geometry and surface identity through workspace
  switches, correct left/right reservations, and cleanup when disabled.

## 0.1.4 — Keep terminal window selections distinct

- Identify picker options by window identity instead of changing list positions.
- Prefer the explicitly selected window over stale slot bindings.
- Prevent terminal slots from claiming unrelated terminals when the selected app closes.
  Reopened terminals require a unique exact match to the saved window title.
- Clear stale bindings when saving or reloading profiles.

## 0.1.3 — Preserve selected window titles

- Preserve the selected window title in app slot labels, so terminal apps such
  as Cliamp and Nvim are not relabeled as their terminal class (for example, kitty).
- Existing slots retain their saved labels; remove and re-add them to capture the title.
  Class-based matching on reopen is unchanged.

## 0.1.2 — Preserve gaps around minimum-size apps

- Respect minimum app heights such as Telegram’s instead of overlapping the next tile.
- Recheck asynchronous resize acknowledgements and redistribute the remaining height.
- Verified kitty / Telegram / YouTube at 427 / 504 / 427 px with 14 px gaps.

## 0.1.1 — Dynamic tile heights

- Divide strip height among currently present apps instead of reserving empty slots.
- Reflow on app close/reopen and assignment removal; preserve configured order and height shares.
- Verify three equal tiles become two equal tiles and return to thirds on reopening.

## 0.1.0 — Initial preview

- Reserve a left/right monitor strip for up to six app windows while retaining native tiling.
- Share profiles across selected workspaces or use an all-workspaces fallback.
- Configure width, app order, height shares, and bar coverage in a native Omarchy panel.
- Restore managed windows and reservations when disabled or uninstalled.
- Validate grouped settings and reject conflicting profiles before applying.
- Index window candidates by app class; coalesce compositor events without indefinite debounce.
- Use private atomic state writes and safely decode installed paths containing spaces.
- Preflight installation before mutations; roll back changed configuration on setup failure.

Tested on Omarchy 4.0.4 / Hyprland 0.56.2. Physical multi-monitor hotplug remains unverified.
