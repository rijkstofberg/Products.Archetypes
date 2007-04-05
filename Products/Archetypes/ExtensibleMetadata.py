import string
from logging import INFO, DEBUG
from zope.component import getUtility
from zope.component import queryUtility

from Products.Archetypes import PloneMessageFactory as _
from Products.Archetypes.Field import *
from Products.Archetypes.Widget import *
from Products.Archetypes.Schema import Schema
from Products.Archetypes.Schema import MetadataSchema
from Products.Archetypes.interfaces.metadata import IExtensibleMetadata
from Products.Archetypes.utils import DisplayList, shasattr
from Products.Archetypes.debug import log
from Products.Archetypes import config
import Persistence
from Acquisition import aq_base
from AccessControl import ClassSecurityInfo
from AccessControl import Unauthorized
from DateTime.DateTime import DateTime
from Globals import InitializeClass, DTMLFile
from Products.CMFCore import permissions
from Products.CMFDefault.utils import _dtmldir
from ComputedAttribute import ComputedAttribute
from Products.CMFCore.interfaces import IDiscussionTool
from Products.CMFCore.interfaces import IMembershipTool

_marker=[]

FLOOR_DATE = DateTime(1000, 0) # always effective
CEILING_DATE = DateTime(2500, 0) # never expires

# We import this conditionally, in order not to introduce a hard dependency
try:
    from plone.i18n.locales.interfaces import IMetadataLanguageAvailability
    HAS_PLONE_I18N = True
except ImportError:
    HAS_PLONE_I18N = False

