import QtQuick 2.3

QtObject {
	property bool enable: true
	property bool transpositionExtra: true

	function note2text(i) {
        return "a"
    }

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
