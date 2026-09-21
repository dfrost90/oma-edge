import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import qs.Ui as Ui
import qs.Commons

Ui.Panel {
    id: root
    moduleName: "io.github.dfrost90.edge-strip"
    ipcTarget: "edge-strip"
    implicitWidth: button.implicitWidth
    implicitHeight: button.implicitHeight
    property var snapshot: ({})
    property var config: ({version: 1, enabled: true, profiles: []})
    property var draft: null
    property int profileIndex: -1
    property bool dirty: false
    property string message: ""
    property string requestResult: ""
    readonly property string backend: decodeURIComponent(Qt.resolvedUrl("backend.py").toString().replace("file://", ""))
    readonly property var monitors: snapshot.monitors || []
    readonly property var windows: (snapshot.clients || []).filter(function(c) {
        return c.mapped && !c.fullscreen && !(c.grouped || []).length
    })
    readonly property var profiles: groupedProfiles()
    function groupedProfiles() {
        var result = []
        ;(config.profiles || []).forEach(function(p, i) {
            var existing = p.group ? result.find(function(r) { return r.group === p.group && r.monitor === p.monitor }) : null
            if (existing) { existing.workspaces.push(p.workspace); existing.sourceIndices.push(i) }
            else {
                var item = clone(p)
                item.workspaces = [p.workspace]
                item.sourceIndices = [i]
                result.push(item)
            }
        })
        return result
    }
    readonly property var workspaceOptions: {
        // Match Omarchy’s Workspaces widget: five base slots plus live slots through 10.
        var values = ["1", "2", "3", "4", "5"]
        ;(snapshot.workspaces || []).forEach(function(w) {
            if (w.id > 0 && w.id <= 10) values.push(String(w.id))
        })
        values = values.filter(function(v, i, arr) { return v !== "*" && arr.indexOf(v) === i })
        values.sort(function(a,b) { return /^\d+$/.test(a) && /^\d+$/.test(b) ? Number(a) - Number(b) : a.localeCompare(b) })
        return [{value:"*", label:"All workspaces"}].concat(values.map(function(v) {
            return {value:v, label:v.startsWith("name:") ? v.slice(5) : "Workspace " + v}
        }))
    }
    readonly property var specificWorkspaces: workspaceOptions.filter(function(o) { return o.value !== "*" })
    function visibleWorkspaceValues() { return specificWorkspaces.map(function(o) { return o.value }) }
    function chooseWorkspaces(values) {
        var next = Array.from(values)
        if (next.indexOf("*") >= 0) {
            next = draft.workspaces.indexOf("*") < 0 ? ["*"] : next.filter(function(v) { return v !== "*" })
        }
        edit("workspaces", next)
    }
    readonly property var profileLabels: profiles.map(function(p) {
        return p.monitor + " · " + (p.workspaces.indexOf("*") >= 0 ? "All workspaces" : "Workspaces " + p.workspaces.map(function(w) { return w.replace("name:", "") }).join(", "))
    })
    function clone(v) { return JSON.parse(JSON.stringify(v)) }
    function selectProfile(i) {
        profileIndex = i
        draft = i >= 0 && i < profiles.length ? clone(profiles[i]) : null
        dirty = false
        message = ""
    }
    function edit(key, value) {
        if (!draft) return
        var next = clone(draft)
        next[key] = value
        draft = next
        dirty = true
    }
    function currentWorkspace(m) {
        if (!m || !m.activeWorkspace) return "1"
        return m.activeWorkspace.id > 0 ? String(m.activeWorkspace.id) : "name:" + m.activeWorkspace.name
    }
    function newProfile() {
        var m = monitors.filter(function(m) { return m.focused })[0] || monitors[0]
        if (!m) { message = "No connected monitor"; return }
        var ws = currentWorkspace(m)
        var existing = profiles.findIndex(function(p) { return p.monitor === m.name && p.workspaces.indexOf(ws) >= 0 })
        if (existing >= 0) { selectProfile(existing); return }
        profileIndex = -1
        draft = {monitor: m.name, workspace: ws, workspaces: [ws], sourceIndices: [], enabled: true, side: "right", width: 20, fullBar: true, slots: []}
        dirty = true
    }
    function windowKey(c) {
        return JSON.stringify([String(c.stableId || ""), c.address, c.pid])
    }
    function addWindow(key) {
        if (!draft) return
        var c = windows.find(function(w) { return root.windowKey(w) === key })
        if (!c) { message = "That window has closed. Select an open window."; return }
        var slots = clone(draft.slots)
        if (slots.length >= 6) { message = "Maximum six app slots"; return }
        slots.push({id: "slot_" + Date.now() + "_" + slots.length, class: c.class,
                    label: c.title || c.class, preferred: String(c.stableId || ""),
                    windowTitle: c.title || "", weight: 1})
        edit("slots", slots)
    }
    function slotAction(i, action) {
        var slots = clone(draft.slots)
        if (action === "remove") slots.splice(i, 1)
        else {
            var other = i + (action === "up" ? -1 : 1)
            if (other < 0 || other >= slots.length) return
            var temp = slots[i]; slots[i] = slots[other]; slots[other] = temp
        }
        edit("slots", slots)
    }
    function setWeight(i, weight) {
        var slots = clone(draft.slots)
        slots[i].weight = weight
        edit("slots", slots)
    }
    function send(data) {
        if (rpc.running) return
        requestResult = ""
        rpc.command = ["python3", backend, "request", JSON.stringify(data)]
        rpc.running = true
    }
    function save(remove) {
        if (!draft) return
        var next = clone(config)
        if (!remove && !draft.workspaces.length) { message = "Select at least one workspace."; return }
        var indices = draft.sourceIndices || []
        next.profiles = next.profiles.filter(function(p, i) { return indices.indexOf(i) < 0 })
        if (!remove) {
            var conflict = next.profiles.find(function(p) {
                return p.monitor === root.draft.monitor && root.draft.workspaces.indexOf(p.workspace) >= 0
            })
            if (conflict) { message = "Workspace " + conflict.workspace + " already has a profile. Edit that profile or uncheck this workspace."; return }
            var group = draft.group || "group_" + Date.now()
            draft.workspaces.forEach(function(ws, i) {
                var p = root.clone(root.draft)
                p.workspace = ws
                p.group = group
                delete p.workspaces
                delete p.sourceIndices
                p.slots.forEach(function(slot, j) { slot.id = group + "_" + i + "_" + j })
                next.profiles.push(p)
            })
        }
        profileIndex = remove ? 0 : Math.max(0, profiles.length - (indices.length ? 1 : 0))
        send({action: "save", config: next})
    }
    function readState() {
        try {
            snapshot = JSON.parse(state.text())
            if (!dirty && !rpc.running) {
                config = clone(snapshot.config)
                if (profileIndex < 0 || profileIndex >= profiles.length) profileIndex = profiles.length ? 0 : -1
                draft = profileIndex >= 0 ? clone(profiles[profileIndex]) : null
            }
        } catch(e) { message = "Waiting for Oma Edge service…" }
    }
    FileView {
        id: state
        path: Quickshell.env("XDG_RUNTIME_DIR") + "/omarchy-edge-strip/state.json"
        watchChanges: true
        onFileChanged: reload()
        onLoaded: root.readState()
    }
    Process {
        id: rpc
        stdout: StdioCollector { onStreamFinished: root.requestResult = text }
        onExited: {
            try {
                var result = JSON.parse(root.requestResult)
                if (result.ok) {
                    root.dirty = false
                    root.message = "Saved"
                    state.reload()
                } else root.message = result.error || "Could not apply configuration"
            } catch(e) { root.message = "Service unavailable. Check installation or restart the shell." }
        }
    }
    onOpenedChanged: if (opened) state.reload()
    Ui.BarIconButton {
        id: button
        anchors.fill: parent
        bar: root.bar
        text: "󰕰"
        tooltipText: "Oma Edge"
        active: root.opened
        onPressed: root.toggle()
    }
    component Caption: Text {
        color: Color.foreground
        font.family: Style.font.family
        font.pixelSize: Style.font.body
        wrapMode: Text.Wrap
        textFormat: Text.PlainText
    }
    component Action: Ui.Button {
        focusable: true
        bordered: true
        opacity: enabled ? 1 : 0.4
    }
    component IconAction: Ui.PanelActionButton {
        focusable: true
        opacity: enabled ? 1 : 0.4
    }
    Ui.KeyboardPanel {
        id: panel
        anchorItem: button
        owner: root
        bar: root.bar
        open: root.opened
        contentWidth: panel.fittedContentWidth(Style.space(460))
        contentHeight: panel.fittedContentHeight(body.implicitHeight + footer.implicitHeight + Style.space(16), Style.space(880))
        focusTarget: form
        ColumnLayout {
            id: form
            anchors.fill: parent
            spacing: Style.space(10)
            focus: true
            Keys.onEscapePressed: root.close()
            ScrollView {
                id: scrollArea
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                // Keep keyboard-focused form controls inside the scroll viewport.
                Connections {
                    target: form.Window.window
                    function onActiveFocusItemChanged() {
                        var item = form.Window.window.activeFocusItem
                        if (!item) return
                        var ancestor = item
                        while (ancestor && ancestor !== body) ancestor = ancestor.parent
                        if (!ancestor) return
                        var y = item.mapToItem(body, 0, 0).y
                        var flick = scrollArea.contentItem
                        var margin = Style.space(8)
                        if (y < flick.contentY + margin) flick.contentY = Math.max(0, y - margin)
                        else if (y + item.height > flick.contentY + scrollArea.availableHeight - margin)
                            flick.contentY = Math.min(Math.max(0, body.height - scrollArea.availableHeight), y + item.height - scrollArea.availableHeight + margin)
                    }
                }
                ColumnLayout {
                    id: body
                    width: scrollArea.availableWidth
                    spacing: Style.space(10)
                    Ui.PanelHero {
                        Layout.fillWidth: true
                        title: "Oma Edge"
                        meta: root.config.enabled ? "Apps beside your layout" : "Paused"
                        detail: root.dirty ? "Unsaved" : ""
                        iconComponent: Component {
                            Text { text: "󰕰"; color: Color.foreground; font.family: Style.font.family; font.pixelSize: Style.font.display }
                        }
                        trailingControl: Component {
                            Ui.ToggleSwitch {
                                checked: root.config.enabled
                                enabled: !rpc.running && !root.dirty
                                opacity: enabled ? 1 : 0.5
                                activeFocusOnTab: true
                                hasCursor: activeFocus
                                Accessible.name: "Enable Oma Edge"
                                Keys.onSpacePressed: toggled()
                                Keys.onReturnPressed: toggled()
                                onToggled: {
                                    var next = root.clone(root.config); next.enabled = !checked
                                    root.send({action: "save", config: next})
                                }
                            }
                        }
                    }
                    Ui.PanelSeparator { Layout.fillWidth: true }
                    Ui.PanelSectionHeader { text: "PROFILE" }
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Style.spacing.controlGap
                        Ui.Dropdown {
                            Layout.fillWidth: true
                            showLabel: false
                            value: String(root.profileIndex)
                            options: root.profileLabels.map(function(label, i) { return {value: String(i), label: label} })
                            enabled: !root.dirty && !rpc.running
                            onChanged: function(value) { root.selectProfile(Number(value)) }
                        }
                        Action { text: "New"; iconText: "+"; tooltipText: "Profile for the current workspace"; enabled: !root.dirty && !rpc.running; onClicked: root.newProfile() }
                    }
                    ColumnLayout {
                        visible: root.draft !== null
                        Layout.fillWidth: true
                        spacing: Style.space(10)
                        ColumnLayout {
                            visible: root.monitors.length > 1
                            Layout.fillWidth: true
                            spacing: Style.spacing.controlGap
                            Caption { text: "Monitor"; font.pixelSize: Style.font.bodySmall; opacity: 0.65 }
                            Flow {
                                Layout.fillWidth: true
                                spacing: Style.space(5)
                                Repeater {
                                    model: root.monitors
                                    delegate: Action {
                                        required property var modelData
                                        text: modelData.name
                                        tooltipText: modelData.description || modelData.name
                                        horizontalPadding: Style.space(9)
                                        selected: root.draft !== null && root.draft.monitor === modelData.name
                                        onClicked: if (!selected) root.edit("monitor", modelData.name)
                                    }
                                }
                            }
                        }
                        ColumnLayout {
                            visible: root.specificWorkspaces.length > 1
                            Layout.fillWidth: true
                            spacing: Style.spacing.controlGap
                            Caption { text: "Workspaces"; font.pixelSize: Style.font.bodySmall; opacity: 0.65 }
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: Style.space(10)
                                Flow {
                                    Layout.fillWidth: true
                                    spacing: Style.space(5)
                                    Repeater {
                                        model: root.specificWorkspaces
                                        delegate: Action {
                                        id: workspaceChoice
                                            required property var modelData
                                            text: modelData.value === "*" ? "All" : modelData.value.replace("name:", "")
                                            tooltipText: modelData.label
                                            horizontalPadding: Style.space(9)
                                            implicitWidth: Math.max(Style.space(31), implicitContentWidth)
                                            readonly property real implicitContentWidth: labelMetrics.width + horizontalPadding * 2 + Style.space(4)
                                            TextMetrics { id: labelMetrics; font.family: Style.font.family; font.pixelSize: Style.font.body; text: workspaceChoice.text }
                                            selected: root.draft !== null && (root.draft.workspaces.indexOf("*") >= 0 || root.draft.workspaces.indexOf(modelData.value) >= 0)
                                            onClicked: {
                                                var values = root.draft.workspaces.indexOf("*") >= 0 ? root.visibleWorkspaceValues() : root.draft.workspaces.slice()
                                                var i = values.indexOf(modelData.value)
                                                if (i >= 0) values.splice(i, 1)
                                                else values.push(modelData.value)
                                                root.chooseWorkspaces(values)
                                            }
                                        }
                                    }
                                }
                                RowLayout {
                                    spacing: Style.space(4)
                                    Caption { text: "All"; font.pixelSize: Style.font.bodySmall }
                                    Ui.ToggleSwitch {
                                        checked: root.draft !== null && root.draft.workspaces.indexOf("*") >= 0
                                        activeFocusOnTab: true
                                        hasCursor: activeFocus
                                        Accessible.name: "All workspaces"
                                        Keys.onSpacePressed: toggled()
                                        Keys.onReturnPressed: toggled()
                                        onToggled: root.edit("workspaces", checked
                                            ? root.visibleWorkspaceValues()
                                            : ["*"])
                                    }
                                }
                            }
                        }
                        Ui.Toggle {
                            Layout.fillWidth: true
                            label: "Use strip in this profile"
                            description: "Overrides the all-workspaces profile, even when off."
                            checked: root.draft ? root.draft.enabled : false
                            onClicked: root.edit("enabled", !checked)
                        }
                        Ui.PanelSeparator { Layout.fillWidth: true }
                        Ui.PanelSectionHeader { text: "LAYOUT" }
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Style.space(10)
                            Ui.Dropdown {
                                Layout.preferredWidth: Style.space(120)
                                label: "Edge"
                                value: root.draft ? root.draft.side : "right"
                                options: [{value:"left", label:"Left"}, {value:"right", label:"Right"}]
                                onChanged: function(value) { root.edit("side", value) }
                            }
                            ColumnLayout {
                                Layout.fillWidth: true
                                Caption { text: "Strip width · " + (root.draft ? root.draft.width : 20) + "%"; font.pixelSize: Style.font.bodySmall }
                                Ui.CursorSurface {
                                    Layout.fillWidth: true
                                    implicitHeight: widthSlider.implicitHeight + Style.space(12)
                                    activeFocusOnTab: true
                                    hasCursor: activeFocus
                                    Keys.onLeftPressed: root.edit("width", Math.max(10, root.draft.width - 1))
                                    Keys.onRightPressed: root.edit("width", Math.min(45, root.draft.width + 1))
                                    Ui.PanelSlider {
                                        id: widthSlider
                                        anchors.fill: parent
                                        anchors.margins: Style.space(6)
                                        bar: root.bar
                                        minimum: 10; maximum: 45; step: 1; integer: true
                                        value: root.draft ? root.draft.width : 20
                                        onMoved: function(value) { root.edit("width", Math.round(value)) }
                                    }
                                }
                            }
                        }
                        Ui.BorderSurface {
                            id: preview
                            Layout.fillWidth: true
                            Layout.preferredHeight: Style.space(100)
                            color: "transparent"
                            borderSpec: Border.controlSpec("normal", Color.foreground, Color.accent)
                            radius: Style.cornerRadius
                            readonly property real stripWidth: (width - Style.space(12)) * (root.draft ? root.draft.width / 100 : 0.2)
                            readonly property bool onLeft: root.draft && root.draft.side === "left"
                            Rectangle {
                                x: Style.space(6) + (preview.onLeft && root.draft && !root.draft.fullBar ? preview.stripWidth : 0)
                                y: Style.space(6)
                                width: preview.width - Style.space(12) - (root.draft && !root.draft.fullBar ? preview.stripWidth : 0)
                                height: Style.space(5)
                                color: Color.foreground; opacity: 0.5
                            }
                            Caption {
                                x: Style.space(6) + (preview.onLeft ? preview.stripWidth : 0)
                                y: Style.space(18)
                                width: preview.width - preview.stripWidth - Style.space(12)
                                height: preview.height - Style.space(24)
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                                text: "Layout · " + (100 - (root.draft ? root.draft.width : 20)) + "%"
                                font.pixelSize: Style.font.caption
                                opacity: 0.65
                            }
                            Column {
                                x: preview.onLeft ? Style.space(6) : preview.width - preview.stripWidth - Style.space(6)
                                y: Style.space(18)
                                width: preview.stripWidth
                                spacing: Style.space(3)
                                readonly property var slots: root.draft && root.draft.slots.length ? root.draft.slots : [{label:"Apps", weight:1}]
                                readonly property real total: slots.reduce(function(sum, s) { return sum + s.weight }, 0)
                                Repeater {
                                    model: parent.slots
                                    Rectangle {
                                        required property var modelData
                                        width: parent.width
                                        height: (preview.height - Style.space(24) - (parent.slots.length - 1) * parent.spacing) * modelData.weight / parent.total
                                        color: Style.selectedFillFor(Color.foreground, Color.accent)
                                        radius: Style.cornerRadius
                                        Caption { anchors.fill: parent; anchors.margins: Style.space(3); text: modelData.label; font.pixelSize: Style.font.caption; elide: Text.ElideRight; wrapMode: Text.NoWrap; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                                    }
                                }
                            }
                        }
                        Ui.Toggle {
                            Layout.fillWidth: true
                            label: "Full-width top bar"
                            description: checked ? "Span the layout and reserved strip." : "Stay above the layout area only."
                            checked: root.draft ? root.draft.fullBar : false
                            onClicked: root.edit("fullBar", !checked)
                        }
                        Ui.PanelSeparator { Layout.fillWidth: true }
                        RowLayout {
                            Layout.fillWidth: true
                            Ui.PanelSectionHeader { text: "APPS · TOP TO BOTTOM"; Layout.fillWidth: true }
                            Caption { text: "Height share"; font.pixelSize: Style.font.caption; opacity: 0.6 }
                        }
                        Repeater {
                            model: root.draft ? root.draft.slots : []
                            delegate: RowLayout {
                                required property var modelData
                                required property int index
                                Layout.fillWidth: true
                                spacing: Style.spacing.controlGap
                                Caption { text: modelData.label; Layout.fillWidth: true; elide: Text.ElideRight; wrapMode: Text.NoWrap }
                                Ui.NumberField {
                                    from: 1; to: 10; value: modelData.weight
                                    fieldWidth: Style.space(70)
                                    onModified: function(value) { root.setWeight(index, value) }
                                }
                                IconAction { iconText: "↑"; tooltipText: "Move up"; enabled: index > 0; onClicked: root.slotAction(index, "up") }
                                IconAction { iconText: "↓"; tooltipText: "Move down"; enabled: index < root.draft.slots.length - 1; onClicked: root.slotAction(index, "down") }
                                IconAction { iconText: "×"; tooltipText: "Remove app"; onClicked: root.slotAction(index, "remove") }
                            }
                        }
                        Ui.SearchableDropdown {
                            Layout.fillWidth: true
                            showLabel: false
                            triggerLabel: "+ Add an open window"
                            placeholderText: "Search apps and window titles…"
                            emptyText: "No matching open windows"
                            options: root.windows.map(function(c) { return {value:root.windowKey(c), label:c.title || c.class, description:c.class} })
                            enabled: root.draft !== null && root.draft.slots.length < 6
                            onChanged: function(value) { root.addWindow(value) }
                        }
                        Caption {
                            Layout.fillWidth: true
                            text: "Apps move here when applied. Height shares set their relative sizes."
                            font.pixelSize: Style.font.caption
                            opacity: 0.6
                        }
                    }
                    Caption { Layout.fillWidth: true; visible: !root.draft; text: "Create a profile for this workspace to assign your first app."; opacity: 0.7 }
                }
            }
            ColumnLayout {
                id: footer
                Layout.fillWidth: true
                spacing: Style.space(10)
                Ui.PanelSeparator { Layout.fillWidth: true }
                Caption { Layout.fillWidth: true; text: root.message || root.snapshot.error || ""; visible: text !== ""; font.pixelSize: Style.font.caption }
                RowLayout {
                    Layout.fillWidth: true
                    visible: root.draft !== null
                    IconAction { iconText: "󰆴"; tooltipText: "Remove profile"; enabled: !rpc.running; onClicked: root.save(true) }
                    Caption { text: root.dirty ? "Unsaved changes" : "Up to date"; opacity: 0.6; font.pixelSize: Style.font.caption; Layout.fillWidth: true }
                    Action { text: "Discard"; enabled: root.dirty && !rpc.running; onClicked: root.selectProfile(root.profileIndex) }
                    Action { text: rpc.running ? "Applying…" : "Apply"; selected: root.dirty; enabled: root.dirty && !rpc.running && root.draft !== null && root.draft.workspaces.length > 0; onClicked: root.save(false) }
                }
            }
        }
    }
}
