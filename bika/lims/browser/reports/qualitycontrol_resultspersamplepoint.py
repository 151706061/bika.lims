from AccessControl import getSecurityManager
from DateTime import DateTime
from Products.CMFCore.utils import getToolByName
from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from bika.lims import bikaMessageFactory as _
from bika.lims.utils import formatDateQuery, formatDateParms
from gpw import plot
from plone.app.content.browser.interfaces import IFolderContentsView
from plone.app.layout.globals.interfaces import IViewView
from zope.interface import implements
import json
import os
import plone
import tempfile

class Report(BrowserView):
    implements(IViewView)
    template = ViewPageTemplateFile("templates/qualitycontrol_resultspersamplepoint.pt")

    def __init__(self, context, request, report):
        self.report = report
        BrowserView.__init__(self, context, request)

    def error(self, message):
        self.context.plone_utils.addPortalMessage(message, 'error')
        self.template = ViewPageTemplateFile("templates/qualitycontrol.pt")
        raise Redirect

    def __call__(self):
        self.portal = getToolByName(self.context, 'portal_url').getPortalObject()
        self.portal_url = self.portal.absolute_url()
        bsc = getToolByName(self.context, "bika_setup_catalog")
        bac = getToolByName(self.context, "bika_analysis_catalog")
        MinimumResults = self.context.bika_setup.getMinimumResults()
        rc = getToolByName(self.context, "reference_catalog")
        site_props = self.context.portal_properties.site_properties
        localTimeFormat = site_props.getProperty("localTimeFormat")
        localTimeOnlyFormat = site_props.getProperty("localTimeOnlyFormat")
        localLongTimeFormat = site_props.getProperty("localLongTimeFormat")
##        warning_icon = "<span style='font-weight:600;font-size:110%;font-color:#ff0000;'>!</span>"
##        error_icon = "<span style='font-weight:600;font-size:110%;color:#ff6666;'>!</span>"
        warning_icon = "<img " +\
            "src='"+self.portal_url+"/++resource++bika.lims.images/warning.png' " +\
            "height='9' width='9'/>"
        error_icon = "<img " +\
            "src='"+self.portal_url+"/++resource++bika.lims.images/exclamation.png' " +\
            "height='9' width='9'/>"

        header = _("Results per sample point")
        subheader = _("Analysis results for per sample point and analysis service")

        title_parts = []

        # Parse form criteria

        client_uid = self.request.form.get("ClientUID", "")
        client_title = client_uid and rc.lookupObject(client_uid).Title() or ''
        if client_title:
            title_parms.append(client_title)

        st_uid = self.request.form["SampleTypeUID"]
        st_title = rc.lookupObject(st_uid).Title()
        title_parts.append(st_title)

        sp_uid = self.request.form["SamplePointUID"]
        sp_title = rc.lookupObject(sp_uid).Title()
        title_parts.append(sp_title)

        spec = self.request.form.get('spec', 'lab')
        spec_title = spec == 'lab' and _("Lab") or _("Client")

        if "ServiceUID" not in self.request.form:
            self.error(_("No analysis services were selected."))
        if type(self.request.form["ServiceUID"]) in (list, tuple):
            service_uids = self.request.form["ServiceUID"] # Multiple services
        else:
            service_uids = (self.request.form["ServiceUID"],) # Single service
        services = [rc.lookupObject(s) for s in service_uids]

        parms = []
        if client_title:
            parms.append({'title': _("Client"), "value": client_title})
        parms.append({'title': _("Sample point"), "value": sp_title})
        parms.append({'title': _("Sample type"), "value": st_title})
        parms.append({'title': _("Services"),
                      "value": ','.join([s.Title() for s in services])})

        query = {
            "portal_type": "Analysis",
            "review_state": ['verified', 'published'],
            "getSamplePointUID": sp_uid,
            "getSampleTypeUID": st_uid,
            "getServiceUID": service_uids,
            "sort_on": "getDateSampled"
        }


        date_query = formatDateQuery(self.context, 'DateAnalysisPublished')
        if date_query:
            title_parts.append(self.context.translate(_("Published")))
            query['getDateAnalysisPublished'] = date_query
            query['review_state'] = 'published'
            parms.append({
                'title': _('Published'),
                'value': formatDateParms(self.context, 'DateAnalysisPublished'),
                'type': 'text'
            })
