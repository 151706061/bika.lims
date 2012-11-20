from AccessControl import getSecurityManager
from DateTime import DateTime
from Products.AdvancedQuery import Or, MatchRegexp, Between
from Products.Archetypes.config import REFERENCE_CATALOG
from Products.CMFCore.utils import getToolByName
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from bika.lims import PMF, logger, bikaMessageFactory as _
from bika.lims.browser import BrowserView
from bika.lims.browser.analysisrequest import AnalysisRequestWorkflowAction, \
    AnalysisRequestsView, AnalysisRequestAddView
from bika.lims.browser.bika_listing import BikaListingView
from bika.lims.browser.client import ClientAnalysisRequestsView, \
    ClientSamplesView
from bika.lims.browser.publish import Publish
from bika.lims.browser.sample import SamplesView
from bika.lims.idserver import renameAfterCreation
from bika.lims.interfaces import IContacts
from bika.lims.permissions import *
from bika.lims.subscribers import doActionFor, skip
from bika.lims.utils import isActive
from operator import itemgetter
from plone.app.content.browser.interfaces import IFolderContentsView
from plone.app.layout.globals.interfaces import IViewView
from zope.i18n import translate
from zope.interface import implements
from zope.cachedescriptors.property import Lazy as lazy_property
import json
import plone

class BatchAnalysisRequestsView(AnalysisRequestsView, AnalysisRequestAddView):
    template = ViewPageTemplateFile("templates/analysisrequests.pt")
    ar_add = ViewPageTemplateFile("templates/ar_add.pt")
    def __init__(self, context, request):
        super(BatchAnalysisRequestsView, self).__init__(context, request)
        self.contentFilter['getBatchUID'] = self.context.UID()

    def __call__(self):
        self.context_actions = {}
        bc = getToolByName(self.context, 'bika_catalog')
        wf = getToolByName(self.context, 'portal_workflow')
        mtool = getToolByName(self.context, 'portal_membership')
        addPortalMessage = self.context.plone_utils.addPortalMessage
        if isActive(self.context):
            if mtool.checkPermission(AddAnalysisRequest, self.portal):
                self.context_actions[self.context.translate(_('Add new'))] = {
                    'url':self.context.absolute_url() + '/ar_add?col_count=1',
                    'icon': '++resource++bika.lims.images/add.png'}
        return super(BatchAnalysisRequestsView, self).__call__()

    @lazy_property

    def Client(self):
        bc = getToolByName(self.context, 'bika_catalog')
        proxies = bc(portal_type="AnalysisRequest", getBatchUID=self.context.UID())
        if proxies:
            return proxies[0].getObject()

    def getMemberDiscountApplies(self):
        client = self.Client
        return client and client.getMemberDiscountApplies() or False

    def getRestrictedCategories(self):
        client = self.Client
        return client and client.getRestrictedCategories() or []

    def getDefaultCategories(self):
        client = self.Client
        return client and client.getDefaultCategories() or []

class BatchSamplesView(SamplesView):
    def __init__(self, context, request):
        super(BatchSamplesView, self).__init__(context, request)
        self.view_url = self.context.absolute_url() + "/samples"
        if 'path' in self.contentFilter:
            del(self.contentFilter['path'])

    def contentsMethod(self, contentFilter):
        tool = getToolByName(self.context, self.catalog)
        state = [x for x in self.review_states if x['id'] == self.review_state][0]
        for k,v in state['contentFilter'].items():
            self.contentFilter[k] = v
        tool_samples = tool(contentFilter)
        samples = {}
        for sample in (p.getObject() for p in tool_samples):
            for ar in sample.getAnalysisRequests():
                if ar.getBatchUID() == self.context.UID():
                    samples[sample.getId()] = sample
        return samples.values()

class ajaxGetBatchInfo(BrowserView):
    """ Grab the details for Doctor, Patient, Hospital (Titles).
    These are displayed onload next to the ID fields, but they are not part of the schema.
    """
    def __call__(self):
        plone.protect.CheckAuthenticator(self.request)

        batch = self.context
        clientUID = batch.getClientUID()
        client = self.portal_catalog(portal_type='Client', UID=batch.getClientUID())
        patient = self.bika_patient_catalog(portal_type='Patient', UID=batch.getPatientUID())
        doctor = self.portal_catalog(portal_type='Doctor', UID=batch.getDoctorUID())

        ret = {'Client': client and client[0].Title or 'None',
               'Patient': patient and patient[0].Title or 'None',
               'Doctor': doctor and doctor[0].Title or 'None'}

        return json.dumps(ret)

