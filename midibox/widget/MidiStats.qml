import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtCharts

ChartView {
	id: msc
	objectName: "MidiStatsChart"
	title: "MIDI stats"
	antialiasing: true

	ValueAxis {
		id: xAxis
		min: 0
		max: 3000
	}

	ValueAxis {
		id: yAxis
		min: 0
		max: 150
	}

	LineSeries {
		id: myser
		axisX: xAxis
		axisY: yAxis
		name: "SplineSeries"

		XYPoint { x: 0; y: 0 }
		XYPoint { x: 1; y: 1 }

		Connections {
			target: monitor
			function onStatsUpdated(timestamp, count) {
				myser.insert(0, timestamp, count)
				zoomReset()
			}
		}
	}
}
