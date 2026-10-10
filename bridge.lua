-- Notify the controller when bar reservations or output geometry change.
-- Side reservations belong to Service.qml's transparent layer surfaces;
-- monitor rules and the selected bar are never rewritten.
hl.on("monitor.layout_changed", function()
  hl.dispatch(hl.dsp.event("edge-strip-layout"))
end)

-- Directional focus can stall when a floating strip app overlaps an off-screen
-- scrolling column. Keep the configured bindings, but let scrolling select its
-- own columns while our reservation is present. Check live surfaces so disabling
-- the service restores ordinary focus without a config reload.
local original_focus = hl.dsp.focus
hl.dsp.focus = function(options)
  local original = original_focus(options)
  local direction = options.direction
  if direction ~= "l" and direction ~= "r" and direction ~= "left" and direction ~= "right" then
    return original
  end
  -- Preserve other focus selectors and their normal validation/precedence.
  for key in pairs(options) do
    if key ~= "direction" then return original end
  end
  local column_focus = hl.dsp.layout("focus " .. ((direction == "l" or direction == "left") and "l" or "r"))
  return function()
    local window = hl.get_active_window()
    local workspace = hl.get_active_special_workspace() or hl.get_active_workspace()
    local monitor = hl.get_active_monitor()
    if window and not window.floating and workspace and workspace.tiled_layout == "scrolling" and monitor then
      for _, layer in ipairs(hl.get_layers()) do
        if layer.mapped and layer.monitor and layer.monitor.name == monitor.name
            and (layer.namespace == "omarchy-edge-reserve-left" or layer.namespace == "omarchy-edge-reserve-right") then
          return hl.dispatch(column_focus)
        end
      end
    end
    return hl.dispatch(original)
  end
end
