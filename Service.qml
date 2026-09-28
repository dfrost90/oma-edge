import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Wayland

Item {
    id: root
    readonly property string backend: decodeURIComponent(Qt.resolvedUrl("backend.py").toString().replace("file://", ""))
    property var reservations: ({})
    property bool reservationLoadPending: true
    FileView {
        id: reservationFile
        path: Quickshell.env("XDG_RUNTIME_DIR") + "/omarchy-edge-strip/reservations.json"
        watchChanges: true
        onFileChanged: reload()
        onLoaded: {
            root.reservationLoadPending = false
            try {
                var data = JSON.parse(text())
                root.reservations = data.session === Quickshell.env("HYPRLAND_INSTANCE_SIGNATURE")
                    ? data.monitors || ({}) : ({})
            } catch (e) { root.reservations = ({}) }
        }
        onLoadFailed: {
            root.reservations = ({})
            root.reservationLoadPending = true
        }
    }
    // On login even the runtime directory may not exist yet, so the file
    // watcher cannot reliably observe the backend's first atomic write.
    Timer {
        interval: 250
        repeat: true
        running: root.reservationLoadPending
        onTriggered: reservationFile.reload()
    }
    Variants {
        model: Quickshell.screens
        delegate: Scope {
            required property var modelData
            id: output
            readonly property var widths: root.reservations[modelData.name] || [0, 0]
            Reservation { screen: output.modelData; side: "left"; extent: output.widths[0] || 0 }
            Reservation { screen: output.modelData; side: "right"; extent: output.widths[1] || 0 }
        }
    }
    component Reservation: PanelWindow {
        required property string side
        required property int extent
        visible: worker.running && extent > 0
        anchors.top: true
        anchors.bottom: true
        anchors.left: side === "left"
        anchors.right: side === "right"
        implicitWidth: Math.max(1, extent)
        color: "transparent"
        mask: Region {}
        exclusionMode: ExclusionMode.Auto
        // Hyprland arranges Top before Overlay: the bar keeps its full width,
        // then this invisible surface reserves space for ordinary app windows.
        WlrLayershell.layer: WlrLayer.Overlay
        WlrLayershell.namespace: "omarchy-edge-reserve-" + side
    }
    // Quickshell may kill owned processes during component destruction before
    // Python's SIGTERM cleanup runs. Recover from the journal in a separate
    // short-lived process, but only if this plugin is actually disabled.
    Component.onDestruction: Quickshell.execDetached(["python3", root.backend, "release-if-disabled"])
    Process {
        id: worker
        command: ["python3", root.backend, "daemon"]
        running: true
        onExited: restart.restart()
    }
    Timer {
        id: restart
        interval: 2000
        onTriggered: worker.running = true
    }
}
