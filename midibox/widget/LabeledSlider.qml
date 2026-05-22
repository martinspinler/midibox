import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

RowLayout {
	id: root
	property alias labelText: lbl.text
	property alias from: sld.from
	property alias to: sld.to
	property alias stepSize: sld.stepSize
	property alias value: sld.value

	signal moved(real value)

	Label { id: lbl }
	Slider {
		id: sld
		Layout.fillWidth: true
		onMoved: root.moved(value)
	}
}
