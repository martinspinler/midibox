import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

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
