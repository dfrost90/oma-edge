import QtQuick
import Quickshell
import Quickshell.Io

Item {
    id: root
    readonly property string backend: decodeURIComponent(Qt.resolvedUrl("backend.py").toString().replace("file://", ""))
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
