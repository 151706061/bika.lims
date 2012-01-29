"""ReferenceSupplier.
"""

from AccessControl import ClassSecurityInfo
from DateTime import DateTime
from Products.Archetypes.public import *
from Products.Archetypes.utils import DisplayList
from Products.CMFCore import permissions
from Products.CMFCore.permissions import ListFolderContents, ModifyPortalContent
from Products.CMFCore.utils import getToolByName
from bika.lims.config import PROJECTNAME, ManageReferenceSuppliers
from bika.lims.content.organisation import Organisation
from bika.lims.interfaces import IReferenceSupplier
from zope.interface import implements
from bika.lims import bikaMessageFactory as _

schema = Organisation.schema.copy()

schema['AccountNumber'].write_permission = ManageReferenceSuppliers

class ReferenceSupplier(Organisation):
    implements(IReferenceSupplier)
    security = ClassSecurityInfo()
    displayContentsTab = False
    schema = schema

    _at_rename_after_creation = True
    def _renameAfterCreation(self, check_auto_id=False):
        from bika.lims.idserver import renameAfterCreation
        renameAfterCreation(self)

registerType(ReferenceSupplier, PROJECTNAME)
