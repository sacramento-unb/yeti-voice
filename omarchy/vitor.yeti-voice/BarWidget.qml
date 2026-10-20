import QtQuick
import qs.Ui

BarWidget {
  id: root
  moduleName: "vitor.yeti-voice"

  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  WidgetButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    text: "󰍬"
    tooltipText: "Yeti Voice — abrir controles"

    onPressed: function(buttonCode) {
      if (buttonCode === Qt.LeftButton && root.bar)
        root.bar.run("omarchy-launch-or-focus-tui --app-id=org.omarchy.yeti-voice yeti-voice")
    }
  }
}
