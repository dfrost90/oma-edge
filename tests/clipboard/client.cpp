#include <QGuiApplication>
#include <QClipboard>
#include <QQmlEngine>
#include <QQmlComponent>
#include <QTimer>
#include <QElapsedTimer>
#include <QDebug>
#include <QMimeData>

int main(int argc, char **argv) {
    QGuiApplication app(argc,argv);
    QQmlEngine engine;
    QQmlComponent component(&engine);
    QByteArray qml=R"(
import QtQuick
import QtQuick.Controls
Item {
    width: 400; height: 200
    SpinBox {
        id: spin; from: 1; to: 10; value: 1; editable: true
        contentItem: TextInput {
            objectName: "weight"; text: spin.displayText
            readOnly: !spin.editable; validator: spin.validator
            inputMethodHints: Qt.ImhFormattedNumbersOnly
        }
    }
    TextField { objectName: "search"; y: 60; placeholderText: "Search apps and window titles" }
}
)";
    if(qEnvironmentVariableIsSet("PATCHED_INPUTS")) {
        qml.prepend("import \"" + QUrl::fromLocalFile(qEnvironmentVariable("EDGE_PLUGIN_DIR")).toEncoded() + "\"\n");
        qml.replace("editable: true", "editable: false");
        qml.replace("TextField { objectName", "KeyboardSearch { objectName");
    }
    if(qEnvironmentVariableIsSet("SAFE_INPUTS")) { qml.replace("editable: true", "editable: false"); qml.replace("TextField { objectName", "TextField { readOnly: true; objectName"); }
    component.setData(qml,QUrl());
    auto root=component.create();
    if(!root) { qCritical()<<component.errors(); return 2; }
    QElapsedTimer clock; clock.start();
    auto clip=QGuiApplication::clipboard();
    QObject::connect(clip,&QClipboard::dataChanged,[&] {
        qInfo()<<"CHANGED"<<clock.elapsed()<<"canPaste"<<root->findChild<QObject*>("search")->property("canPaste");
    });
    QTimer heartbeat;
    QObject::connect(&heartbeat,&QTimer::timeout,[&]{qInfo()<<"HEARTBEAT"<<clock.elapsed();});
    heartbeat.start(250);
    if(argc>1) QTimer::singleShot(4000,[&] {
        auto field=root->findChild<QObject*>(argv[1]);
        qInfo()<<"PASTE START"<<clock.elapsed();
        QMetaObject::invokeMethod(field,"paste");
        qInfo()<<"PASTE END"<<clock.elapsed()<<"length"<<field->property("text").toString().size();
    });
    QTimer::singleShot(9500,&app,&QCoreApplication::quit);
    int result=app.exec(); delete root; return result;
}
