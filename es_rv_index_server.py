#!/usr/bin/env python

# Caches Google Spreadsheets on-demand in Python
# POST it a payload of the Spreadsheet key
# Expects to read a configuration file, conf.yaml

import sys
import urllib2
import json
import dateutil.parser
from elasticsearch import Elasticsearch
import cgi

import cgitb
# to log errors to html pages in this specified directory
cgitb.enable(False, '/Users/Shared/errors')

# Now also make a connection to Elasticsearch
es = Elasticsearch()
es_index_name = 'rendezvous_test'
es_doc_type = 'talks'
# TODO: need mapping

# Create the index
if not es.indices.exists( index = es_index_name ):
    es.indices.create( index = es_index_name )
    # es.indices.put_mapping(index=es_index_name, doc_type=es_doc_type, body=case_mapping)

# Logging
log_f = open('/Users/Shared/gs_changes_server.log', 'w')

form = cgi.FieldStorage()
key = form.getvalue("key")
modified_sheet_name = form.getvalue("sheet_name")
# log_f.write(key + " __ " + modified_sheet_name + '\n')

sheets_json_url = "https://spreadsheets.google.com/feeds/worksheets/"+key+"/public/basic?alt=json"
sheets_json = urllib2.urlopen(sheets_json_url).read()
sheets_dict = json.loads(sheets_json)

for entry in sheets_dict['feed']['entry']:
    sheet_name = entry['title']['$t']
    sheet_id = urllib2.urlparse.urlparse(entry['id']['$t']).path.split('/')[-1]
    if sheet_name == modified_sheet_name:
        sheet_json_url = "https://spreadsheets.google.com//feeds/list/"+key+"/"+sheet_id+"/public/values?alt=json"
        sheet_json = urllib2.urlopen(sheet_json_url).read()
        sheet_dict = json.loads(sheet_json)
        
        for row in sheet_dict['feed']['entry']:
            doc = {}
            doc_id = None
            
            doc['gs_link'] = row['id']['$t']
            column_names = [k for k in row.keys() if k.startswith('gsx$')]
            for col_name in column_names:
                real_name = col_name[4:].lower().replace(' ','_')
                doc[real_name] = row[col_name]['$t']
                # Using date as unique ID for talk, but changing to YYYY-MM-DD format
                if real_name == 'date':
                    date_str = row[col_name]['$t']
                    dd = dateutil.parser.parse(date_str)
                    doc_id = dd.date().isoformat()
            
            # store talk in ES
            log_f.write(doc_id + '\n' + str(doc) + '\n')
            res = es.index(index=es_index_name, doc_type=es_doc_type, id=doc_id, body=doc)
            log_f.write(str(res) + '\n')
                    
print "Content-type:text/html\r\n\r\n"
print '<html>'
print '<head>'
print '<title>Success</title>'
print '</head>'
print '<body>'
print '<h2>Execution successful</h2>'
print '</body>'
print '</html>'

log_f.close()