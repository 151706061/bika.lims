from AccessControl import ClassSecurityInfo
from DateTime import DateTime
from Products.ATContentTypes.lib.historyaware import HistoryAwareMixin
from Products.ATContentTypes.utils import DT2dt, dt2DT
from Products.Archetypes.public import *
from Products.Archetypes.references import HoldingReference
from Products.CMFCore.utils import getToolByName
from bika.lims import bikaMessageFactory as _
from bika.lims.browser.fields import DurationField
from bika.lims.config import PROJECTNAME
from bika.lims.content.bikaschema import BikaSchema
from bika.lims.interfaces import IBatch
from bika.lims.utils import isActive
from bika.lims.workflow import doActionFor
from bika.lims.workflow import skip
from datetime import timedelta
from zope.interface import implements
import json
import plone

schema = BikaSchema.copy() + Schema((
    StringField('BatchID',
        searchable=True,
        required=0,
        widget=StringWidget(
            visible = False,
            label=_("Batch ID"),
        )
    ),
    StringField('ClientBatchID',
        searchable=True,
        required=0,
        widget=StringWidget(
            label=_("Client Batch ID")
        )
    ),
    LinesField('BatchLabels',
        vocabulary = "BatchLabelVocabulary",
        widget=MultiSelectionWidget(
            label=_("Batch labels"),
            format="checkbox",
        )
    ),
    TextField('Remarks',
        searchable=True,
        default_content_type='text/x-web-intelligent',
        allowable_content_types=('text/x-web-intelligent',),
        default_output_type="text/html",
        widget=TextAreaWidget(
            macro="bika_widgets/remarks",
            label=_('Remarks'),
            append_only=True,
        )
    )
)
)

schema['title'].required = False
schema['title'].widget.visible = False
schema['description'].required = False
schema['description'].widget.visible = True

class Batch(BaseContent):
    implements(IBatch)
    security = ClassSecurityInfo()
    displayContentsTab = False
    schema = schema

    _at_rename_after_creation = True
    def _renameAfterCreation(self, check_auto_id=False):
        from bika.lims.idserver import renameAfterCreation
        renameAfterCreation(self)

    def _getCatalogTool(self):
        from bika.lims.catalog import getCatalog
        return getCatalog(self)

    def Title(self):
        """ Return the BatchID or id as title """
        res = self.getBatchID()
        return str(res).encode('utf-8')

    security.declarePublic('getBatchID')
    def getBatchID(self):
        return self.getId()

    def getContacts(self, dl=True):
        pc = getToolByName(self, 'portal_catalog')
        bc = getToolByName(self, 'bika_catalog')
        bsc = getToolByName(self, 'bika_setup_catalog')
        pairs = []
        objects = []
        for contact in bsc(portal_type = 'LabContact',
                           inactive_state = 'active',
                           sort_on = 'sortable_title'):
            pairs.append((contact.UID, contact.Title))
            if not dl:
                objects.append(contact.getObject())
        return dl and DisplayList(pairs) or objects

    def getCCs(self):
        items = []
        for contact in self.getContacts(dl=False):
            item = {'uid': contact.UID(), 'title': contact.Title()}
            ccs = []
            if hasattr(contact, 'getCCContact'):
                for cc in contact.getCCContact():
                    if isActive(cc):
                        ccs.append({'title': cc.Title(),
                                    'uid': cc.UID(),})
            item['ccs_json'] = json.dumps(ccs)
            item['ccs'] = ccs
            items.append(item)
        items.sort(lambda x, y:cmp(x['title'].lower(), y['title'].lower()))
        return items

    def BatchLabelVocabulary(self):
        """ return all batch labels """
        bsc = getToolByName(self, 'bika_setup_catalog')
        ret = []
        for p in bsc(portal_type = 'BatchLabel',
                      inactive_state = 'active',
                      sort_on = 'sortable_title'):
            ret.append((p.UID, p.Title))
        return DisplayList(ret)

    def getAnalysisRequests(self):
        bc = getToolByName(self, 'bika_catalog')
        uid = self.UID()
        return [b.getObject() for b in bc(portal_type='AnalysisRequest', getBatchUID=uid)]

    def workflow_guard_receive(self):
        """Permitted when all Samples are > sample_received
        """
        wf = getToolByName(self, 'portal_workflow')
        states = ['sample_registered', 'to_be_sampled', 'sampled', 'to_be_preserved', 'sample_due']
        import pdb;pdb.set_trace()
        for o in self.getAnalysisRequests():
            if wf.getInfoFor(o, 'review_state') in states:
                return False
        return True

    # def workflow_before_receive(self, state_info):
    #     pass

    def workflow_after_receive(self, state_info):
        skip(self, 'receive')

    def workflow_guard_open(self):
        """Permitted when at least one sample is < sample_received
        """
        wf = getToolByName(self, 'portal_workflow')
        states = ['sample_registered', 'to_be_sampled', 'sampled', 'to_be_preserved', 'sample_due']
        for o in self.getAnalysisRequests():
            if wf.getInfoFor(o, 'review_state') in states:
                return True
        return False

    # def workflow_before_open(self, state_info):
    #     pass

    def workflow_after_open(self, state_info):
        skip(self, 'open')
        # reset everything and return to open state
        self.setDateReceived(None)
        self.reindexObject(idxs = ["getDateReceived", ])

    def workflow_guard_submit(self):
        """Permitted when all samples >= to_be_verified
        """
        wf = getToolByName(self, 'portal_workflow')
        states = ['sample_registered', 'to_be_sampled', 'sampled', 'to_be_preserved', 'sample_due', 'sample_received']
        for o in self.getAnalysisRequests():
            if wf.getInfoFor(o, 'review_state') in states:
                return False
        return True

    # def workflow_before_submit(self, state_info):
    #     pass

    # def workflow_after_submit(self, state_info):
    #     skip(self, 'open')

    def workflow_guard_verify(self):
        """Permitted when all samples >= verified
        """
        wf = getToolByName(self, 'portal_workflow')
        states = ['sample_registered', 'to_be_sampled', 'sampled', 'to_be_preserved', 'sample_due', 'sample_received',
                  'to_be_verified']
        for o in self.getAnalysisRequests():
            if wf.getInfoFor(o, 'review_state') in states:
                return False
        return True

    # def workflow_before_verify(self, state_info):
    #     pass

    # def workflow_after_verify(self, state_info):
    #     skip(self, 'open')

    # def workflow_guard_close(self):
    #     return True

    # def workflow_before_close(self, state_info):
    #     pass

    # def workflow_after_close(self, state_info):
    #     skip(self, 'open')


registerType(Batch, PROJECTNAME)
