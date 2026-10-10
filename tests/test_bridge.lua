local callback, dispatched
local window = { floating = false }
local workspace = { tiled_layout = "scrolling" }
local special
local monitor = { name = "eDP-1" }
local layers = {}
hl = {
  on = function(event, cb) assert(event == "monitor.layout_changed"); callback = cb end,
  dsp = {
    event = function(name) return {event = name} end,
    focus = function(options) return {focus = options} end,
    layout = function(message) return {layout = message} end,
  },
  dispatch = function(action)
    if type(action) == "function" then return action() end
    dispatched = action
  end,
  get_active_window = function() return window end,
  get_active_workspace = function() return workspace end,
  get_active_special_workspace = function() return special end,
  get_active_monitor = function() return monitor end,
  get_layers = function() return layers end,
  monitor = function() error("must not modify monitor rules") end,
}
local original_monitor = hl.monitor
dofile("bridge.lua")
assert(hl.monitor == original_monitor)
callback()
assert(dispatched.event == "edge-strip-layout")
local right = hl.dsp.focus({direction = "r"})
local function expect_original(action)
  hl.dispatch(action or right)
  assert(dispatched.focus, "ordinary focus expected")
end
local function expect_column(action, direction)
  hl.dispatch(action or right)
  assert(dispatched.layout == "focus " .. (direction or "r"), "column navigation expected")
end
expect_original()
layers = {{namespace = "omarchy-edge-reserve-right", mapped = true, monitor = monitor}}
expect_column()
expect_column(hl.dsp.focus({direction = "left"}), "l")
expect_column(hl.dsp.focus({direction = "right"}))
expect_column(hl.dsp.focus({direction = "l"}), "l")
-- The callback uses live state, including after disabling/re-enabling the strip.
layers[1].mapped = false
expect_original()
layers[1].mapped = true
expect_column()
layers[1].monitor = {name = "DP-2"}
expect_original()
layers[1].monitor = monitor
layers[1].namespace = "another-panel"
expect_original()
layers[1].namespace = "omarchy-edge-reserve-left"
expect_column()
window.floating = true
expect_original()
window.floating = false
workspace.tiled_layout = "dwindle"
expect_original()
workspace.tiled_layout = "scrolling"
special = {tiled_layout = "master"}
expect_original()
special = nil
window = nil
expect_original()
window = {floating = false}
monitor = nil
expect_original()
monitor = {name = "eDP-1"}
for _, options in ipairs({{direction="u"}, {direction="d"}, {window="class:foot"}, {workspace="2"}, {monitor="r"}, {direction="r", window="class:foot"}}) do
  local action = hl.dsp.focus(options)
  assert(type(action) == "table", "unrelated dispatchers must retain their type")
  expect_original(action)
end
print("Layout bridge: scoped column focus, live disable/re-enable, and ordinary focus fallbacks passed")
