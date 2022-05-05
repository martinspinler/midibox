import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtWebEngine 1.10

Pane {
	visible: true
	width: 1280 / 2
	height: 720 / 2
	padding: 0

	Layout.fillWidth: true
	Layout.fillHeight:true
	//anchors.fill: parent

	MidiboxContent {
	}
}
