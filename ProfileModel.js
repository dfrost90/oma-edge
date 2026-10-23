// Pure profile transformations, shared by the QML panel and Node tests.
function clone(value) { return JSON.parse(JSON.stringify(value)) }

var sequence = 0
function newId(prefix) { return prefix + "_" + Date.now() + "_" + (++sequence) }

function profileKey(profile) {
    return profile ? JSON.stringify([profile.monitor, profile.group ? "group" : "workspace", profile.group || profile.workspace]) : ""
}

function groupedProfiles(config) {
    var result = []
    ;(config.profiles || []).forEach(function(profile, index) {
        var item = profile.group ? result.find(function(p) {
            return p.group === profile.group && p.monitor === profile.monitor
        }) : null
        if (!item) {
            item = clone(profile)
            item.workspaces = []
            item.sourceIndices = []
            item.slots.forEach(function(slot) { slot.sourceIds = {} })
            result.push(item)
        }
        item.workspaces.push(profile.workspace)
        item.sourceIndices.push(index)
        item.slots.forEach(function(slot, i) {
            slot.sourceIds[profile.workspace] = profile.slots[i].id
        })
    })
    return result
}

function saveProfile(config, draft, remove) {
    if (!remove && !draft.workspaces.length) throw new Error("Select at least one workspace.")
    var next = clone(config)
    var indices = draft.sourceIndices || []
    next.profiles = next.profiles.filter(function(p, i) { return indices.indexOf(i) < 0 })
    if (remove) return {config: next, selection: ""}
    var conflict = next.profiles.find(function(p) {
        return p.monitor === draft.monitor && draft.workspaces.indexOf(p.workspace) >= 0
    })
    if (conflict) throw new Error("Workspace " + conflict.workspace + " already has a profile. Edit that profile or uncheck this workspace.")
    var group = draft.group || newId("group")
    var usedIds = new Set()
    next.profiles.forEach(function(p) { p.slots.forEach(function(s) { usedIds.add(s.id) }) })
    draft.workspaces.forEach(function(workspace) {
        var profile = clone(draft)
        profile.workspace = workspace
        profile.group = group
        delete profile.workspaces
        delete profile.sourceIndices
        profile.slots.forEach(function(slot) {
            var id = slot.sourceIds ? slot.sourceIds[workspace] : slot.id
            if (!id || usedIds.has(id)) {
                do { id = newId("slot") } while (usedIds.has(id))
            }
            slot.id = id
            usedIds.add(id)
            delete slot.sourceIds
        })
        next.profiles.push(profile)
    })
    return {config: next, selection: profileKey({monitor: draft.monitor, group: group})}
}

if (typeof module !== "undefined") module.exports = {clone, newId, profileKey, groupedProfiles, saveProfile}
