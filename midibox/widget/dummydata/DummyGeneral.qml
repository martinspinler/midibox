import QtQuick 2.3

QtObject {
	property bool enabled: true

	property list<QtObject> pedals: [
		DummyGeneralPedal{},
		DummyGeneralPedal{},
		DummyGeneralPedal{},
		DummyGeneralPedal{},
		DummyGeneralPedal{},
		DummyGeneralPedal{},
		DummyGeneralPedal{},
		DummyGeneralPedal{}
	]
}
