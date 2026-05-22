import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

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
							color: midibox.layers[modelData].enabled
								? (midibox.layers[modelData].active_status ? "green" : "blue")
								: "red"
						}
					}

					text: midibox.layers[modelData].shortName
				}
			}
		}

		Connections {
			target: layersBar
			function onCurrentIndexChanged() {
				layerBar.currentIndex = 0
			}
		}

		TabBar {
			id: layerBar
			Layout.fillWidth: true
			Repeater {
				Layout.fillWidth: true
				model: ["Program", "Config", "Effects", "Pedals", "Harmonic"]

				delegate: TabButton {
					text: qsTr(modelData)
					background: Rectangle {
						color: parent.checked ? palette.window : palette.button
					}
				}
			}
		}

		StackLayout {
			Layout.fillWidth: true
			Layout.margins: 10

			currentIndex: layerBar.currentIndex

			Item {
				Layout.fillWidth: true

				GridLayout {
					anchors.fill: parent
					columns: 2
					Column {
						Label {
							text: qsTr("Program")
						}

						RoundButton {
							onClicked: layerx.current.reset()
							text: "Reset"
						}
						Switch {
							onToggled: layerx.current.enabled = checked
							checked: layerx.current.enabled
							text: "Enabled"
						}

						Switch {
							onToggled: layerx.current.active = checked
							checked: layerx.current.active
							text: "Active"
						}
						ComboBox {
							Layout.fillWidth: true
							model: playModeModel
							onActivated: layerx.current.mode = currentValue
							currentIndex: indexOfValue(layerx.current.mode)
							textRole: 'text'
							valueRole: 'value'
						}
					}
					GroupBox {
						Layout.fillWidth: true
						Layout.fillHeight: true

						ListView {
							anchors.fill: parent
							model: programPresetsModel
							clip: true
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

			Item {
				Layout.fillWidth: true
				GridLayout {
					anchors.fill: parent
					columns: 2

					Label {
						text: "Range:\n" + midibox.note2text(layerx.current.rangel) + " - " + midibox.note2text(layerx.current.rangeu)
					}
					RowLayout {
						width: parent.width
						RoundButton {
							id: rsL
							icon.name: "color-select-symbolic"
							onClicked: midibox.requestKey(layersBar.currentIndex, 'rangel')
						}
						RangeSlider {
							id: rangeSlider
							Layout.fillWidth: true
							Layout.alignment: Qt.AlignHCenter

							from: 21
							to: 108
							stepSize: 1
							first.value: layerx.current.rangel
							second.value: layerx.current.rangeu
							first.onMoved: layerx.current.rangel = first.value
							second.onMoved: layerx.current.rangeu = second.value
						}
						RoundButton {
							id: rsR
							icon.name: "color-select-symbolic"
							onClicked: midibox.requestKey(layersBar.currentIndex, 'rangeu')
						}
					}

					Label {
						text: "Transposition:\n" +
							((layerx.current.transposition == 0)
								? " "
								: (layerx.current.transposition < 0 ? "-" : "+")) +
							Math.floor(Math.abs(layerx.current.transposition / 12)) + "." +
							Math.abs(layerx.current.transposition % 12)
					}
					RowLayout {
						id: transpRow
						width: parent.width
						RoundButton {
							icon.name: "list-remove"
							onClicked: layerx.current.transposition -= 12
						}
						Slider {
							Layout.fillWidth: true
							id: transpositionSlider
							from: -63
							to: 63
							stepSize: 1
							value: layerx.current.transposition
							onMoved: layerx.current.transposition = value
						}
						RoundButton {
							icon.name: "list-add"
							onClicked: layerx.current.transposition += 12
						}
					}

					Label {
						text: "   Semitones:"
					}
					RowLayout {
						id: transpFineRow
						width: parent.width
						RoundButton {
							icon.name: "list-remove"
							onClicked: layerx.current.transposition -= 1
						}
						Item {
							id: transpFineSp
							Layout.fillWidth: true
						}
						RoundButton {
							icon.name: "list-add"
							onClicked: layerx.current.transposition += 1
						}
					}

					Label {
						text: "Volume:\n" + layerx.current.volume
					}
					RowLayout {
						width: parent.width
						RoundButton {
							icon.name: "audio-volume-low-symbolic"
							onClicked: layerx.current.volume -= 10
						}
						Slider {
							Layout.fillWidth: true
							Layout.alignment: Qt.AlignHCenter
							from: 0
							to: 127
							stepSize: 1
							value: layerx.current.volume
							onMoved: layerx.current.volume = Math.round(value)
						}
						RoundButton {
							icon.name: "audio-volume-high-symbolic"
							onClicked: layerx.current.volume += 10
						}
					}
				}
			}

			/* Effects */
			Item {
				Layout.fillWidth: true
				ColumnLayout {
					anchors.fill: parent
					LabeledSlider {
						labelText: qsTr("Release: " + layerx.current.release)
						from: -64
						to: 63
						stepSize: 1
						value: layerx.current.release
						onMoved: layerx.current.release = Math.round(value)
					}
					LabeledSlider {
						labelText: qsTr("Attack: " + layerx.current.attack)
						from: -64
						to: 63
						stepSize: 1
						value: layerx.current.attack
						onMoved: layerx.current.attack = Math.round(value)
					}
					LabeledSlider {
						labelText: qsTr("Cutoff: " + layerx.current.cutoff)
						from: -64
						to: 63
						stepSize: 1
						value: layerx.current.cutoff
						onMoved: layerx.current.cutoff = Math.round(value)
					}
					LabeledSlider {
						labelText: qsTr("Decay: " + layerx.current.decay)
						from: -64
						to: 63
						stepSize: 1
						value: layerx.current.decay
						onMoved: layerx.current.decay = Math.round(value)
					}
					LabeledSlider {
						labelText: qsTr("Portamento time: " + layerx.current.portamento_time)
						from: 0
						to: 127
						stepSize: 1
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
							columns: 3
							Label {
								text: qsTr("Ped " + (modelData + 1))
							}

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
				ColumnLayout {
					anchors.fill: parent
					LabeledSlider {
						labelText: qsTr("Percussion: " + layerx.current.percussion)
						from: 0
						to: 4
						stepSize: 1
						value: layerx.current.percussion
						onMoved: layerx.current.percussion = Math.round(value)
					}
					LabeledSlider {
						labelText: qsTr("Harmonic Bar 16': " + layerx.current.harmonic_bar0)
						from: 0
						to: 15
						stepSize: 1
						value: layerx.current.harmonic_bar0
						onMoved: layerx.current.harmonic_bar0 = Math.round(value)
					}
					LabeledSlider {
						labelText: qsTr("Harmonic Bar 5+1/3': " + layerx.current.harmonic_bar1)
						from: 0
						to: 15
						stepSize: 1
						value: layerx.current.harmonic_bar1
						onMoved: layerx.current.harmonic_bar1 = Math.round(value)
					}
					LabeledSlider {
						labelText: qsTr("Harmonic Bar 8': " + layerx.current.harmonic_bar2)
						from: 0
						to: 15
						stepSize: 1
						value: layerx.current.harmonic_bar2
						onMoved: layerx.current.harmonic_bar2 = Math.round(value)
					}
					LabeledSlider {
						labelText: qsTr("Harmonic Bar 4': " + layerx.current.harmonic_bar3)
						from: 0
						to: 15
						stepSize: 1
						value: layerx.current.harmonic_bar3
						onMoved: layerx.current.harmonic_bar3 = Math.round(value)
					}
					LabeledSlider {
						labelText: qsTr("Harmonic Bar 2+2/3': " + layerx.current.harmonic_bar4)
						from: 0
						to: 15
						stepSize: 1
						value: layerx.current.harmonic_bar4
						onMoved: layerx.current.harmonic_bar4 = Math.round(value)
					}
					LabeledSlider {
						labelText: qsTr("Harmonic Bar 2': " + layerx.current.harmonic_bar5)
						from: 0
						to: 15
						stepSize: 1
						value: layerx.current.harmonic_bar5
						onMoved: layerx.current.harmonic_bar5 = Math.round(value)
					}
					LabeledSlider {
						labelText: qsTr("Harmonic Bar 1+3/5': " + layerx.current.harmonic_bar6)
						from: 0
						to: 15
						stepSize: 1
						value: layerx.current.harmonic_bar6
						onMoved: layerx.current.harmonic_bar6 = Math.round(value)
					}
					LabeledSlider {
						labelText: qsTr("Harmonic Bar 1+1/3': " + layerx.current.harmonic_bar7)
						from: 0
						to: 15
						stepSize: 1
						value: layerx.current.harmonic_bar7
						onMoved: layerx.current.harmonic_bar7 = Math.round(value)
					}
					LabeledSlider {
						labelText: qsTr("Harmonic Bar 1': " + layerx.current.harmonic_bar8)
						from: 0
						to: 15
						stepSize: 1
						value: layerx.current.harmonic_bar8
						onMoved: layerx.current.harmonic_bar8 = Math.round(value)
					}
				}
			}
		}
	}
}
