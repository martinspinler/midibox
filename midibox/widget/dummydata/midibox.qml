import QtQuick 2.3

QtObject {
	property bool transpositionExtra: true

	function note2text(i) {
        return "a"
    }

	property QtObject general: DummyGeneral{}

	property list<QtObject> layers: [
		DummyLayer{},
		DummyLayer{},
		DummyLayer{},
		DummyLayer{},
		DummyLayer{},
		DummyLayer{},
		DummyLayer{},
		DummyLayer{}
	]

}
