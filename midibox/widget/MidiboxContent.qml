import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

import QtWebEngine 1.10

Pane {
	property real my_scale: 1
	scale: my_scale
	width: parent.width / my_scale
	height: parent.height / my_scale
	transformOrigin: Item.TopLeft

	Layout.fillHeight: true

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
		Layout.fillHeight: true
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
			Layout.fillHeight: true
			currentIndex: mainBar.currentIndex

			MainPanel {
			}

			Layers {
			}

			GridLayout {
				objectName: "presets"
				rows: 6
				flow: GridLayout.TopToBottom
				Button {text:"P1"; onClicked: midibox.loadPreset(0)}
				Button {text:"P2"; onClicked: midibox.loadPreset(1)}
				Button {text:"P3"; onClicked: midibox.loadPreset(2)}
				Button {text:"P4"; onClicked: midibox.loadPreset(3)}
				Button {text:"P5"; onClicked: midibox.loadPreset(4)}
				Button {text:"P6"; onClicked: midibox.loadPreset(5)}
				Button {text:"P7"; onClicked: midibox.loadPreset(6)}
				Button {text:"P8"; onClicked: midibox.loadPreset(7)}
				Button {text:"P9"; onClicked: midibox.loadPreset(8)}
				Button {text:"P10"; onClicked: midibox.loadPreset(9)}
				Button {text:"P11"; onClicked: midibox.loadPreset(10)}
				Button {text:"P12"; onClicked: midibox.loadPreset(11)}
			}

			WebEngineView {
				objectName: "playlistWebView"
				url: "https://perfecttime.livelist.cz/"
				//zoomFactor: reterm ? 2 : 1
			}

			MidiStats {
			}
		}
	}
}
