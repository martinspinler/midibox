import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
	Layout.fillWidth: true
	ColumnLayout {
		id: layerx
		anchors.fill: parent

		property var current: midibox.layers[layersBar.currentIndex]

		TabBar {
			Layout.fillWidth: true
			id: layersBar
			objectName: "layersBar"
			Repeater {
				Layout.fillWidth: true
				model: 8
				TabButton {
					objectName: "layersBarButton"
					background: Rectangle {
						color: parent.checked ? palette.highlight : palette.window

						Rectangle {
							anchors.fill: parent
							opacity: 0.5
							color: midibox.layers[modelData].active ? "green" : "red"
						}
					}

					//text: modelData + 1
					text: midibox.layers[modelData].shortName
				}
			}
		}
		
		TabBar {
			id: layerBar
			Layout.fillWidth: true

			Component.onCompleted: currentIndex = 0
			Repeater {
				Layout.fillWidth: true
				model: ["Program", "Config", "Pedals"]

				delegate: TabButton {
					text: qsTr(modelData)
					background: Rectangle {color: parent.checked ? palette.window : palette.button}
				}
			}
		}

		StackLayout {
			Layout.fillWidth: true
			Layout.margins: 10

			currentIndex: layerBar.currentIndex
			Item {
				Layout.fillWidth: true
				//anchors.fill: parent

				GridLayout {
					anchors.fill: parent
					columns: 2
					Column {
						Label{text: qsTr("Program     ")}

						RoundButton {
							onClicked: {
								layerx.current.transposition = 0;
								layerx.current.rangel = 0;
								layerx.current.rangeu = 127;
								layerx.current.volume = 100;
							}
							
							text: "Reset"
						}
						Switch{
							onToggled: layerx.current.active = checked
							checked: layerx.current.active
							text: "Active"
						}

					}
					GroupBox {
						Layout.fillWidth: true
						Layout.fillHeight: true

						ListView {
							anchors.fill: parent
							model: programPresetsModel
							ScrollBar.vertical: ScrollBar {
								active: true
							}
							delegate: Button {
								checkable: true
								checked: layerx.current.program == model.pid
								onClicked: layerx.current.program = model.pid
								width: parent.width
								text: model.text
								background: Rectangle {
									color: checked ? palette.highlight : palette.window
								}
							}
						}
					}
				}
			}
			Item { // GroupBox {
				Layout.fillWidth: true
				GridLayout {
					width: parent.width
					columns: 2

					Label {text: "Range:\n" + midibox.note2text(layerx.current.rangel) + " - " + midibox.note2text(layerx.current.rangeu)}
					RowLayout {
						width: parent.width
						RoundButton {id: rsL; icon.name: "color-select-symbolic"; onClicked: midibox.requestKey(layersBar.currentIndex, 'rangel')}
						RangeSlider {
							id: rangeSlider
							Layout.fillWidth: true
							Layout.alignment: Qt.AlignHCenter

							from: 21; to: 108; stepSize: 1
							first.value: layerx.current.rangel
							second.value: layerx.current.rangeu
							first.onMoved: layerx.current.rangel = first.value
							second.onMoved: layerx.current.rangeu = second.value
						}
						RoundButton {id:rsR; icon.name: "color-select-symbolic"; onClicked: midibox.requestKey(layersBar.currentIndex, 'rangeu')}
					}

					Label {text: "Transposition:\n" + 
						((layerx.current.transposition == 0) ? " " : (layerx.current.transposition < 0 ? "-" : "+")) + 
						Math.floor(Math.abs(layerx.current.transposition / 12)) + "." + Math.abs(layerx.current.transposition % 12)
					}
					RowLayout {
						id: transpRow
						width: parent.width
						RoundButton {icon.name: "list-remove"; onClicked: layerx.current.transposition -= 12}
						Slider {
							Layout.fillWidth: true
							id: transpositionSlider
							from: -63; to: 63; stepSize: 1
							value: layerx.current.transposition
							onMoved: layerx.current.transposition = value
						}
						RoundButton {icon.name: "list-add"; onClicked: layerx.current.transposition += 12}
					}

					Label {text: "   Semitones:"}
					RowLayout {
						id: transpFineRow
						width: parent.width
						RoundButton {icon.name: "list-remove"; onClicked: layerx.current.transposition -= 1}
						/*
						Slider {
							Layout.fillWidth: true
							id: transpositionFineSlider
							from: 0; to: 12; stepSize: 1
							value: layerx.current.transposition % 12
							onMoved: layerx.current.transposition = Math.abs(value % 12 + transpositionSlider.value * 12)
						}
						*/
						Item {
							id: transpFineSp
							Layout.fillWidth: true
						}
						RoundButton {icon.name: "list-add"; onClicked: layerx.current.transposition += 1}
					}


					Label {text: "Volume:\n" + layerx.current.volume}
					RowLayout { 
						width: parent.width
						RoundButton {icon.name: "audio-volume-low-symbolic"; onClicked: layerx.current.volume -= 10}
						Slider {
							Layout.fillWidth: true
							Layout.alignment: Qt.AlignHCenter
							from: 0; to: 127; stepSize: 1
							value: layerx.current.volume
							onMoved: layerx.current.volume = Math.round(value)
						}
						RoundButton {icon.name: "audio-volume-high-symbolic"; onClicked: layerx.current.volume += 10}
					}
				}
			}
		}
	}
}
