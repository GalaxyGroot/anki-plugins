# Main interface between Anki and this addon components

# Holds references so GC does kill them
controllerInstance = None

import const
from notemenu import NoteMenuHandler
import browser
import anki
import json

# import urllib.request
from urllib2 import urlopen

def run(providers = {}):
    global controllerInstance
    
    from aqt import mw
    from notemenu import ankiSetup

    print('Setting anki-web-browser controller')
    
    ankiSetup()
    NoteMenuHandler.setOptions(providers)
    controllerInstance = Controller(mw)
    controllerInstance.setupBindings()

    if True:    # FIXME
        from aqt.utils import showInfo, tooltip, showWarning
        tooltip('Anki-Web-Browser loaded. Version {}'.format('1.0.5'))
        controllerInstance.openInBrowser('https://google.com/search?q={}', 'api-test', None)


class Controller:
    """
        The mediator/adapter between Anki with its components and this addon specific API
    """

    _browser = None
    _editorReference = None
    _currentNote = None
    _ankiMw = None    

    def __init__(self, ankiMw):
        NoteMenuHandler.setController(self)
        self._browser = browser.AwBrowser(ankiMw)
        self._browser.setSelectionListener(self)
        self._ankiMw = ankiMw

    def setupBindings(self):
        # anki.hooks.addHook('afterStateChange', self.setState)
        # anki.hooks.addHook('EditorWebView.contextMenuEvent', NoteMenuHandler.onEditorMenu)
        anki.hooks.addHook('EditorWebView.contextMenuEvent', self.onEditorHandle)
        anki.hooks.addHook('AnkiWebView.contextMenuEvent', self.onReviewerHandle)

        # editor.Editor.setNote = wrap(editor.Editor.setNote, mySetup, 'after')

    def isEditing(self):
        'Checks anki current state. Whether is editing or not'

        return True if (self._ankiMw and self._ankiMw.state == 'resetRequired' and self._editorReference) else False

    def onEditorHandle(self, webView, menu):
        """
            Wrapper to the real context menu handler on the editor;
            Also holds a reference to the editor
        """

        self._editorReference = webView.editor
        NoteMenuHandler.onEditorMenu(webView, menu)        

    def onReviewerHandle(self, webView, menu):
        """
            Wrapper to the real context menu handler on the reviewer;
            Cleans up editor reference
        """

        self._editorReference = None
        note = self._ankiMw.reviewer.card.note()
        NoteMenuHandler.onReviewerMenu(webView, menu, note)

    def openInBrowser(self, website, query, note, isEditMode = False):
        """
            Setup enviroment for web browser and invoke it
        """

        self._currentNote = note
        print('OpenInBrowser: {} ({})'.format(note, self.isEditing()))
        
        if self.isEditing():
            fieldList = note.model()['flds']
            fieldsNames = {ind: val for ind, val in enumerate(map(lambda i: i['name'], fieldList))}
            self._browser.setFields(fieldsNames)
        else:
            self._browser.setFields(None)   # clear fields

        self._browser.open(website, query)

    def handleSelection(self, fieldIndex, value, isUrl = False):
        """
            Callback from the web browser. 
            Invoked when there is a selection coming from the browser. It need to be delivered to a given field
        """

        print('Received something from Web Browser: [{}] {}'.format(isUrl, value))

        self._editorReference.currentField = fieldIndex

        if isUrl:
            self.handleUrlSelection(fieldIndex, value)
        else:
            self.handleTextSelection(fieldIndex, value)        

    def handleUrlSelection(self, fieldIndex, value):
        # imgReference = self._editorReference.urlToLink(value)

        response = urllib2.urlopen(url, timeout=45)
        if response.getcode() != 200:
            showWarning(_("Unexpected response code: %s") % response.status_code)
            return
        filecontents = response.read()
        ct = dict(response.info())
        path = url #urllib.parse.unquote(url)

        print(ct)

        # imgReference = self._ankiMw.col.media.writeData(path, filecontents, typeHint=ct)

        if not imgReference:
            from aqt.utils import tooltip
            tooltip('It was not possible to save the selected reference. Check whether the link is of an accepted type in Anki (audio, image)')
            return


        imgReference = ('<img src="%s" />' % imgReference)
        print(value, imgReference)

        self._editorReference.web.eval("setFormat('inserthtml', %s);" % json.dumps(imgReference))
        # self._editorReference.setNote(self._currentNote, focusTo=fieldIndex)


    def handleTextSelection(self, fieldIndex, value):
        newValue = self._currentNote.fields[fieldIndex] + '\n ' + value
        self._currentNote.fields[fieldIndex] = newValue
        self._editorReference.setNote(self._currentNote)