from interface import Interface, Attribute

class IField(Interface):
    """ Interface for fields """

#     required = Attribute('required', 'Require a value to be present when submitting the field')
#     default = Attribute('default', 'Default value for a field')
#     vocabulary = Attribute('vocabulary', 'List of suggested values for the field')
#     enforceVocabulary = Attribute('enforceVocabulary', \
#                                   'Restrict the allowed values to the ones in the vocabulary')
#     multiValued = Attribute('multiValued', 'Allow the field to have multiple values')
#     searchable = Attribute('searchable', 'Make the field searchable')
#     isMetadata = Attribute('isMetadata', 'Is this field a metadata field?')
#     accessor = Attribute('accessor', 'Use this method as the accessor for the field')
#     mutator = Attribute('mutator', 'Use this method as the mutator for the field')
#     mode = Attribute('mode', 'Mode of access to this field')
#     read_permission = Attribute('read_permission', \
#                                 'Permission to use to protect field reading')
#     write_permission = Attribute('write_permission', \
#                                  'Permission to use to protect writing to the field')

#     storage = Attribute('storage', 'Storage class to use for this field')
#     form_info = Attribute('form_info', 'Form Info (?)')
#     generateMode = Attribute('generateMode', 'Generate Mode (?)')
#     force = Attribute('force', 'Force (?)')
#     type = Attribute('type', 'Type of the field')

    def Vocabulary(content_instance=None):
        """
        returns a DisplayList

        uses self.vocabulary as source

        1) Dynamic vocabulary:

            precondition: a content_instance is given.

            has to return a:
                * DisplayList or
                * list of strings or
                * list of 2-tuples with strings:
                    '[("key1","value 1"),("key 2","value 2"),]'

            the output is postprocessed like a static vocabulary.

            vocabulary is a string:
                if a method with the name of the string exists it will be called

            vocabulary is a class implementing IVocabulary:
                the "getDisplayList" method of the class will be called.


        2) Static vocabulary

            * is already a DisplayList
            * is a list of 2-tuples with strings (see above)
            * is a list of strings (in this case a DisplayList with key=value
              will be created)

        """

    def copy():
        """
        Return a copy of field instance, consisting of field name and
        properties dictionary.
        """

    def validate(value, instance, errors={}, **kwargs):
        """
        Validate passed-in value using all field validators.
        Return None if all validations pass; otherwise, return failed
        result returned by validator
        """

    def validate_required(instance, value, errors):
        """Validate the required flag for a field
        
        Overwrite it in your field for special case handling like empty files
        """

    def checkPermission(mode, instance):
        """
        Check whether the security context allows the given permission on
        the given object.

        Arguments:

        permission -- A permission name
        instance -- The object being accessed according to the permission
        """

    def getWidgetName():
        """Return the widget name that is configured for this field as
        a string"""

    def getName():
        """Return the name of this field as a string"""

    def getType():
        """Return the type of this field as a string"""

    def getDefault():
        """Return the default value to be used for initializing this
        field"""

    def getAccessor(instance):
        """Return the accessor method for getting data out of this
        field"""

    def getEditAccessor(instance):
        """Return the accessor method for getting raw data out of this
        field e.g.: for editing
        """

    def getMutator(instance):
        """Return the mutator method used for changing the value
        of this field"""

    def toString():
        """Utility method for converting a Field to a string for the
        purpose of comparing fields.  This comparison is used for
        determining whether a schema has changed in the auto update
        function.  Right now it's pretty crude."""

    def isLanguageIndependent(instance):
        """Get the language independed flag for i18n content (used by LinguaPlon)
        """


class IObjectField(IField):
    """ Interface for fields that support a storage layer """

    def get(instance, **kwargs):
        """ Get the value for this field using the underlying storage """

    def getRaw(instance, **kwargs):
        """Get the raw value for this field using the underlying storage """

    def set(instance, value, **kwargs):
        """ Set the value for this field using the underlying storage """

    def unset(instance, **kwargs):
        """ Unset the value for this field using the underlying storage """

    def getStorage():
        """ Return the storage class used in this field """

    def setStorage(instance, storage):
        """ Set the storage for this field to the give storage.
        Values are migrated by doing a get before changing the storage
        and doing a set after changing the storage.

        The underlying storage must take care of cleaning up of removing
        references to the value stored using the unset method."""

    def getStorageName(instance=None):
        """Return the storage name that is configured for this field
        as a string"""

    def getStorageType(instance=None):
        """Return the type of the storage of this field as a string"""

    def getContentType(instance, fromBaseUnit=True):
        """Return the mime type of object if known or can be guessed;
        otherwise, return None."""

class IFileField(IObjectField):
    """Interface fora fields which (may) contain a file like FileField or
    TextField
    """

    #content_class = Attribute("""Class that is used to wrap the data like
    #                              OFS.Image.File for FileField"""

    def getBaseUnit(instance):
        """Return the value of the field wrapped in a base unit object
        """

    def getFilename(instance, fromBaseUnit=True):
        """Get file name of underlaying file object
        """

class IImageField(IFileField):
    """ Marker interface for detecting an image field """
