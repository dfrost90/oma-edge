-- Notify the controller when bar reservations or output geometry change.
-- Side reservations belong to Service.qml's transparent layer surfaces;
-- monitor rules and the selected bar are never rewritten.
hl.on("monitor.layout_changed", function()
  hl.dispatch(hl.dsp.event("edge-strip-layout"))
end)