##        if self.request.form.has_key('cancellation_state'):
##            query['cancellation_state'] = self.request.form['cancellation_state']
##            cancellation_state = workflow.getTitleForStateOnType(
##                self.request.form['cancellation_state'], 'Analysis')
##            title_parts.append(self.context.translate(_(cancellation_state)))
##            parms.append({
##                'title': _('Active'),
##                'value': cancellation_state,
##                'type': 'text'
##            })
        if self.request.form.has_key('ws_review_state'):
            query['worksheetanalysis_review_state'] = self.request.form['ws_review_state']
            ws_review_state = workflow.getTitleForStateOnType(
                self.request.form['ws_review_state'], 'Analysis')
            title_parts.append(self.context.translate(_(ws_review_state)))
            parms.append({
                'title': _('Assigned to worksheet'),
                'value': ws_review_state,
                'type': 'text'
            })

        # Query the catalog and store analysis data in a dict
        analyses = {}
        out_of_range_count = 0
        in_shoulder_range_count = 0
        analysis_count = 0

        proxies = bac(query)
        if not proxies:
            self.error(_("No analyses matched your query"))

        cached_specs = {} # keyed by parent_folder

        def lookup_spec(analysis):
            # If an analysis is OUT OF RANGE, the failed spec values are passed
            # back from the result_in_range function. But if the analysis resuit
            # is IN RANGE, we need to look it up.
            service = analysis['service']
            keyword = service['Keyword']
            analysis = analysis['obj']
            if spec == "client":
                parent = analysis.aq_parent.aq_parent
            else:
                parent = self.context.bika_setup.bika_analysisspecs
            if not parent.UID() in cached_specs:
                proxies = bsc(
                    portal_type = 'AnalysisSpec',
                    getSampleTypeUID = st_uid,
                    path = {"query": "/".join(parent.getPhysicalPath()),
                            "level" : 0 }
                )
                if proxies:
                    spec_obj = proxies[0].getObject()
                    this_spec = spec_obj.getResultsRangeDict()
                else:
                    this_spec = {'min':None,'max':None}
                cached_specs[parent.UID()] = this_spec
            else:
                this_spec = cached_specs[parent.UID()]
            return this_spec

        ## Compile a list of dictionaries, with all relevant analysis data
        for analysis in (a.getObject() for a in proxies):
            client = analysis.aq_parent.aq_parent
            uid = analysis.UID()
            service = analysis.getService()
            keyword = service.getKeyword()
            service_title = "%s (%s)" % (service.Title(), service.getKeyword())
            result_in_range = analysis.result_in_range(specification=spec)
            try:
                precision = str(service.getPrecision())
            except:
                precision = "2"

            if service_title not in analyses.keys():
                analyses[service_title] = []
            try:
                result = float(analysis.getResult())
            except:
                # XXX Unfloatable analysis results should be indicated
                continue
            analyses[service_title].append({
                'service': service,
                'obj': analysis,
                'Request ID': analysis.aq_parent.getId(),
                'Analyst': analysis.getAnalyst(),
                'Result': result,
                'precision': precision,
                'Sampled': analysis.getDateSampled(),
                'Captured': analysis.getResultCaptureDate(),
                'result_in_range': result_in_range,
                'Unit': service.getUnit(),
                'Keyword': keyword,
                'icons': '',
            })
            analysis_count += 1

        keys = analyses.keys()
        keys.sort()

        parms += [
            {"title": _("Total analyses"), "value": analysis_count},
            {"title": _("Analysis specification"), "value": spec_title},
        ]

        ## This variable is output to the TAL
        self.report_data = {
            'header': header,
            'subheader': subheader,
            'parms': parms,
            'tables': [],
            'footnotes': [], # list of strings
        }

        plotscript = """
        set terminal png size 700,350 font "Verdana, 8"
        set title "%(title)s"
        set xlabel "%(xlabel)s"
        set ylabel "%(ylabel)s"
        set key off
        #set logscale
        set timefmt "%(timefmt)s"
        set xdata time
        set format x "%(xtimefmt)s"
        set xrange ["%(x_start)s":"%(x_end)s"]
        set yrange [%(y_start)s:%(y_end)s]
        set xtics rotate by 90 offset 0,-5 out nomirror
        set ytics nomirror
        plot "gpw_DATAFILE_gpw" using 1:5 title 'data' with points pt 7 ps .5 lc rgb '#0060ad',\
        '' using 1:5 smooth bezier lw .5'
        """
        ## Compile plots and format data for display
        for service_title in keys:
            # used to calculate XY axis ranges
            result_values = [int(o['Result']) for o in analyses[service_title]]
            result_dates = [o['Sampled'] for o in analyses[service_title]]

            parms = []
            plotdata = ""

            for a in analyses[service_title]:

                a['Sampled'] = a['Sampled'].strftime(localLongTimeFormat)
                a['Captured'] = a['Captured'].strftime(localLongTimeFormat)

                plotdata += "%s\t%s\n"%(
                    a['Sampled'],
                    a['Result'],
                )
                plotdata.encode('utf-8')

                a['Result'] = str("%." + precision + "f")% a['Result']

                in_range = a['result_in_range']
                # in-range: lookup spec, if possible
                if in_range[1] == None:
                    this_spec_results = lookup_spec(a)
                    if this_spec_results and a['Keyword'] in this_spec_results:
                        this_spec = this_spec_results[a['Keyword']]
                        in_range[1] == this_spec
                # result out of range
                if in_range[0] == False:
                    out_of_range_count += 1
                    a['Result'] = "%s %s" % (a['Result'], error_icon)
                # result almost out of range
                if in_range[0] == 1:
                    in_shoulder_range_count += 1
                    a['Result'] = "%s %s" % (a['Result'], warning_icon)
                a['range_min'] = in_range[1] and in_range[1]['min'] or ''
                a['range_max'] = in_range[1] and in_range[1]['max'] or ''

            spec_str = "%s: %s, %s: %s" % (
                self.context.translate(_("Range min")), a['range_min'],
                self.context.translate(_("Range max")), a['range_max'],
            )
            parms.append({'title': _('Specification'), 'value': spec_str,})
            if MinimumResults <= len(dict([(d, d) for d in result_dates])):
                _plotscript = str(plotscript)%{
                    'title': "",
                    'xlabel': self.context.translate(_("Date Sampled")),
                    'ylabel': analyses[service_title][0]['Unit'],
                    'timefmt': localLongTimeFormat,
                    'xtimefmt': "%s\\n%s"%(localTimeFormat,localTimeOnlyFormat),
                    'x_start': "%s 00:00" % min(result_dates).strftime(localTimeFormat),
                    'x_end': "%s 23:59" % max(result_dates).strftime(localTimeFormat),
                    'y_start': max(min(result_values)-5, 0),
                    'y_end': max(result_values)+2,
                }
                _plotscript = _plotscript.encode('utf-8')

                plot_png = plot(plotdata, plotscript=_plotscript, usefifo=False)

                # Temporary PNG data file
                fh,data_fn = tempfile.mkstemp(suffix='.png')
                os.write(fh, plot_png)
                plot_url = data_fn
                self.request['to_remove'].append(data_fn)

                plot_url = data_fn
            else:
                plot_url = ""

            table = {
                'title': "%s: %s" % (
                    self.context.translate(_("Analysis Service")),
                    service_title),
                'parms': parms,
                'columns': ['Request ID',
                            'Analyst',
                            'Result',
                            'Sampled',
                            'Captured'],
                'data': analyses[service_title],
                'plot_url': plot_url,
            }

            self.report_data['tables'].append(table)

        ## footnotes
        if out_of_range_count:
            msgid = _("Analyses out of range")
            translate = self.context.translate
            self.report_data['footnotes'].append(
                "%s %s" % (error_icon, translate(msgid)))
        if in_shoulder_range_count:
            msgid = _("Analyses in error shoulder range")
            self.report_data['footnotes'].append(
                "%s %s" % (warning_icon, translate(msgid)))

        self.report_data['parms'].append(
            {"title": _("Analyses out of range"),
             "value": out_of_range_count})
        self.report_data['parms'].append(
            {"title": _("Analyses in error shoulder range"),
             "value": in_shoulder_range_count})

        title = self.context.translate(header)
        if title_parts:
            title += " (%s)" % " ".join(title_parts)
        return {
            'report_title': title,
            'report_data': self.template(),
        }
