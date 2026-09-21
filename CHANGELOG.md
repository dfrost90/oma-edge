# Changelog

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
