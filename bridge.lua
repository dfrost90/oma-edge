-- Loaded BEFORE monitor configuration, so reservations can reuse the exact
-- user monitor rule (including refresh rate, color settings, VRR and scale).
local original = hl.monitor
local rules = {}
local function copy(value)
  if type(value) ~= "table" then return value end
  local result = {}
  for k, v in pairs(value) do result[k] = copy(v) end
  return result
end
hl.monitor = function(spec)
  rules[spec.output or ""] = copy(spec)
  return original(spec)
end
local function rule_for(name)
  if rules[name] then return copy(rules[name]) end
  local monitor = hl.get_monitor(name)
  if not monitor then error("Oma Edge: monitor disconnected: " .. name) end
  for selector, spec in pairs(rules) do
    if selector:sub(1, 5) == "desc:" and
       monitor.description:sub(1, #selector - 5) == selector:sub(6) then
      local result = copy(spec)
      result.output = name
      return result
    end
  end
  if not rules[""] then error("Oma Edge: no captured monitor rule for " .. name) end
  local result = copy(rules[""])
  result.output = name
  return result
end
_G.omarchy_edge_strip = {
  version = 1,
  reserve = function(name, left, right)
    local spec = rule_for(name)
    local base = spec.reserved_area or spec.reserved or 0
    if type(base) == "number" then
      base = { top = base, right = base, bottom = base, left = base }
    end
    spec.reserved = nil
    spec.reserved_area = {
      top = base.top or 0, bottom = base.bottom or 0,
      left = (base.left or 0) + left, right = (base.right or 0) + right,
    }
    original(spec)
  end,
}
-- Bar reservations and output geometry can change without a workspace event.
hl.on("monitor.layout_changed", function()
  hl.dispatch(hl.dsp.event("edge-strip-layout"))
end)
