import QtQuick 2.3

QtObject {
	property string program: "piano"
	property string shortName: "Pn"
	property bool enabled: true
	property bool active: true

	property int rangel: 44
	property int rangeu: 120
	property int volume: 120
	property int transposition: 12

	property int release: 12
	property int attack: 12
	property int cutoff: 12
	property int decay: 12
	property int portamento_time: 12

	property int percussion: 1
	property int harmonic_bar0: 12
	property int harmonic_bar1: 12
	property int harmonic_bar2: 12
	property int harmonic_bar3: 12
	property int harmonic_bar4: 12
	property int harmonic_bar5: 12
	property int harmonic_bar6: 12
	property int harmonic_bar7: 12
	property int harmonic_bar8: 12

	property list<QtObject> pedals: [
		DummyPedalLayer{},
		DummyPedalLayer{},
		DummyPedalLayer{},
		DummyPedalLayer{},
		DummyPedalLayer{},
		DummyPedalLayer{},
		DummyPedalLayer{},
		DummyPedalLayer{},
	]
}
