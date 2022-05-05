import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

import QtWebEngine 1.10

Pane {
	property real my_scale: 1
	scale: my_scale
	width: parent.width / my_scale
	height: parent.height / my_scale

	palette {
		window: "#15171a"
		button: "#282b30"
	//	dark:   "#282b30"
		dark:   "orange"
		highlight: "#2196f3"

		light: "yellow"
		link: "yellow"
		linkVisited: "yellow"
		highlightedText:"blue"
		mid: "orange"
		midlight: "#606060"
	//	base: "orange"
		base: "blue"
	//	dark: "blue"
		text: "orange"
		shadow: "orange"
		windowText: "orange"
		buttonText: "orange"
		brightText: "white"
		alternateBase: "blue"
		toolTipBase: "green"
		toolTipText: "green"
	}

	ColumnLayout {
		anchors.fill: parent
		TabBar {
			id: mainBar
			objectName: "mainBar"
			Layout.fillWidth: true

			Repeater {
				model: ["Main", "Layers", "Presets", "Playlist", "Stats"]
				TabButton {
					text: qsTr(modelData)
					background: Rectangle {color: parent.checked ? palette.window : palette.button}
				}
			}
		}

		StackLayout {
			Layout.fillWidth: true
			currentIndex: mainBar.currentIndex

			MainPanel {
			}

			Layers {
			}

			ColumnLayout{
				//columns: 2
				Button {text:"Pno (+1ova) / Bs"; onClicked: midibox.loadPreset(0)}
				Button {text:"P2"; onClicked: midibox.loadPreset(1)}
				Button {text:"P3"; onClicked: midibox.loadPreset(2)}
			}

			WebEngineView {
				url: "https://perfecttime.livelist.cz/"
				//zoomFactor: reterm ? 2 : 1
			}

			MidiStats {
			}
		}
	}
}
