import QtQuick
import QtTest
import ".."

Item {
    width: 400; height: 100
    KeyboardSearch { id: field; anchors.fill: parent }
    TestCase {
        name: "KeyboardSearch"
        when: windowShown
        function init() { field.text = ""; field.forceActiveFocus() }
        function test_typing_and_selection() {
            keyClick(Qt.Key_A)
            keyClick(Qt.Key_B)
            keyClick(Qt.Key_C)
            compare(field.text, "abc")
            keyClick(Qt.Key_Left)
            keyClick(Qt.Key_Backspace)
            compare(field.text, "ac")
            keyClick(Qt.Key_Delete)
            compare(field.text, "a")
            keyClick(Qt.Key_A, Qt.ControlModifier)
            keyClick(Qt.Key_Z)
            compare(field.text, "z")
        }
        function test_unicode_and_bound() {
            field.handleKey({text: "Київ😀", key: 0, modifiers: 0, accepted: false})
            compare(field.text, "Київ😀")
            keyClick(Qt.Key_Backspace)
            compare(field.text, "Київ")
            field.text = "a".repeat(255)
            field.cursorPosition = 255
            field.handleKey({text: "😀", key: 0, modifiers: 0, accepted: false})
            compare(field.text.length, 255)
            keyClick(Qt.Key_B)
            keyClick(Qt.Key_C)
            compare(field.text.length, 256)
        }
        function test_clipboard_shortcuts_do_not_edit() {
            field.text = "query"
            field.selectAll()
            keyClick(Qt.Key_V, Qt.ControlModifier)
            keyClick(Qt.Key_Insert, Qt.ShiftModifier)
            keyClick(Qt.Key_X, Qt.ControlModifier)
            field.paste()
            compare(field.text, "query")
            verify(field.readOnly)
        }
    }
}
