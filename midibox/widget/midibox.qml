import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtWebEngine

ApplicationWindow {
	title: "MidiBox"
	visible: true
	flags: Qt.FramelessWindowHint | Qt.Window
	width: 1280
	height: 720

	MidiboxContent {
	}
}
