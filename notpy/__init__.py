#!/usr/bin/env python
'''
provides NotClient, the subclassed evernote client
'''
import re
import logging

# evernote imports
from evernote.api.client import EvernoteClient
from evernote.edam.notestore.ttypes import NoteFilter, NotesMetadataResultSpec
import evernote.edam.type.ttypes as Types


class NoteSaveError(Exception):
    def __init__(self, original_exc, note_contents=''):
        message = "Exception message: {0}\nUnsaved note contents: {1}".format(original_exc, note_contents)
        super(NoteSaveError, self).__init__(message)


class NotClient(EvernoteClient):
    def __init__(self, *args, **kwargs):
        '''
        subclass evernote client and get a note store obj
        '''
        super(NotClient, self).__init__(*args, **kwargs)
        self.note_store = self.get_note_store()
        self.logger = logging.getLogger(self.__class__.__name__)

    def get_content(self, note_guid):
        '''
        get the actual contents of a note based on guid
        '''
        note = self.note_store.getNote(note_guid, True, False, False, False)
        # Strip tags
        content = re.sub('<br/>', '\n', note.content)
        content = re.sub('<.*?>', '', content)
        self.logger.debug("Got text content from note guid {0}: {1}".format(note_guid, content))
        return content

    def search(self, title):
        '''
        bumble through evernote's api to find a note
        '''
        try:
            # evernote's api is ridiculous
            filter = NoteFilter(words="intitle:'{0}'".format(title))
            finder = self.note_store.findNotesMetadata(filter, 0, 1, NotesMetadataResultSpec())
            self.note_guid = finder.notes[0].guid
            return self.note_guid
        except:
            return False

    def check_tags(self, body):
        for line in body.split('\n'):
            if line.startswith('tags:'):
                return line.split('tags:')[1].replace(' ','').split(',')

    def save(self, body, title):
        '''
        if the note exists, update it
        else, create it
        '''
        try:
            if self.search(title):
                note = self.note_store.getNote(self.note_guid, True, False, False, False)
                save_it = self.note_store.updateNote
            else:
                note = Types.Note()
                save_it = self.note_store.createNote

            # look for and save tags:
            note.tagNames = self.check_tags(body)

            # evernotes special markup:
            note.title = title
            note.content = '<?xml version="1.0" encoding="UTF-8"?>'
            note.content += '<!DOCTYPE en-note SYSTEM "http://xml.evernote.com/pub/enml2.dtd">'
            note.content += '<en-note>{0}</en-note>'.format(body)
            note.content = re.sub('\n', '<br/>', note.content)

            # save new note or update existing
            save_it(note)
        except Exception as e:
            raise NoteSaveError(e, body)
