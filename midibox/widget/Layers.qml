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
							color: midibox.layers[modelData].enabled ? (midibox.layers[modelData].active ? "green" : "blue") : "red"
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
/* FIXME: doesn't updates for example pedals cc */
			Component.onCompleted: currentIndex = 0
			Repeater {
				Layout.fillWidth: true
				model: ["Program", "Config", "Effects", "Pedals", "Harmonic"]

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
							onClicked: layerx.current.reset()
							text: "Reset"
						}
						Switch{
							onToggled: layerx.current.enabled = checked
							checked: layerx.current.enabled
							text: "Enabled"
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
								checked: layerx.current.program == model.value
								onClicked: layerx.current.program = model.value
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
					anchors.fill: parent
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
			/* Effects */
			Item {
				Layout.fillWidth: true
				GridLayout {
					anchors.fill: parent
					columns: 2

					Label{text: qsTr("Release: " + (layerx.current.release))}
					Slider {
						Layout.fillWidth: true
						Layout.alignment: Qt.AlignHCenter
						from: -64; to: 63; stepSize: 1
						value: layerx.current.release
						onMoved: layerx.current.release = Math.round(value)
					}
					Label{text: qsTr("Attack: " + (layerx.current.attack))}
					Slider {
						Layout.fillWidth: true
						Layout.alignment: Qt.AlignHCenter
						from: -64; to: 63; stepSize: 1
						value: layerx.current.attack
						onMoved: layerx.current.attack = Math.round(value)
					}
					Label{text: qsTr("Cutoff: " + (layerx.current.cutoff))}
					Slider {
						Layout.fillWidth: true
						Layout.alignment: Qt.AlignHCenter
						from: -64; to: 63; stepSize: 1
						value: layerx.current.cutoff
						onMoved: layerx.current.cutoff = Math.round(value)
					}
					Label{text: qsTr("Decay: " + (layerx.current.decay))}
					Slider {
						Layout.fillWidth: true
						Layout.alignment: Qt.AlignHCenter
						from: -64; to: 63; stepSize: 1
						value: layerx.current.decay
						onMoved: layerx.current.decay = Math.round(value)
					}
					Label{text: qsTr("Portamento time: " + (layerx.current.portamento_time))}
					Slider {
						Layout.fillWidth: true
						Layout.alignment: Qt.AlignHCenter
						from: 0; to: 127; stepSize: 1
						value: layerx.current.portamento_time
						onMoved: layerx.current.portamento_time = Math.round(value)
					}
				}

			}
			/* Pedals */
			Item {
				Layout.fillWidth: true
				GridLayout {
					anchors.fill: parent
					columns: 2

					Repeater {
						id: pedal
						Layout.fillWidth: true
						model: 8

						GridLayout {
							Layout.fillWidth: true
							//anchors.fill: parent
							columns: 3
							Label{text: qsTr("Pedal " + (modelData+1))}

							ComboBox {
								Layout.fillWidth: true
								model: pedalCcModel
								onActivated: layerx.current.pedals[modelData].cc = currentValue
								currentIndex: indexOfValue(layerx.current.pedals[modelData].cc)
								textRole: 'text'
								valueRole: 'value'
							}
							ComboBox {
								Layout.fillWidth: true
								model: pedalModeModel
								onActivated: layerx.current.pedals[modelData].mode = currentValue
								currentIndex: indexOfValue(layerx.current.pedals[modelData].mode)
								textRole: 'text'
								valueRole: 'value'
							}
						}
					}
				}
			}
			Item {
				Layout.fillWidth: true
				GridLayout {
					anchors.fill: parent
					columns: 2

					Label{text: qsTr("Percussion: " + (layerx.current.percussion))}
					Slider {
						Layout.fillWidth: true
						Layout.alignment: Qt.AlignHCenter
						from: 0; to: 4; stepSize: 1
						value: layerx.current.percussion
						onMoved: layerx.current.percussion = Math.round(value)
					}
					Label{text: qsTr("Harmonic Bar 16': " + (layerx.current.harmonic_bar0))}
					Slider {
						Layout.fillWidth: true
						Layout.alignment: Qt.AlignHCenter
						from: 0; to: 15; stepSize: 1
						value: layerx.current.harmonic_bar0
						onMoved: layerx.current.harmonic_bar0 = Math.round(value)
					}
					Label{text: qsTr("Harmonic Bar 5+1/3': " + (layerx.current.harmonic_bar1))}
					Slider {
						Layout.fillWidth: true
						Layout.alignment: Qt.AlignHCenter
						from: 0; to: 15; stepSize: 1
						value: layerx.current.harmonic_bar1
						onMoved: layerx.current.harmonic_bar1 = Math.round(value)
					}
					Label{text: qsTr("Harmonic Bar 8': " + (layerx.current.harmonic_bar2))}
					Slider {
						Layout.fillWidth: true
						Layout.alignment: Qt.AlignHCenter
						from: 0; to: 15; stepSize: 1
						value: layerx.current.harmonic_bar2
						onMoved: layerx.current.harmonic_bar2 = Math.round(value)
					}
					Label{text: qsTr("Harmonic Bar 4': " + (layerx.current.harmonic_bar3))}
					Slider {
						Layout.fillWidth: true
						Layout.alignment: Qt.AlignHCenter
						from: 0; to: 15; stepSize: 1
						value: layerx.current.harmonic_bar3
						onMoved: layerx.current.harmonic_bar3 = Math.round(value)
					}
					Label{text: qsTr("Harmonic Bar 2+2/3': " + (layerx.current.harmonic_bar4))}
					Slider {
						Layout.fillWidth: true
						Layout.alignment: Qt.AlignHCenter
						from: 0; to: 15; stepSize: 1
						value: layerx.current.harmonic_bar4
						onMoved: layerx.current.harmonic_bar4 = Math.round(value)
					}
					Label{text: qsTr("Harmonic Bar 2': " + (layerx.current.harmonic_bar5))}
					Slider {
						Layout.fillWidth: true
						Layout.alignment: Qt.AlignHCenter
						from: 0; to: 15; stepSize: 1
						value: layerx.current.harmonic_bar5
						onMoved: layerx.current.harmonic_bar5 = Math.round(value)
					}
					Label{text: qsTr("Harmonic Bar 1+3/5': " + (layerx.current.harmonic_bar6))}
					Slider {
						Layout.fillWidth: true
						Layout.alignment: Qt.AlignHCenter
						from: 0; to: 15; stepSize: 1
						value: layerx.current.harmonic_bar6
						onMoved: layerx.current.harmonic_bar6 = Math.round(value)
					}
					Label{text: qsTr("Harmonic Bar 1+1/3': " + (layerx.current.harmonic_bar7))}
					Slider {
						Layout.fillWidth: true
						Layout.alignment: Qt.AlignHCenter
						from: 0; to: 15; stepSize: 1
						value: layerx.current.harmonic_bar7
						onMoved: layerx.current.harmonic_bar7 = Math.round(value)
					}
					Label{text: qsTr("Harmonic Bar 1': " + (layerx.current.harmonic_bar8))}
					Slider {
						Layout.fillWidth: true
						Layout.alignment: Qt.AlignHCenter
						from: 0; to: 15; stepSize: 1
						value: layerx.current.harmonic_bar8
						onMoved: layerx.current.harmonic_bar8 = Math.round(value)
					}
				}
			}
		}
	}
}
