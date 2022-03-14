
import qpageview
import os
import glob
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QApplication, QDialog, QPushButton, QLabel, QLineEdit, 
        QGridLayout, QFileDialog, QListView, QTreeView, QFileSystemModel,
        QAbstractItemView, QListWidget, QTextEdit, QCheckBox, QFrame)

global selected_files
global docindex
docindex = 0

class MainWindow(QDialog):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)

        select_files = SelectFilesDialog(self)         
        select_files.show()   

        self.resize(640,800)
        self.v = qpageview.View()
        self.wordBox = QTextEdit()
        self.makeButton = QPushButton('Make Searchable')
        self.removeOrginalCheckBox = QCheckBox('Remove Original (destructive)')
        self.infoLabel = QLabel('File Information:\n\nNo information yet')
        self.dateCheckBox = QCheckBox("Add date to filname")
        self.backButton = QPushButton('<Back')
        self.nextButton = QPushButton('Next>')
        self.goButton = QPushButton('Save (destructive)')
        self.suggested1 = QLineEdit()
        self.suggested2 = QLineEdit()
        self.suggested3 = QLineEdit()
        self.saveas = QLineEdit()
        self.saveas.setMinimumWidth(500)
        self.infoLabel.setFrameStyle(QFrame.Panel | QFrame.Raised)
        self.suggestedLabel = QLabel("Suggested Filenames:")
        self.saveasLabel = QLabel("Save As:")
        layout = QGridLayout()
        layout.addWidget(self.v, 0, 0, 9, 3)
        layout.addWidget(self.wordBox, 0, 3, 1, 4, Qt.AlignTop)
        layout.addWidget(self.makeButton, 1, 3, 1, 3, Qt.AlignTop )
        layout.addWidget(self.removeOrginalCheckBox, 1, 6)
        layout.addWidget(self.infoLabel, 2, 3, 1, 4)
        layout.addWidget(self.dateCheckBox, 2, 6, 1, 1)
        layout.addWidget(self.suggestedLabel, 3, 3, 1, 1, Qt.AlignBottom)
        layout.addWidget(self.suggested1, 4, 3, 1, 4)
        layout.addWidget(self.suggested2, 5, 3, 1, 4)
        layout.addWidget(self.suggested3, 6, 3, 1, 4)
        layout.addWidget(self.saveasLabel, 7, 3, 1, 1, Qt.AlignBottom)
        layout.addWidget(self.saveas, 8, 3, 1, 4)
        layout.addWidget(self.backButton, 9, 1)
        layout.addWidget(self.goButton, 9, 2)
        layout.addWidget(self.nextButton, 9, 3)
        layout.setColumnMinimumWidth(0,500)
        self.setLayout(layout)        
        self.makeButton.clicked.connect(self.onMakeSearchableClicked)
        self.backButton.clicked.connect(self.onBackButton)
        self.nextButton.clicked.connect(self.onNextButton)   

    def onMakeSearchableClicked(self):
        global selected_files
        global docindex
        viewable_file = selected_files[docindex]
        if len(viewable_file):

            ext = os.path.splitext(viewable_file)[1]

            if ext == '.pdf' or ext == '.PDF':
                success = os.system('pdf2pdfocr/pdf2pdfocr.py -t -i "'+viewable_file+'"')
                filebase = viewable_file.split('.')[0]
                if filebase.split('-')[-1] != 'OCR':
                    selected_files[docindex] = filebase+'-OCR.pdf'
                if self.removeOrginalCheckBox.isChecked() and success == 0:
                    os.remove(viewable_file)
                viewable_file = selected_files[docindex]
                self.removeOrginalCheckBox.setChecked(False)
            self.load_viewable_file(viewable_file)           
            
    def load_wordbox(self):
        page = self.v.currentPage()
        full_text = page.text(page.rect())
        self.wordBox.setPlainText(full_text)

    def load_viewable_file(self, viewable_file):
        if viewable_file:

            ext = os.path.splitext(viewable_file)[1]

            if ext == '.pdf' or ext == '.PDF':
                self.v.loadPdf(viewable_file)

            elif ext == '.JPG' or ext == '.JPEG' or ext == '.PNG':
                self.v.loadImages(glob.glob(viewable_file))
            
            elif ext == '.jpg' or ext == '.jpeg' or ext == '.png':
                self.v.loadImages(glob.glob(viewable_file))
                
            elif ext == '.svg' or ext == '.SVG':
                self.v.loadSvgs(glob.glob(viewable_file))
            self.setWindowTitle(viewable_file)
        self.v.setViewMode(qpageview.FitBoth)        # shows the full page

        self.load_wordbox() 
        self.v.show()

    def onBackButton(self):
        global docindex
        global selected_files
        if docindex > 0:
            docindex -= 1
        self.load_viewable_file(selected_files[docindex])

    def onNextButton(self):
        global docindex
        global selected_files
        if docindex < len(selected_files):
            docindex += 1
        self.load_viewable_file(selected_files[docindex])


class SelectFilesDialog(QDialog):
    def __init__(self, parent):        
        super(SelectFilesDialog, self).__init__(parent)
        self.setModal(Qt.ApplicationModal)
        self.setWindowTitle('Select Folders')
        label = QLabel('Please Select all Folders you Wish to Scan for Scanned Documents.')
        label.setMargin(50)
        button = QPushButton('. . .')
        doneButton = QPushButton('Done')
        self.listWidget = QListWidget()
        layout = QGridLayout()
        layout.addWidget(label, 0, 0, 1, 2)
        layout.addWidget(self.listWidget, 1, 0, 7, 1)        
        layout.addWidget(button, 4, 1)
        layout.addWidget(doneButton, 9, 0, 2, 1)
        layout.setColumnMinimumWidth(0, 500)
        layout.setRowMinimumHeight(0,200)
        self.setLayout(layout)

        button.clicked.connect(self.handleChooseDirectories)
        doneButton.clicked.connect(self.onDoneButtonClicked)

    def onDoneButtonClicked(self):  
        global selected_files
        selected_files = create_file_list(self.selected_folders)
        self.parent().load_viewable_file(selected_files[0])
        self.close()

    def handleChooseDirectories(self):
        dialog = QFileDialog(self)
        dialog.setWindowTitle('Choose Directories')
        dialog.setOption(QFileDialog.DontUseNativeDialog, True)
        dialog.setFileMode(QFileDialog.DirectoryOnly)
        for view in dialog.findChildren(
            (QListView, QTreeView)):
            if isinstance(view.model(), QFileSystemModel):
                view.setSelectionMode(
                    QAbstractItemView.ExtendedSelection)
        if dialog.exec_() == QDialog.Accepted:
            self.listWidget.clear()
            self.listWidget.addItems(dialog.selectedFiles())
            self.selected_folders = dialog.selectedFiles()
            print(self.selected_folders)
        dialog.deleteLater()

def create_file_list(selected_folders):
    _selected_files = []
    for folder in selected_folders:
        for root, subdirs, files in os.walk(folder):
            for filename in files:
                _selected_files.append(os.path.join(root, filename))
    return _selected_files

if __name__ == '__main__':

    app = QApplication([])
    main_window = MainWindow()
    main_window.show()
    app.exec_()