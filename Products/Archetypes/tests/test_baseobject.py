# -*- coding: UTF-8 -*-
################################################################################
#
# Copyright (c) 2002-2005, Benjamin Saller <bcsaller@ideasuite.com>, and
#                              the respective authors. All rights reserved.
# For a list of Archetypes contributors see docs/CREDITS.txt.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
# * Neither the name of the author nor the names of its contributors may be used
#   to endorse or promote products derived from this software without specific
#   prior written permission.
#
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
################################################################################
"""
"""

import os, sys
if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))
from Testing import ZopeTestCase

from Products.Archetypes.tests.atsitetestcase import ATSiteTestCase
from Products.Archetypes.tests.utils import mkDummyInContext

from Products.Archetypes import PloneMessageFactory as _
from Products.Archetypes.atapi import *
from Products.Archetypes.config import PKG_NAME

class DummyDiscussionTool:
    def isDiscussionAllowedFor( self, content ):
        return False
    def overrideDiscussionFor(self, content, allowDiscussion):
        pass

MULTIPLEFIELD_LIST = DisplayList(
    (
    ('1', _(u'Option 1 : printemps')),
    ('2', unicode('Option 2 : été', 'utf-8')),
    ('3', u'Option 3 : automne'),
    ('4', _(u'option3', default=u'Option 3 : hiver')),
    ))

schema = BaseSchema + Schema((
    LinesField(
        'MULTIPLEFIELD',
        searchable = 1,
        vocabulary = MULTIPLEFIELD_LIST,
        widget = MultiSelectionWidget(
            i18n_domain = 'plone',
            ),
        ), 
))

class Dummy(BaseContent):
   
    portal_discussion = DummyDiscussionTool()

    def getCharset(self):
         return 'utf-8'
         
class BaseObjectTest(ATSiteTestCase):

    def afterSetUp(self):
        ATSiteTestCase.afterSetUp(self)
        self._dummy = mkDummyInContext(Dummy, oid='dummy', context=self.portal,
                                      schema=schema)
    
    def test_searchableText(self):
        """
        Fix bug [ 951955 ] BaseObject/SearchableText and list of Unicode stuffs
        """
        dummy = self._dummy

        # Set a multiple field
        dummy.setMULTIPLEFIELD(['1','2'])
        searchable = dummy.SearchableText()

        self.failUnless(isinstance(searchable, basestring))
        self.assertEquals(searchable, '1 2 Option 1 : printemps Option 2 : été')

        dummy.setMULTIPLEFIELD(['3','4'])
        searchable = dummy.SearchableText()

        self.assertEquals(searchable, '3 4 Option 3 : automne option3')

    def test_searchableTextUsesIndexMethod(self):
        """See http://dev.plone.org/archetypes/ticket/645

        We want SearchableText to use the ``index_method`` attribute
        of fields to determine which is the accessor it should use
        while gathering values.
        """
        ATSiteTestCase.afterSetUp(self)
        dummy = mkDummyInContext(Dummy, oid='dummy', context=self.portal,
                                 schema=schema.copy())
        
        # This is where we left off in the previous test
        dummy.setMULTIPLEFIELD(['1','2'])
        searchable = dummy.SearchableText()
        self.failUnless(searchable.startswith('1 2 Option 1 : printemps'))

        # Now we set another index_method and expect it to be used:
        dummy.getField('MULTIPLEFIELD').index_method = 'myMethod'
        def myMethod(self):
            return "What do you expect of a Dummy?"
        Dummy.myMethod = myMethod
        searchable = dummy.SearchableText()
        self.failUnless(searchable.startswith("What do you expect of a Dummy"))
        del Dummy.myMethod
        

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(BaseObjectTest))
    return suite

if __name__ == '__main__':
    framework()