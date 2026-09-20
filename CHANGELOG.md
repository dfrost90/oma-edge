# Changelog

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
