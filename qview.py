import sys
import glob
import qpageview

from PyQt5.QtWidgets import QApplication
a = QApplication([])

v = qpageview.View()
#v.loadImages(glob.glob("EPSON058.JPG"))
v.loadPdf("EPSON001.PDF")

v.show()

sys.exit(a.exec_())