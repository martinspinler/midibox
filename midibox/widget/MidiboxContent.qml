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

			Component.onCompleted: currentIndex = 0

			Repeater {
				model: ["Main", "Layers", "Presets", "Playlist", "Stats"]
				TabButton {
					text: qsTr(modelData)
					background: Rectangle {color: parent.checked ? palette.window : palette.button}
				}
			}

			// Connection status indicator (non-clickable).
			// green: OSC server + Midibox HW + piano all connected
			// orange: OSC + HW connected, piano Active Sensing not received
			// red: OSC server or Midibox HW not connected
			TabButton {
				id: statusIndicator
				checkable: false
				text: ""
				implicitWidth: 28
				implicitHeight: mainBar.implicitHeight
				width: implicitWidth

				property bool allConnected: midibox.connected && midibox.hwConnected
				property bool pianoConnected: midibox.general ? midibox.general.piano_connected : false
				property color statusColor: !midibox.connected || !midibox.hwConnected ? "red"
					: (pianoConnected ? "green" : "orange")

				background: Rectangle {
					color: palette.button
				}

				Rectangle {
					anchors.centerIn: parent
					width: 14
					height: 14
					radius: width / 2
					color: statusIndicator.statusColor
					border.color: "black"
					border.width: 1
				}

				ToolTip.text: {
					var osc = midibox.connected ? "ok" : "down"
					var hw = midibox.hwConnected ? "ok" : "down"
					var piano = statusIndicator.pianoConnected ? "ok" : "down"
					return "OSC server: " + osc + "\nMidibox HW: " + hw + "\nPiano: " + piano
				}
				ToolTip.visible: statusMouse.containsMouse
				ToolTip.delay: 200

				MouseArea {
					id: statusMouse
					anchors.fill: parent
					hoverEnabled: true
					cursorShape: Qt.ArrowCursor
					onPressed: mouse.accepted = true
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
