import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15


ColumnLayout {
	Layout.fillWidth: true
	Layout.fillHeight: true

	TabBar {
		id: mainBar
		Layout.fillWidth: true
		Component.onCompleted: currentIndex = 0
		Repeater {
			Layout.fillWidth: true
			model: ["Main", "Pedals"]

			delegate: TabButton {
				text: qsTr(modelData)
				background: Rectangle {color: parent.checked ? palette.window : palette.button}
			}
		}
	}

	StackLayout {
		Layout.fillWidth: true
		Layout.fillHeight: true
		Layout.margins: 10

		currentIndex: mainBar.currentIndex

		Column {
			Layout.fillWidth: true
			Switch{
				text: "Enable"
				onToggled: midibox.general.enabled = checked
				checked: midibox.general.enabled
			}
			Switch{
				text: "Transpose 1ova on ch0"
				onToggled: midibox.transpositionExtra = checked
				checked: midibox.transpositionExtra
			}
			RoundButton {
				onClicked: midibox.initialize()
				text: "Init"
				icon.name: "sidebar-show-symbolic"
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
			Label {
				text: "Tempo:\n" + midibox.general.tempo
			}
			Slider {
				width: parent.width
				id:tempoSlider
				from: 40; to: 300; stepSize: 1
				value: midibox.general.tempo
				onMoved: midibox.general.tempo = value
			}

			GroupBox {
				property int rangeH: 10
				id: rangeOverview
				width: parent.width
				height: 8*rangeH + 2
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
								y: modelData * rangeOverview.rangeH
								x: midibox.layers[modelData].rangel * (parent.width/127)
								width: (midibox.layers[modelData].rangeu  - midibox.layers[modelData].rangel) * (parent.width/127)
								height: rangeOverview.rangeH - 2
								color: ( midibox.layers[modelData].enabled ? "orange" : "#332222")
							}
						}
					}
				}
			}
		}

		/* Pedals */
		Item{
			Layout.fillWidth: true
			Layout.fillHeight: true
			Flickable{
				Layout.fillWidth: true
				Layout.fillHeight: true
				anchors.fill: parent
				contentHeight: pedalGL.height
				clip: true

				ScrollBar.vertical: ScrollBar {
					policy: ScrollBar.AsNeeded
				}

				GridLayout {
					id: pedalGL
					columns: 3
					Layout.fillWidth: true

					Repeater {
						model: 8
						Item {
							Slider {
								Layout.alignment: Qt.AlignRight
								parent: pedalGL
								from: 0; to: 127; stepSize: 1
								value: midibox.general.pedals[modelData].max
								onMoved: midibox.general.pedals[modelData].max = Math.round(value)
							}
							Slider {
								Layout.alignment: Qt.AlignRight
								parent: pedalGL
								from: 0; to: 127; stepSize: 1
								value: midibox.general.pedals[modelData].min
								onMoved: midibox.general.pedals[modelData].min = Math.round(value)
							}
							Label {
								parent: pedalGL
								text: qsTr("Ped " + (modelData+1) + ": " + midibox.general.pedals[modelData].min) + " - " + midibox.general.pedals[modelData].max
							}
						}
					}
				}
			}
		}
	}
}

