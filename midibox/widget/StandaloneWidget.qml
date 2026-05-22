import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtWebEngine

Pane {
	visible: true
	width: 640   // 1280 / 2
	height: 360  // 720 / 2
	padding: 0

	Layout.fillWidth: true
	Layout.fillHeight: true

	MidiboxContent {
	}
}
