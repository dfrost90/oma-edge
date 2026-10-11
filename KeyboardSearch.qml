import QtQuick

// Never make this native input editable: affected Qt builds eagerly read the
// clipboard on dataChanged, before maximumLength or a validator can protect us.
// Native read-only selection/navigation remain available; bounded key events
// update the search string without accessing either clipboard selection.
TextInput {
    id: root
    property string placeholderText: ""
    property color foreground: "white"
    property color accent: foreground
    readOnly: true
    maximumLength: 256
    activeFocusOnTab: true
    selectByMouse: true
    cursorVisible: activeFocus
    clip: true
    color: foreground
    selectionColor: accent
    selectedTextColor: "black"
    verticalAlignment: TextInput.AlignVCenter
    Accessible.name: placeholderText

    Text {
        anchors.fill: parent
        text: root.placeholderText
        textFormat: Text.PlainText
        font: root.font
        color: root.foreground
        opacity: 0.5
        visible: root.text.length === 0
        verticalAlignment: Text.AlignVCenter
    }

    function replaceSelection(replacement) {
        var start = selectionStart
        var end = selectionEnd
        var room = maximumLength - (text.length - (end - start))
        var bounded = replacement.slice(0, room)
        // QML's JS iterator may expose UTF-16 code units. Do not split a pair.
        var last = bounded.charCodeAt(bounded.length - 1)
        if (last >= 0xd800 && last <= 0xdbff) bounded = bounded.slice(0, -1)
        text = text.slice(0, start) + bounded + text.slice(end)
        cursorPosition = start + bounded.length
    }

    function handleKey(event) {
        var shortcut = event.modifiers & (Qt.ControlModifier | Qt.MetaModifier | Qt.AltModifier)
        if (shortcut) {
            if (event.key === Qt.Key_A && (event.modifiers & Qt.ControlModifier)) {
                selectAll()
                event.accepted = true
                return true
            }
            // Do not implement cut/paste or clipboard shortcuts. Read-only Qt
            // also prevents middle-click paste and native editing actions.
            return false
        }
        if (event.key === Qt.Key_Backspace || event.key === Qt.Key_Delete) {
            if (selectionStart === selectionEnd) {
                var position = cursorPosition
                if (event.key === Qt.Key_Backspace && position > 0) {
                    var previous = text.charCodeAt(position - 1)
                    var count = previous >= 0xdc00 && previous <= 0xdfff && position > 1 ? 2 : 1
                    select(position - count, position)
                } else if (event.key === Qt.Key_Delete && position < text.length) {
                    var next = text.charCodeAt(position)
                    var count = next >= 0xd800 && next <= 0xdbff && position + 1 < text.length ? 2 : 1
                    select(position, position + count)
                }
            }
            replaceSelection("")
        } else if (event.text && !/[\x00-\x1f\x7f]/.test(event.text)) {
            replaceSelection(event.text)
        } else {
            return false
        }
        event.accepted = true
        return true
    }

    Keys.onPressed: function(event) { handleKey(event) }
}
