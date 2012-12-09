from AccessControl import ClassSecurityInfo
from Products.ATExtensions.ateapi import RecordsField
from DateTime import DateTime
from Products.ATExtensions.ateapi import DateTimeField, DateTimeWidget
from Products.Archetypes.public import *
from Products.CMFCore.permissions import View, ModifyPortalContent
from bika.lims import bikaMessageFactory as _
from bika.lims.content.bikaschema import BikaSchema
from bika.lims.config import PROJECTNAME
from bika.lims.browser.widgets import RecordsWidget
from zope.interface import implements
from Products.CMFCore.utils import getToolByName

schema = BikaSchema.copy() + Schema((
    StringField('Type',
        widget = StringWidget(
            label = _("Instrument type"),
        )
    ),
    StringField('Brand',
        widget = StringWidget(
            label = _("Brand"),
            description = _("The commercial 'make' of the instrument"),
        )
    ),
    StringField('Model',
        widget = StringWidget(
            label = _("Model"),
            description = _("The instrument's model number"),
        )
    ),
    StringField('SerialNo',
        widget = StringWidget(
            label = _("Serial No"),
            description = _("The serial number that uniquely identifies the instrument"),
        )
    ),
    StringField('CalibrationCertificate',
        widget = StringWidget(
            label = _("Calibration Certificate"),
            description = _("The instrument's calibration certificate and number"),
        )
    ),
    DateTimeField('CalibrationExpiryDate',
        with_time = 0,
        with_date = 1,
        widget = DateTimeWidget(
            label = _("Calibration Expiry Date"),
            description = _("Due Date for next calibration"),
        ),
    ),
    StringField('DataInterface',
        vocabulary = "getDataInterfacesList",
        widget = ReferenceWidget(
            checkbox_bound = 1,
            label = _("Data Interface"),
            description = _("Select an Import/Export interface for this instrument."),
        ),
    ),
    RecordsField('DataInterfaceOptions',
        type = 'interfaceoptions',
        subfields = ('Key','Value'),
        required_subfields = ('Key','Value'),
        subfield_labels = {'OptionValue': _('Key'),
                           'OptionText': _('Value'),},
        widget = RecordsWidget(
            label = _("Data Interface Options"),
            description = _("Use this field to pass arbitrary parameters to the export/import "
                            "modules."),
        ),
    ),
    ReferenceField('Manufacturer',
        vocabulary='getManufacturers',
        allowed_types=('Manufacturer',),
        relationship='InstrumentManufacturer',
        required=1,
        widget=SelectionWidget(
            format='select',
            label=_('Manufacturer'),
        ),
    ),
    ComputedField('ManufacturerUID',
        expression='here.getManufacturer() and here.getManufacturer().UID() or None',
        widget=ComputedWidget(
        ),
    ),
    ReferenceField('Supplier',
        vocabulary='getSuppliers',
        allowed_types=('Supplier',),
        relationship='InstrumentSupplier',
        required=1,
        widget=SelectionWidget(
            format='select',
            label=_('Supplier'),
        ),
    ),
    ComputedField('SupplierUID',
        expression='here.getSupplier() and here.getSupplier().UID() or None',
        widget=ComputedWidget(
        ),
    ),
    TextField('InlabCalibrationProcedure',
        schemata = 'Procedures',
        default_content_type = 'text/x-web-intelligent',
        allowable_content_types = ('text/x-web-intelligent',),
        default_output_type="text/html",
        widget = TextAreaWidget(
            label = _("In-lab calibration procedure"),
            description = _("Instructions for in-lab regular calibration routines intended for analysts"),
        ),
    ),
    TextField('PreventiveMaintenanceProcedure',
        schemata = 'Procedures',
        default_content_type = 'text/x-web-intelligent',
        allowable_content_types = ('text/x-web-intelligent',),
        default_output_type="text/html",
        widget = TextAreaWidget(
            label = _("Preventive maintenance procedure"),
            description = _("Instructions for regular preventive and maintenance routines intended for analysts"),
        ),
    ),
))
schema['description'].widget.visible = True
schema['description'].schemata = 'default'

def getDataInterfaces(context):
    """ Return the current list of data interfaces
    """
    from bika.lims.exportimport import instruments
    exims = [('',context.translate(_('None')))]
    for exim_id in instruments.__all__:
        exim = getattr(instruments, exim_id)
        exims.append((exim_id, exim.title))
    return DisplayList(exims)

class Instrument(BaseContent):
    security = ClassSecurityInfo()
    displayContentsTab = False
    schema = schema

    _at_rename_after_creation = True
    def _renameAfterCreation(self, check_auto_id=False):
        from bika.lims.idserver import renameAfterCreation
        renameAfterCreation(self)

    def Title(self):
        return self.title

    def getDataInterfacesList(self):
        return getDataInterfaces(self)
    
    def getManufacturers(self):        
        manufacturers = []
        bsc = getToolByName(self, "bika_setup_catalog")
        for manufacturer in bsc(portal_type = 'Manufacturer',
                                inactive_state = 'active'):
            manufacturers.append([manufacturer.UID, manufacturer.Title])
        manufacturers.sort(lambda x,y:cmp(x[1], y[1]))
        return DisplayList(manufacturers)

    def getSuppliers(self):        
        suppliers = []
        bsc = getToolByName(self, "bika_setup_catalog")
        for supplier in bsc(portal_type = 'Supplier',
                                inactive_state = 'active'):
            suppliers.append([supplier.UID, supplier.getName])
        suppliers.sort(lambda x,y:cmp(x[1], y[1]))
        return DisplayList(suppliers)

registerType(Instrument, PROJECTNAME)
