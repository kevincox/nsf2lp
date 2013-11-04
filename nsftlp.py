#/usr/bin/env python3

'''
	Converts Sourceforge JSON bugs to Launchpad XML.
'''

import os, sys, json, re
import time
import subprocess
import datetime
import urllib, urllib.parse, urllib.request
import base64
from xml.sax.saxutils import escape

statusconv = {
	"abandoned":    "INCOMPLETE",
	"accepted":     "TRIAGED",
	"fixed":        "FIXRELEASED",
	"non-issue":    "INVALID",
	"open":         "NEW",
	"upstream":     "CONFIRMED",
	"wont-fix":     "WONTFIX",
	"would-accept": "CONFIRMED",
}

sevconv = {
	"critical": "CRITICAL",
	"high":     "HIGH",
	"low":      "LOW",
	"medium":   "MEDIUM",
}

def prettydate(date):
	return subprocess.check_output(['date', '-ud', date, '+%FT%H:%M:%S']).decode()[:-1]

IDENT_RE = re.compile('([^a-z0-9+.-]|^[+.-])')
def ident(s):
	return IDENT_RE.sub('', s)

if len(sys.argv) < 3:
	print('Usage: nsf2lp.py <sf json> <lp output>')
	exit(1)

with open(sys.argv[1], 'r') as f:
	sf = json.loads(f.read())

lp = open(sys.argv[2], 'w')

lp.write("""<?xml version="1.0"?>
<launchpad-bugs xmlns="https://launchpad.net/xmlns/2006/bugs">
""")

for t in sf['tickets']:
	lp.write('''<bug xmlns="https://launchpad.net/xmlns/2006/bugs" id="{bid}">
	<private>False</private>
	<security_related>False</security_related>
	<datecreated>{date}</datecreated>
	<title>{title}</title>
	<description>{desc}</description>
	<reporter name="{rname}" email="{rname}@users.sourceforge.net">{rname}</reporter>
	<status>{status}</status>
	<importance>{priority}</importance>
	<subscriptions>
		<subscriber email="{rname}@users.sourceforge.net">{rname}</subscriber>
	</subscriptions>
	<tags>'''.format(
		bid = t['ticket_num'],
		date = prettydate(t['created_date']),
		title = escape(t['summary']),
		desc = escape(t['description']),
		rname = ident(t['reported_by']),
		status = statusconv[t['status']],
		priority = sevconv[t['custom_fields'].get('_severity', 'medium')],
	))
	for l in t['labels']:
		lp.write("\n\t\t<tag>{}</tag>".format(ident(l)))
	lp.write('''
	</tags>''')
	atch = t['attachments']
	if atch:
		t['discussion_thread']['posts'].insert(0, {
			"author": t['reported_by'],
			"timestamp": prettydate(t['created_date']),
			"text": "",
			"attachments": atch,
		})
	for c in t['discussion_thread']['posts']:
		lp.write('''
	<comment>
		<sender name="{pname}" email="{pname}@users.sourceforge.net">{pname}</sender>
		<date>{date}</date>
		<text>{text}</text>'''.format(
			pname = ident(c['author']),
			date = prettydate(c['timestamp']),
			text = escape(c['text']),
		))
		
		for a in c['attachments']:
			r = urllib.request.urlopen(a['url'])
			d = r.read()
			lp.write('''
		<attachment>
			<type>UNSPECIFIED</type>
			<filename>{bname}</filename>
			<title>{bname}</title>
			<mimetype>{mime}</mimetype>
			<contents>{content}</contents>
		</attachment>'''.format(
			bname = urllib.parse.unquote(os.path.basename(a['url'])),
			mime = r.getheader("Content-Type", "application/octet-stream"),
			content = base64.b64encode(d).decode()
		))
		
		lp.write('''
	</comment>''')
	lp.write('''
</bug>
''')

lp.write("</launchpad-bugs>\n")

