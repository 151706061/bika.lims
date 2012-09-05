from AccessControl import getSecurityManager
from DateTime import DateTime
from Products.CMFCore.utils import getToolByName
from bika.lims.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from bika.lims import bikaMessageFactory as _
from bika.lims.browser.bika_listing import BikaListingView
from bika.lims.browser.reports.selection_macros import SelectionMacrosView
from bika.lims.interfaces import IReportFolder
from bika.lims.utils import getUsers
from bika.lims.utils import logged_in_client
from bika.lims.utils import pretty_user_email
from bika.lims.utils import pretty_user_name_or_id
from cStringIO import StringIO
from plone.app.content.browser.interfaces import IFolderContentsView
from plone.app.layout.globals.interfaces import IViewView
from zope.interface import implements
import json
import os
import plone
import sys
import xhtml2pdf.pisa as pisa


class ProductivityView(BrowserView):
    """ Productivity View form
    """
    implements(IViewView)
    template = ViewPageTemplateFile("templates/productivity.pt")
    def __call__(self):
        self.selection_macros = SelectionMacrosView(self.context, self.request)
        self.icon = "++resource++bika.lims.images/report_big.png"
        self.getAnalysts = getUsers(self.context, ['Manager', 'LabManager', 'Analyst'])
        return self.template()


class QualityControlView(BrowserView):
    """ QC View form
    """
    implements(IViewView)
    template = ViewPageTemplateFile("templates/qualitycontrol.pt")
    def __call__(self):
        self.selection_macros = SelectionMacrosView(self.context, self.request)
        self.icon = "++resource++bika.lims.images/report_big.png"
        return self.template()


class AdministrationView(BrowserView):
    """ Administration View form
    """
    implements(IViewView)
    template = ViewPageTemplateFile("templates/administration.pt")
    def __call__(self):
        self.selection_macros = SelectionMacrosView(self.context, self.request)
        self.icon = "++resource++bika.lims.images/report_big.png"
        return self.template()


class ReportHistoryView(BikaListingView):
    """ Report history form
    """
    implements(IViewView)

    def __init__(self, context, request):
        super(ReportHistoryView, self).__init__(context, request)

        self.catalog = "bika_catalog"
        # this will be reset in the call to filter on own reports
        self.contentFilter = {'portal_type': 'Report',
                              'sort_order': 'reverse'}
        self.context_actions = {}
        self.show_sort_column = False
        self.show_select_row = False
        self.show_select_column = True
        self.pagesize = 50

        self.icon = "++resource++bika.lims.images/report_big.png"
        self.title = _("Reports")
        self.description = ""

        # this is set up in call where member is authenticated
        self.columns = {}
        self.review_states = []

    def __call__(self):
        this_client = logged_in_client(self.context)
        if this_client:
            self.contentFilter = {
                'portal_type': 'Report',
                'getClientUID': this_client.UID(),
                'sort_order': 'reverse'}
            self.columns = {
                'Title': {'title': _('Title')},
                'FileSize': {'title': _('Size')},
                'Created': {'title': _('Created')},
                'By': {'title': _('By')}, }
            self.review_states = [
                {'id':'default',
                 'title': 'All',
                 'contentFilter':{},
                 'columns': ['Title',
                             'FileSize',
                             'Created',
                             'By']},
            ]
        else:
            self.contentFilter = {
                'portal_type': 'Report',
                'sort_order': 'reverse'}

            self.columns = {
                'Client': {'title': _('Client')},
                'Title': {'title': _('Report Type')},
                'FileSize': {'title': _('Size')},
                'Created': {'title': _('Created')},
                'By': {'title': _('By')},
            }
            self.review_states = [
                {'id':'default',
                 'title': 'All',
                 'contentFilter':{},
                 'columns': ['Client',
                             'Title',
                             'FileSize',
                             'Created',
                             'By']},
            ]

        return super(ReportHistoryView, self).__call__()

    def lookupMime(self, name):
        mimetool = getToolByName(self, 'mimetypes_registry')
        mimetypes = mimetool.lookup(name)
        if len(mimetypes):
            return mimetypes[0].name()
        else:
            return name

    def folderitems(self):
        items = BikaListingView.folderitems(self)
        props = self.context.portal_properties.site_properties
        for x in range(len(items)):
            if not items[x].has_key('obj'): continue
            obj = items[x]['obj']
            obj_url = obj.absolute_url()
            file = obj.getReportFile()
            icon = file.getBestIcon()

            items[x]['Client'] = ''
            client = obj.getClient()
            if client:
                items[x]['replace']['Client'] = "<a href='%s'>%s</a>" % \
                    (client.absolute_url(), client.Title())
            items[x]['FileSize'] = '%sKb' % (file.get_size() / 1024)
            items[x]['Created'] = self.ulocalized_time(obj.created())
            items[x]['By'] = pretty_user_name_or_id(self.context, obj.Creator())

            items[x]['replace']['Title'] = \
                 "<a href='%s/at_download/ReportFile'>%s</a>" % \
                 (obj_url, items[x]['Title'])
        return items