## MIXIN
class ExtensibleMetadata(Persistence.Persistent):
    """a replacement for CMFDefault.DublinCore.DefaultDublinCoreImpl
    """
    # XXX This is not completely true. We need to review this later
    # and make sure it is true.
    # Just so you know, the problem here is that Title
    # is on BaseObject.schema, so it does implement IExtensibleMetadata
    # as long as both are used together.
    __implements__ = IExtensibleMetadata

    security = ClassSecurityInfo()

    schema = type = MetadataSchema(
        (
        StringField(
            'allowDiscussion',
            accessor="isDiscussable",
            mutator="allowDiscussion",
            edit_accessor="editIsDiscussable",
            default=None,
            enforceVocabulary=1,
            vocabulary=DisplayList((
                ('None', _(u'label_discussion_default', default=u'Default')),
                ('1', _(u'label_discussion_enabled', default=u'Enabled')),
                ('0', _(u'label_discussion_disabled', default=u'Disabled')),
                )),
            widget=SelectionWidget(
                label=_(u'label_allow_discussion',
                        default=u'Allow comments on this item')
                ),
        ),
        LinesField(
            'subject',
            multiValued=1,
            accessor="Subject",
            searchable=True,
            widget=KeywordWidget(
                label=_(u'label_keywords', default=u'Categories'),
                description=_(u'help_categories',
                              default=u'Also known as keywords, tags or labels, '
                                       'these help you categorize your content.'),
                ),
        ),
        TextField(
            'description',
            default='',
            searchable=1,
            accessor="Description",
            default_content_type = 'text/plain',
            allowable_content_types = ('text/plain',),
            widget=TextAreaWidget(
                label=_(u'label_description', default=u'Description'),
                description=_(u'help_description',
                              default=u'A short summary of the content.'),
                ),
        ),
        # Location, also known as Coverage in the DC metadata standard, but we
        # keep the term Location here for historical reasons.
        StringField(
            'location',
            searchable=True,
            widget = StringWidget(
                label = _(u'label_location', default=u'Location'),
                description=_(u'help_description',
                              default=u'The geographical location associated with the item, if applicable.'),
                ),
        ),
        LinesField(
            'contributors',
            accessor="Contributors",
            widget=LinesWidget(
                label=_(u'label_contributors', u'Contributors'),
                description=_(u'help_contributors',
                              default=u"The names of people that have contributed "
                                       "to this item. Each contributor should "
                                       "be on a separate line."),
                ),
        ),
        LinesField(
            'creators',
            accessor="Creators",
            widget=LinesWidget(
                label=_(u'label_creators', u'Creators'),
                description=_(u'help_creators',
                              default=u"Persons responsible for creating the content of "
                                       "this item. Please enter a list of user names, one "
                                       "per line. The principal creator should come first."),
                rows = 3
                ),
        ),
        DateTimeField(
            'effectiveDate',
            mutator='setEffectiveDate',
            languageIndependent = True,
            widget=CalendarWidget(
                label=_(u'label_effective_date', u'Publication Date'),
                description=_(u'help_effective_date',
                              default=u"If this date is in the future, the content will "
                                       "not show up in listings and searches until this date."),
                ),
        ),
        DateTimeField(
            'expirationDate',
            mutator='setExpirationDate',
            languageIndependent = True,
            widget=CalendarWidget(
                label=_(u'label_expiration_date', u'Expiration Date'),
                description=_(u'help_expiration_date',
                              default=u"When this date is reached, the content will no"
                                       "longer be visible in listings and searches."),
                ),
        ),
        StringField(
            'language',
            accessor="Language",
            default = config.LANGUAGE_DEFAULT,
            vocabulary='languages',
            widget=LanguageWidget(
                label=_(u'label_language', default=u'Language'),
                ),
        ),
        TextField(
            'rights',
            accessor="Rights",
            widget=TextAreaWidget(
                label=_(u'label_copyrights', default=u'Rights'),
                description=_(u'help_copyrights',
                              default=u'Copyright statement or other rights information on this item.'),
                )),
        )) + Schema((
        # XXX change this to MetadataSchema in AT 1.4
        # Currently we want to stay backward compatible without migration
        # between beta versions so creation and modification date are using the
        # standard schema which leads to AttributeStorage
        DateTimeField(
            'creation_date',
            accessor='created',
            mutator='setCreationDate',
            default_method=DateTime,
            languageIndependent=True,
            isMetadata=True,
            schemata='metadata',
            generateMode='mVc',
            widget=CalendarWidget(
                label=_(u'label_creation_date', default=u'Creation Date'),
                description=_(u'help_creation_date',
                              default=u'Date this object was created'),
                visible={'edit':'invisible', 'view':'invisible'}),
        ),
        DateTimeField(
            'modification_date',
            accessor='modified',
            mutator = 'setModificationDate',
            default_method=DateTime,
            languageIndependent=True,
            isMetadata=True,
            schemata='metadata',
            generateMode='mVc',
            widget=CalendarWidget(
                label=_(u'label_modification_date',
                        default=u'Modification Date'),
                description=_(u'help_modification_date',
                              default=u'Date this content was modified last'),
                visible={'edit':'invisible', 'view':'invisible'}),
        ),
        ))

    def __init__(self):
        pass

    security.declarePrivate('defaultLanguage')
    def defaultLanguage(self):
        """Retrieve the default language"""
        # This method is kept around for backward compatibility only
        log('defaultLanguage is deprecated and will be removed in AT 1.6',
            level=INFO)
        return config.LANGUAGE_DEFAULT

    security.declareProtected(permissions.View, 'isDiscussable')
    def isDiscussable(self, encoding=None):
        dtool = getUtility(IDiscussionTool)
        return dtool.isDiscussionAllowedFor(self)

    security.declareProtected(permissions.View, 'editIsDiscussable')
    def editIsDiscussable(self, encoding=None):
        # XXX this method highly depends on the current implementation
        # it's a quick hacky fix
        result = getattr(aq_base(self), 'allow_discussion', None)
        if result is not None:
            try:
                # deal with booleans
                result = int(result)
            except (TypeError, ValueError):
                pass
        return str(result)

    security.declareProtected(permissions.ModifyPortalContent,
                              'allowDiscussion')
    def allowDiscussion(self, allowDiscussion=None, **kw):
        if allowDiscussion is not None:
            try:
                allowDiscussion = int(allowDiscussion)
            except (TypeError, ValueError):
                allowDiscussion = allowDiscussion.lower().strip()
                d = {'on' : 1, 'off': 0, 'none':None, '':None, 'None':None}
                allowDiscussion = d.get(allowDiscussion, None)
        dtool = getUtility(IDiscussionTool)
        try:
            dtool.overrideDiscussionFor(self, allowDiscussion)
        except (KeyError, AttributeError), err:
            if allowDiscussion is None:
                # work around a bug in CMFDefault.DiscussionTool. It's using
                # an unsafe hasattr() instead of a more secure getattr() on an
                # unwrapped object
                # XXX CMF 2.1 fixes this bug, check if we can remove this code
                msg = "Unable to set discussion on %s to None. Already " \
                      "deleted allow_discussion attribute? Message: %s" % (
                       self.getPhysicalPath(), str(err))
                log(msg, level=DEBUG)
            else:
                raise
        except ("Unauthorized", Unauthorized):
            # Catch Unauthorized exception that could be raised by the
            # discussion tool when the authenticated users hasn't
            # ModifyPortalContent permissions. IMO this behavior is safe because
            # this method is protected, too.
            # Explanation:
            # A user might have CreatePortalContent but not ModifyPortalContent
            # so allowDiscussion could raise a Unauthorized error although it's
            # called from trusted code. That is VERY bad inside setDefault()!
            #
            # XXX: Should we have our own implementation of
            #      overrideDiscussionFor?
            log('Catched Unauthorized on discussiontool.' \
                'overrideDiscussionFor(%s)' % self.absolute_url(1),
                level=DEBUG)

    # Vocabulary methods ######################################################

    security.declareProtected(permissions.View, 'languages')
    def languages(self):
        """Vocabulary method for the language field
        """
        util = None
        # Try the utility first
        if HAS_PLONE_I18N:
            util = queryUtility(IMetadataLanguageAvailability)
        # Fall back to acquiring availableLanguages
        if util is None:
            languages = getattr(self, 'availableLanguages', None)
            if callable(languages):
                languages = languages()
            # Fall back to static definition
            if languages is None:
                return DisplayList(
                    (('en','English'), ('fr','French'), ('es','Spanish'),
                     ('pt','Portuguese'), ('ru','Russian')))
        else:
            languages = util.getLanguageListing()
            languages.sort(lambda x,y:cmp(x[1], y[1]))
            # Put language neutral at the top.
            languages.insert(0,(u'',_(u'Language neutral (site default)')))
        return DisplayList(languages)

    #  DublinCore interface query methods #####################################

    security.declareProtected(permissions.View, 'CreationDate')
    def CreationDate(self):
        """ Dublin Core element - date resource created.
        """
        creation = self.getField('creation_date').get(self)
        # return unknown if never set properly
        return creation is None and 'Unknown' or creation.ISO()

    security.declareProtected( permissions.View, 'EffectiveDate')
    def EffectiveDate(self):
        """ Dublin Core element - date resource becomes effective.
        """
        effective = self.getField('effectiveDate').get(self)
        return effective is None and 'None' or effective.ISO()

    def _effective_date(self):
        """Computed attribute accessor
        """
        return self.getField('effectiveDate').get(self)

    security.declareProtected(permissions.View, 'effective_date')
    effective_date = ComputedAttribute(_effective_date, 1)


    security.declareProtected( permissions.View, 'ExpirationDate')
    def ExpirationDate(self):
        """Dublin Core element - date resource expires.
        """
        expires = self.getField('expirationDate').get(self)
        return expires is None and 'None' or expires.ISO()

    def _expiration_date(self):
        """Computed attribute accessor
        """
        return self.getField('expirationDate').get(self)

    security.declareProtected(permissions.View, 'expiration_date')
    expiration_date = ComputedAttribute(_expiration_date, 1)

    security.declareProtected(permissions.View, 'Date')
    def Date(self):
        """
        Dublin Core element - default date
        """
        # Return effective_date if specifically set, modification date
        # otherwise
        effective = self.getField('effectiveDate').get(self)
        if effective is None:
            effective = self.modified()
        return effective is None and DateTime() or effective.ISO()

    security.declareProtected(permissions.View, 'Format')
    def Format(self):
        """cmf/backward compat
        Dublin Core element - resource format
        """
        # FIXME: get content type from marshaller
        return self.getContentType()

    security.declareProtected(permissions.ModifyPortalContent,
                              'setFormat')
    def setFormat(self, value):
        """cmf/backward compat: ignore setFormat"""
        self.setContentType(value)

    def Identifer(self):
        """ dublin core getId method"""
        return self.getId()

    #  DublinCore utility methods #############################################

    security.declareProtected(permissions.View, 'contentEffective')
    def contentEffective(self, date):
        """Is the date within the resource's effective range?
        """
        effective = self.getField('effectiveDate').get(self)
        expires = self.getField('expirationDate').get(self)
        pastEffective = ( effective is None or effective <= date )
        beforeExpiration = ( expires is None or expires >= date )
        return pastEffective and beforeExpiration

    security.declareProtected(permissions.View, 'contentExpired')
    def contentExpired(self, date=None):
        """ Is the date after resource's expiration """
        if not date:
            date = DateTime()
        expires = self.getField('expirationDate').get(self)
        if not expires:
            expires = CEILING_DATE
        return expires <= date

    #  CatalogableDublinCore methods ##########################################

    security.declareProtected(permissions.View, 'created')
    def created(self):
        """Dublin Core element - date resource created,
        returned as DateTime.
        """
        # allow for non-existent creation_date, existed always
        created = self.getField('creation_date').get(self)
        return created is None and FLOOR_DATE or created

    security.declareProtected(permissions.View, 'modified')
    def modified(self):
        """Dublin Core element - date resource last modified,
        returned as DateTime.
        """
        modified = self.getField('modification_date').get(self)
        # TODO may return None
        return modified

    security.declareProtected(permissions.View, 'effective')
    def effective(self):
        """Dublin Core element - date resource becomes effective,
        returned as DateTime.
        """
        effective = self.getField('effectiveDate').get(self)
        return effective is None and FLOOR_DATE or effective

    security.declareProtected(permissions.View, 'expires')
    def expires(self):
        """Dublin Core element - date resource expires,
        returned as DateTime.
        """
        expires = self.getField('expirationDate').get(self)
        return expires is None and CEILING_DATE or expires

    ## code below come from CMFDefault.DublinCore.DefaultDublinCoreImpl #######

    ###########################################################################
    #
    # Copyright (c) 2001 Zope Corporation and Contributors. All Rights Reserved
    #
    # This software is subject to the provisions of the Zope Public License,
    # Version 2.0 (ZPL).  A copy of the ZPL should accompany this distribution.
    # THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
    # WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
    # WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
    # FOR A PARTICULAR PURPOSE
    #
    ###########################################################################

    #
    #  Set-modification-date-related methods.
    #  In DefaultDublinCoreImpl for lack of a better place.
    #

    security.declareProtected(permissions.ModifyPortalContent,
                              'notifyModified')
    def notifyModified(self):
        """
        Take appropriate action after the resource has been modified.
        For now, change the modification_date.
        """
        self.setModificationDate(DateTime())
        if shasattr(self, 'http__refreshEtag'):
            self.http__refreshEtag()

    security.declareProtected(permissions.ManagePortal,
                              'setModificationDate')
    def setModificationDate(self, modification_date=None):
        """Set the date when the resource was last modified.
        When called without an argument, sets the date to now.
        """
        if modification_date is None:
            modified = DateTime()
        else:
            modified = self._datify(modification_date)
        self.getField('modification_date').set(self, modified)

    security.declareProtected(permissions.ManagePortal,
                              'setCreationDate')
    def setCreationDate(self, creation_date=None):
        """Set the date when the resource was created.
        When called without an argument, sets the date to now.
        """
        if creation_date is None:
            created = DateTime()
        else:
            created = self._datify(creation_date)
        self.getField('creation_date').set(self, created)

    security.declarePrivate( '_datify' )
    def _datify(self, date):
        """Try to convert something into a DateTime instance or None
        """
        # stupid web
        if date == 'None':
            date = None
        if not isinstance(date, DateTime):
            if date is not None:
                date = DateTime(date)
        return date

    #
    #  DublinCore interface query methods
    #
    security.declareProtected(permissions.View, 'Publisher')
    def Publisher(self):
        """Dublin Core element - resource publisher
        """
        # XXX: fixme using 'portal_metadata'
        return 'No publisher'

    security.declareProtected(permissions.View, 'ModificationDate')
    def ModificationDate(self):
        """ Dublin Core element - date resource last modified.
        """
        modified = self.modified()
        return modified is None and DateTime() or modified.ISO()

    security.declareProtected(permissions.View, 'Type')
    def Type(self):
        """Dublin Core element - Object type"""
        if hasattr(aq_base(self), 'getTypeInfo'):
            ti = self.getTypeInfo()
            if ti is not None:
                return ti.Title()
        return self.meta_type

    security.declareProtected(permissions.View, 'Identifier')
    def Identifier(self):
        """Dublin Core element - Object ID"""
        # XXX: fixme using 'portal_metadata' (we need to prepend the
        #      right prefix to self.getPhysicalPath().
        return self.absolute_url()

    security.declareProtected(permissions.View, 'listContributors')
    def listContributors(self):
        """Dublin Core element - Contributors"""
        return self.Contributors()

    security.declareProtected(permissions.ModifyPortalContent,
                              'addCreator')
    def addCreator(self, creator=None):
        """ Add creator to Dublin Core creators.
        """
        if creator is None:
            mtool = getUtility(IMembershipTool)
            creator = mtool.getAuthenticatedMember().getId()

        # call self.listCreators() to make sure self.creators exists
        curr_creators = self.listCreators()
        if creator and not creator in curr_creators:
            self.setCreators(curr_creators + (creator, ))

    security.declareProtected(permissions.View, 'listCreators')
    def listCreators(self):
        """ List Dublin Core Creator elements - resource authors.
        """
        creators = self.Schema()['creators']
        if not creators.get(self):
            # for content created with CMF versions before 1.5
            owner_id = self.getOwnerTuple()[1]
            if owner_id:
                creators.set(self, (owner_id,))
            else:
                creators.set(self, ())

        return creators.get(self)

    security.declareProtected(permissions.View, 'Creator')
    def Creator(self):
        """ Dublin Core Creator element - resource author.
        """
        creators = self.listCreators()
        return creators and creators[0] or ''

    #
    #  DublinCore utility methods
    #

    # Deliberately *not* protected by a security declaration
    # See https://dev.plone.org/archetypes/ticket/712
    def content_type(self):
        """ WebDAV needs this to do the Right Thing (TM).
        """
        return self.Format()
    #
    #  CatalogableDublinCore methods
    #

    security.declareProtected(permissions.View, 'getMetadataHeaders')
    def getMetadataHeaders(self):
        """ Return RFC-822-style headers.
        """
        hdrlist = []
        hdrlist.append( ( 'Title', self.Title() ) )
        hdrlist.append( ( 'Subject', string.join( self.Subject(), ', ' ) ) )
        hdrlist.append( ( 'Publisher', self.Publisher() ) )
        hdrlist.append( ( 'Description', self.Description() ) )
        hdrlist.append( ( 'Contributors', string.join(
            self.Contributors(), '; ' ) ) )
        hdrlist.append( ( 'Creators', string.join(
            self.Creators(), '; ' ) ) )
        hdrlist.append( ( 'Effective_date', self.EffectiveDate() ) )
        hdrlist.append( ( 'Expiration_date', self.ExpirationDate() ) )
        hdrlist.append( ( 'Type', self.Type() ) )
        hdrlist.append( ( 'Format', self.Format() ) )
        hdrlist.append( ( 'Language', self.Language() ) )
        hdrlist.append( ( 'Rights', self.Rights() ) )
        return hdrlist

    #
    #  Management tab methods
    #

    security.declarePrivate( '_editMetadata' )
    def _editMetadata(self
                      , title=_marker
                      , subject=_marker
                      , description=_marker
                      , contributors=_marker
                      , effective_date=_marker
                      , expiration_date=_marker
                      , format=_marker
                      , language=_marker
                      , rights=_marker
                      ):
        """ Update the editable metadata for this resource.
        """
        if title is not _marker:
            self.setTitle( title )
        if subject is not _marker:
            self.setSubject( subject )
        if description is not _marker:
            self.setDescription( description )
        if contributors is not _marker:
            self.setContributors( contributors )
        if effective_date is not _marker:
            self.setEffectiveDate( effective_date )
        if expiration_date is not _marker:
            self.setExpirationDate( expiration_date )
        if format is not _marker:
            self.setFormat( format )
        if language is not _marker:
            self.setLanguage( language )
        if rights is not _marker:
            self.setRights( rights )

    security.declareProtected(permissions.ModifyPortalContent,
                              'manage_metadata' )
    manage_metadata = DTMLFile('zmi_metadata', _dtmldir)

    security.declareProtected(permissions.ModifyPortalContent,
                               'manage_editMetadata')
    def manage_editMetadata( self
                           , title
                           , subject
                           , description
                           , contributors
                           , effective_date
                           , expiration_date
                           , format
                           , language
                           , rights
                           , REQUEST
                           ):
        """ Update metadata from the ZMI.
        """
        self._editMetadata( title, subject, description, contributors
                          , effective_date, expiration_date
                          , format, language, rights
                          )
        REQUEST[ 'RESPONSE' ].redirect( self.absolute_url()
                                + '/manage_metadata'
                                + '?manage_tabs_message=Metadata+updated.' )

    security.declareProtected(permissions.ModifyPortalContent,
                              'editMetadata')
    def editMetadata(self
                     , title=''
                     , subject=()
                     , description=''
                     , contributors=()
                     , effective_date=None
                     , expiration_date=None
                     , format='text/html'
                     , language='en-US'
                     , rights=''
                     ):
        """
        used to be:  editMetadata = WorkflowAction(_editMetadata)
        Need to add check for webDAV locked resource for TTW methods.
        """
        self.failIfLocked()
        self._editMetadata(title=title
                           , subject=subject
                           , description=description
                           , contributors=contributors
                           , effective_date=effective_date
                           , expiration_date=expiration_date
                           , format=format
                           , language=language
                           , rights=rights
                           )
        self.reindexObject()

InitializeClass(ExtensibleMetadata)

ExtensibleMetadataSchema = ExtensibleMetadata.schema

__all__ = ('ExtensibleMetadata', 'ExtensibleMetadataSchema', )
