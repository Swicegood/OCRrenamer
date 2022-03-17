
from http.client import OK
from logging import warning
from tkinter.messagebox import NO, YES
import qpageview
import os
import glob
import platform
import time
from PIL import Image
from datetime import datetime
from PyQt5.QtCore import Qt, QProcess
from PyQt5.QtWidgets import (QApplication, QDialog, QPushButton, QLabel, QLineEdit, 
        QGridLayout, QFileDialog, QListView, QTreeView, QFileSystemModel,
        QAbstractItemView, QListWidget, QTextEdit, QCheckBox, QFrame, QMessageBox,
        QButtonGroup)

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
        self.sug1Check = QCheckBox()
        self.sug2Check = QCheckBox()
        self.sug3Check = QCheckBox()
        self.buttongroup = QButtonGroup(self)
        self.buttongroup.addButton(self.sug1Check)
        self.buttongroup.addButton(self.sug2Check)
        self.buttongroup.addButton(self.sug3Check)
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
        layout.addWidget(self.sug1Check, 4, 7, 1, 1)
        layout.addWidget(self.suggested2, 5, 3, 1, 4)
        layout.addWidget(self.sug2Check, 5, 7, 1, 1)
        layout.addWidget(self.suggested3, 6, 3, 1, 4)
        layout.addWidget(self.sug3Check, 6, 7, 1, 1)
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
        self.buttongroup.buttonClicked.connect(self.updatefromsuggested)
        # self.sug1Check.stateChanged.connect(self.updatefromsuggested)
        # self.sug2Check.stateChanged.connect(self.updatefromsuggested)
        # self.sug3Check.stateChanged.connect(self.updatefromsuggested)
        self.dateCheckBox.stateChanged.connect(self.state_changed)
        self.buttongroup.setExclusive(True)
        # QProcess object for external app
        self.ocrproc = QProcess(self)
        # QProcess emits `readyRead` when there is data to be read
        self.ocrproc.readyRead.connect(self.dataReady)     
    
        self.ocrproc.started.connect(lambda: self.makeButton.setEnabled(False))
        self.ocrproc.finished.connect(self.onOcrFinished)


    def dataReady(self):
        cursor = self.wordBox.textCursor()
        cursor.movePosition(cursor.End)
        cursor.insertText(str(self.ocrproc.readAll()))
        self.wordBox.ensureCursorVisible()

    def fillInfoBox(self):
        path = selected_files[docindex]
        mtime = os.path.getmtime(path)
        ctime = creation_date(path)
        mtime_pretty = datetime.utcfromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
        ctime_pretty = datetime.utcfromtimestamp(ctime).strftime('%Y-%m-%d %H:%M:%S')
        infotxt = '\n\nFile Information:\n\n\nModified time: '+mtime_pretty+'\n\n\nCreation time: '+ctime_pretty+'\n\n'
        self.infoLabel.setText(infotxt)
        
    def onMakeSearchableClicked(self):
        global selected_files
        global docindex
        viewable_file = selected_files[docindex] 
        if len(viewable_file):

            ext = os.path.splitext(viewable_file)[1]

            if ext == '.pdf' or ext == '.PDF':
                self.ocrproc.start('pdf2pdfocr/pdf2pdfocr.py', ['-t', '-i', viewable_file])
  
            elif ext in ['.JPG','.JPEG','.PNG','.jpg','.jpeg','.png','.svg','.SVG']:
                self.convert_to_pdf()
                self.onMakeSearchableClicked()     
           
    def convert_to_pdf(self):
        viewable_file = selected_files[docindex]        
        mtime_seconds = os.path.getmtime(viewable_file)
        time_seconds = time.time()
        basename = os.path.basename(viewable_file)
        dir = os.path.dirname(viewable_file)
        filebase = basename.split('.')[0]
        image_1 = Image.open(viewable_file)
        im_1 = image_1.convert('RGB')
        newpath = os.path.join(dir ,filebase) + '.pdf'
        im_1.save(newpath)
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Warning)
        msgBox.setText('Do you want to DELETE the original?')
        msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
  #      msgBox.buttonClicked.connect(self.msgbtn)
        retval = msgBox.exec()
        if retval == 0x00004000:
            os.utime(newpath, (time_seconds, mtime_seconds))
            os.remove(viewable_file)
            selected_files[docindex] = newpath
    
    def msgbtn(self, button):
        pass

    def onOcrFinished(self):
        self.makeButton.setEnabled(True)
        viewable_file = selected_files[docindex]        
        mtime_seconds = os.path.getmtime(viewable_file)
        time_seconds = time.time()
        filebase = viewable_file.split('.')[0]
        if filebase.split('-')[-1] != 'OCR':
            selected_files[docindex] = filebase+'-OCR.pdf'
        if self.removeOrginalCheckBox.isChecked() and self.ocrproc.exitCode() == 0:
            os.remove(viewable_file)                    
        viewable_file = selected_files[docindex]
        os.utime(viewable_file, (time_seconds, mtime_seconds))
        self.removeOrginalCheckBox.setChecked(False)
        self.load_viewable_file(viewable_file)           
            
    def load_wordbox(self):
        page = self.v.currentPage()
        full_text = page.text(page.rect())
        self.wordBox.setPlainText(full_text)
        return full_text

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

        full_text = self.load_wordbox()
        self.fillInfoBox()
        self.saveas.setText(os.path.basename(viewable_file)) 
        self.suggested1.setText(head_in_snake_case(full_text, 14))
        base = os.path.basename(viewable_file).split('.')[0:-1]
        base = '.'.join(base)
        self.suggested3.setText(base)
        self.v.show()

    def state_changed(self, int):
        if self.dateCheckBox.isChecked():
            self.onAddDateToFnameChecked()
        else:
            self.onAddDateToFnameUnchecked()

    def onAddDateToFnameChecked(self):
        viewable_file = selected_files[docindex]        
        mtime_seconds = os.path.getmtime(viewable_file)
        mtime_pretty = datetime.utcfromtimestamp(mtime_seconds).strftime('%Y-%m-%dT%H%M%S')
        saveasfname = self.saveas.text()
        ext = saveasfname.split('.')[-1]
        base = saveasfname.split('.')[0:-1]
        base = '.'.join(base)
        self.saveas.setText(base +'_'+ mtime_pretty +'.'+ ext)

    def onAddDateToFnameUnchecked(self):
        saveasfname = self.saveas.text()
        ext = saveasfname.split('.')[-1]
        oldbase = saveasfname.split('.')[0:-1]
        oldbase = '.'.join(oldbase)
        newbase = oldbase.split('_')[0:-1]
        newbase = '_'.join(newbase)
        self.saveas.setText(newbase + '.' + ext)
    
    def updatefromsuggested(self):
        date = ''
        newbase = ''
        button = self.buttongroup.checkedButton()
        if button == self.sug1Check:
            newbase = self.suggested1.text()
        if button == self.sug2Check:
            newbase = self.suggested2.text()
        if button == self.sug3Check:
            newbase = self.suggested3.text()        
        saveasfname = self.saveas.text()
        oldbase = saveasfname.split('.')[0:-1]
        oldbase = '.'.join(oldbase)
        if self.dateCheckBox.isChecked():
            date = '_' + oldbase.split('_')[-1]
        ext = saveasfname.split('.')[-1]
        self.saveas.setText(newbase + date + '.' + ext)


    def onBackButton(self):
        global docindex
        global selected_files
        if docindex > 0:
            docindex -= 1
        self.load_viewable_file(selected_files[docindex])

    def onNextButton(self):
        global docindex
        global selected_files
        if docindex < len(selected_files) - 1:
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
        self.selected_folders = []

        button.clicked.connect(self.handleChooseDirectories)
        doneButton.clicked.connect(self.onDoneButtonClicked)

    def onDoneButtonClicked(self):  
        global selected_files
        if not len(self.selected_folders):
            msgBox = QMessageBox()
            msgBox.setText('No Folders Selected!')
            msgBox.exec()
        else:
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

def creation_date(path_to_file):
        """
        Try to get the date that a file was created, falling back to when it was
        last modified if that isn't possible.
        See http://stackoverflow.com/a/39501288/1709587 for explanation.
        """
        if platform.system() == 'Windows':
            return os.path.getctime(path_to_file)
        else:
            stat = os.stat(path_to_file)
            try:
                return stat.st_birthtime
            except AttributeError:
                # We're probably on Linux. No easy way to get creation dates here,
                # so we'll settle for when its content was last modified.
                return stat.st_mtime

def head_in_snake_case(text, numofwords):
    words = text.split(' ')
    head = ""
    i = 0
    j = 0 
    while(j < numofwords and i < len(words)):
        if '\t' not in words[i] and '\n' not in words[i] and words[i] != '':
            if j < numofwords - 1:
                head += words[i]+'_'
            else:
                head += words[i]
            j += 1
        i += 1
    return head

if __name__ == '__main__':

    app = QApplication([])
    main_window = MainWindow()
    main_window.show()
    app.exec_()