class SubmitForm(BrowserView):
    """ Redirect to specific report
    """
    implements(IViewView)
    frame_template = ViewPageTemplateFile("templates/report_frame.pt")
    # default and errors use this template:
    template = ViewPageTemplateFile("templates/productivity.pt")

    def __init__(self, context, request):
        BrowserView.__init__(self, context, request)

    def __call__(self):
        """Create and render selected report
        """

        # if there's an error, we return productivity.pt which requires these.
        self.selection_macros = SelectionMacrosView(self.context, self.request)

        report_id = self.request.get('report_id', '')
        if not report_id:
            message =  "No report specified in request"
            self.logger.error(message)
            self.context.plone_utils.addPortalMessage(message, 'error')
            return self.template()

        props = self.context.portal_properties.site_properties

        self.date = DateTime()
        username = self.context.portal_membership.getAuthenticatedMember().getUserName()
        self.reporter = pretty_user_name_or_id(self.context, username)
        self.reporter_email = pretty_user_email(self.context, username)

        lab = self.context.bika_setup.laboratory
        self.lab_title = lab.getName()
        self.lab_address = lab.getPrintAddress()
        self.lab_email = lab.getEmailAddress()
        self.lab_url = lab.getLabURL()

        client = logged_in_client(self.context)
        if client:
            clientuid = client.UID()
            self.client_title = client.Title()
            self.client_address = client.getPrintAddress()
        else:
            clientuid = None
            self.client_title = None
            self.client_address = None

        ## Render form output

        # the report can add file names to this list; they will be deleted
        # once the PDF has been generated.  temporary plot image files, etc.
        self.request['to_remove'] = []

        try:
            exec("from bika.lims.browser.reports.%s import Report" % report_id)
        except ImportError:
            message = "Report %s not found (shouldn't happen)" % report_id
            self.logger.error(message)
            self.context.plone_utils.addPortalMessage(message, 'error')
            return self.template()

        # Report must return dict with:
        # - report_title - title string for pdf/history listing
        # - report_data - rendered report
        output = Report(self.context, self.request)()

        if type(output) in (str, unicode, bytes):
            # remove temporary files
            for f in self.request['to_remove']:
                os.remove(f)
            return output

        ## The report output gets pulled through report_frame.pt
        self.reportout = output['report_data']
        framed_output = self.frame_template()

        # this is the good part
        pisa.showLogging()
        ramdisk = StringIO()
        pdf = pisa.CreatePDF(framed_output, ramdisk)
        result = ramdisk.getvalue()
        ramdisk.close()

        ## Create new report object
        reportid = self.aq_parent.generateUniqueId('Report')
        self.aq_parent.invokeFactory(id = reportid, type_name = "Report")
        report = self.aq_parent._getOb(reportid)
        report.edit(Client = clientuid)
        report.processForm()

        ## write pdf to report object
        report.edit(title = output['report_title'], ReportFile = result)
        report.reindexObject()

        fn = "%s - %s" % (self.date.strftime(r"%Y-%m-%d"),
                          output['report_title'])

        # remove temporary files
        for f in self.request['to_remove']:
            os.remove(f)

        if not pdf.err:
            setheader = self.request.RESPONSE.setHeader
            setheader('Content-Type', 'application/pdf')
            setheader("Content-Disposition", "attachment;filename=\"%s\""%fn)
            self.request.RESPONSE.write(result)

        return
