import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15


Column{
	//Layout.fillWidth: true
	//padding: 0
	Switch{
		text: "Enable"
		onToggled: midibox.enable = checked
		checked: midibox.enable
	}
	Switch{
		text: "Transpose 1ova on ch0"
		onToggled: midibox.transpositionExtra = checked
		checked: midibox.transpositionExtra
	}
	RoundButton {
		onClicked: midibox.split12()
		text: "Split 1-2"
		icon.name: "sidebar-show-symbolic"
	}
	RoundButton {
		onClicked: midibox.allSoundsOff()
		text: "All sounds off"
		icon.name: "emblem-important-symbolic"
	}

	GroupBox {
		width: parent.width
		height: 8*8 + 16
		//leftPadding: 0
		padding: 1
		Control {
			anchors.fill: parent
			Rectangle {
				width: (parent.width/127)*21
				height: parent.height
				color: "black"
			}

			Rectangle {
				Layout.fillWidth: true
				x: 108 * (parent.width/127)
				width: (127-108) * (parent.width/127)
				height: parent.height
				color: "black"
			}

			Repeater {
				anchors.fill: parent
				model: 8
				Item {
					anchors.fill: parent
					Rectangle {
						//Layout.fillWidth: true
						y: modelData * parent.height/8
						x: midibox.layers[modelData].rangel * (parent.width/127)
						width: midibox.layers[modelData].rangeu * (parent.width/127) - midibox.layers[modelData].rangel * 5
						height: midibox.layers[modelData].active ? parent.height/8 - 2 : 1
						color: ( modelData % 2 ? "orange" : "orange")
					}
				}
			}
		}
	}
}

