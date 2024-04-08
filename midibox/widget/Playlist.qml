import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

ListView {
	id: plid
	Layout.fillWidth: true
	Layout.fillHeight: true
	model: playlistModel

	ScrollBar.vertical: ScrollBar {
		active: true
	}

	delegate: Button {
		width: plid.width
		height: 40
		text: model.text
		onClicked: midibox.loadSong(model)
	}
}
