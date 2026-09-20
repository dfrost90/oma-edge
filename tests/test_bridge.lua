local applied = {}
local function copy(t)
  if type(t) ~= "table" then return t end
  local c = {}; for k,v in pairs(t) do c[k] = copy(v) end; return c
end
hl = {
  monitor = function(spec) table.insert(applied, copy(spec)) end,
  get_monitor = function(name) return {description = "LG test panel"} end,
  on = function(event, callback) assert(event == "monitor.layout_changed") end,
}
dofile("bridge.lua")
hl.monitor({output="", mode="preferred", position="auto", scale=1})
hl.monitor({output="DP-1", mode="3440x1440@179.98", position="-3440x20", scale=1.25,
            vrr=2, cm="hdr", bitdepth=10, reserved_area={left=25,top=30}})
omarchy_edge_strip.reserve("DP-1", 0, 688)
local r=applied[#applied]
assert(r.mode=="3440x1440@179.98" and r.position=="-3440x20" and r.scale==1.25)
assert(r.vrr==2 and r.cm=="hdr" and r.bitdepth==10)
assert(r.reserved_area.left==25 and r.reserved_area.top==30 and r.reserved_area.right==688)
omarchy_edge_strip.reserve("DP-1", 100, 0)
r=applied[#applied]
assert(r.reserved_area.left==125 and r.reserved_area.right==0, "reservations must not compound")
omarchy_edge_strip.reserve("DP-1", 0, 0)
r=applied[#applied]
assert(r.reserved_area.left==25 and r.reserved_area.right==0)
hl.monitor({output="DP-1",mode="2560x1440@144",scale=1,reserved_area=10})
omarchy_edge_strip.reserve("DP-1",0,500)
r=applied[#applied]
assert(r.mode=="2560x1440@144" and r.reserved_area.right==510, "external rules supersede cached rules")
hl.monitor({output="desc:LG",mode="preferred",scale=2})
omarchy_edge_strip.reserve("HDMI-A-1",0,200)
r=applied[#applied]
assert(r.output=="HDMI-A-1" and r.scale==2)
print("Monitor bridge: preserves settings, restores reservations, handles rule changes and descriptions")
