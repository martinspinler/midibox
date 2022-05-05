import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtWebEngine 1.10

//import QtQuick.Controls.Material 2.12
//import QtQuick.Controls.Imagine 2.12
//import QtQuick.Controls.Material 2.12

//import "style"

ApplicationWindow {
	title: "MidiBox"
	visible: true
	flags: Qt.FramelessWindowHint | Qt.Window
	width: 1280 / 1
	height: 720 / 1

	MidiboxContent {
	}
}
