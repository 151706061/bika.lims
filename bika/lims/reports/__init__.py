from Products.CMFPlone.utils import _createObjectByType
from bika.lims.utils import tmpID
from zExceptions import BadRequest
from zope.interface import alsoProvides
from bika.lims.reports.interfaces import *


class CreateReport(object):
    """docstring for CreateReport"""
    def __init__(self, context, request=None):
        self.context = context
        self.request = request

    def __call__(self):
        if 'report' not in self.request:
            raise BadRequest("No report was specified in request!")
        report_type = self.request['report']        
        obj = _createObjectByType('ReportCollection', self.context, tmpID())

        obj.unmarkCreationFlag()
    #    productivity_reports = ['dailysamplesreceived', 'samplesreceivedvsreported', 'analysesperservice', 'analysespersampletype', \
    #     'analysesperclient', 'analysestats', 'analysestats_overtime', 'analysesperdepartment', 'analysesperformedpertotal', \
    #     'analysesattachments', 'dataentrydaybook']
        if report_type == 'productivity_dailysamplesreceived' :
            alsoProvides(obj, IDailySamplesReceived)
            obj.Schema().getField('query').set(obj,[
                {'i': 'DateReceived', 'o': 'plone.app.querystring.operation.date.today', 'v': ['', '']}
                ])
        elif report_type == 'productivity_samplesreceivedvsreported' :
            alsoProvides(obj, ISamplesReceivedVsReported)
            obj.Schema().getField('query').set(obj,[
                {'i': 'DateReceived', 'o': 'plone.app.querystring.operation.date.today', 'v': ['', '']}
                ])
        elif report_type == 'productivity_analysesperservice' :
            alsoProvides(obj, IAnalysesPerService)
            obj.Schema().getField('query').set(obj,[
                {'i': 'created', 'o': 'plone.app.querystring.operation.date.today'}, \
                {'i': 'DatePublished', 'o': 'plone.app.querystring.operation.date.today'}, \
                {'i': 'review_state', 'o': 'plone.app.querystring.operation.selection.is'}, \
                {'i': 'cancellation_state', 'o': 'plone.app.querystring.operation.selection.is'}, \
                {'i': 'worksheetanalysis_review_state', 'o': 'plone.app.querystring.operation.selection.is'} \
                ])
        elif report_type == 'productivity_analysespersampletype' :
            alsoProvides(obj, IAnalysesPerSampleType)
            obj.Schema().getField('query').set(obj,[
                {'i': 'created', 'o': 'plone.app.querystring.operation.date.today'}, \
                {'i': 'review_state', 'o': 'plone.app.querystring.operation.selection.is'}, \
                {'i': 'cancellation_state', 'o': 'plone.app.querystring.operation.selection.is'}, \
                {'i': 'worksheetanalysis_review_state', 'o': 'plone.app.querystring.operation.selection.is'} \
                ])    
        elif report_type == 'productivity_analysesperclient' :
            alsoProvides(obj, IAnalysesPerClient)
            obj.Schema().getField('query').set(obj,[
                {'i': 'created', 'o': 'plone.app.querystring.operation.date.today'}, \
                {'i': 'review_state', 'o': 'plone.app.querystring.operation.selection.is'}, \
                {'i': 'cancellation_state', 'o': 'plone.app.querystring.operation.selection.is'}, \
                {'i': 'worksheetanalysis_review_state', 'o': 'plone.app.querystring.operation.selection.is'} \
                ])
        elif report_type == 'productivity_analysestats' :
            alsoProvides(obj, IAnalysesStats)
            obj.Schema().getField('query').set(obj,[
                {'i': 'ClientTitle', 'o': 'plone.app.querystring.operation.selection.is'}, \
                {'i': 'DateReceived', 'o': 'plone.app.querystring.operation.date.today'}, \
                {'i': 'worksheetanalysis_review_state', 'o': 'plone.app.querystring.operation.selection.is'} \
                ])    
        elif report_type == 'productivity_analysestats_overtime' :
            alsoProvides(obj, IAnalysesStatsOvertime)
            obj.Schema().getField('query').set(obj,[
                {'i': 'AnalysisService', 'o': 'plone.app.querystring.operation.selection.is'}, \
                {'i': 'Analyst', 'o': 'plone.app.querystring.operation.selection.is'}, \
                {'i': 'InstrumentTitle', 'o': 'plone.app.querystring.operation.selection.is'}, \
                {'i': 'DateReceived', 'o': 'plone.app.querystring.operation.date.today'}
                ])    
        elif report_type == 'productivity_analysesperdepartment' :
            alsoProvides(obj, IAnalysesPerDepartment)
            obj.Schema().getField('query').set(obj,[
                {'i': 'created', 'o': 'plone.app.querystring.operation.date.today'}, \
                {'i': 'review_state', 'o': 'plone.app.querystring.operation.selection.is'}
                ])
        elif report_type == 'productivity_analysesperformedpertotal' :
            alsoProvides(obj, IAnalysesPerformedPerTotal)
            obj.Schema().getField('query').set(obj,[
                {'i': 'created', 'o': 'plone.app.querystring.operation.date.today'}, \
                {'i': 'review_state', 'o': 'plone.app.querystring.operation.selection.is'}
                ])
        elif report_type == 'productivity_analysesattachments' :
            alsoProvides(obj, IAnalysesAttachments)
            obj.Schema().getField('query').set(obj,[
                {'i': 'ClientTitle', 'o': 'plone.app.querystring.operation.selection.is'}, \
                {'i': 'created', 'o': 'plone.app.querystring.operation.date.today'}
                ])
        elif report_type == 'productivity_dataentrydaybook' :
            alsoProvides(obj, IDataEntryDayBook)
            obj.Schema().getField('query').set(obj,[
                {'i': 'created', 'o': 'plone.app.querystring.operation.date.today'}
                ])
        self.request.response.redirect(obj.absolute_url())




        