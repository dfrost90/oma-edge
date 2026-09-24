local callback
hl = {
  on = function(event, cb) assert(event == "monitor.layout_changed"); callback = cb end,
  dsp = {event = function(name) return name end},
  dispatch = function(event) assert(event == "edge-strip-layout") end,
  monitor = function() error("must not modify monitor rules") end,
}
local original = hl.monitor
dofile("bridge.lua")
assert(hl.monitor == original, "must not wrap monitor configuration")
assert(callback)
callback()
print("Layout bridge: emits layout events without modifying monitor rules")
