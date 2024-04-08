import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtCharts 2.1

ChartView {
	id: msc
	objectName: "MidiStatsChart"
	title: "MIDI stats"
	antialiasing: true

	ValueAxis {
        id: xAxis
        min: 0
        max: 200
    }

	LineSeries {
		id: myser
		Connections{
			target: monitor

			function onFoo(x, y){
				myser.insert(0, x, y)

				zoomReset()

				msc.axisX(msc.series(0)).max = 3000
				msc.axisY(msc.series(0)).max = 150
			}
		}
		name: "SplineSeries"
		XYPoint { x:   0; y: 0 }
		XYPoint { x: 1; y: 1 }
		//XYPoint { x: 100; y: 100 }
	}
}
