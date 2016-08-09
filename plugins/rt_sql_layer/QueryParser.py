# -*- coding: utf-8 -*-
"""
/***************************************************************************
Name                 : RT Sql Layer - Query Parser
Description          : Parse a query and return its parts
Date                 : 03/Apr/2010 
Copyright            : (c) 2010 by Giuseppe Sucameli (Faunalia)
Email                : brush.tyler@gmail.com 
 ***************************************************************************
Developed by Giuseppe Sucameli (brush.tyler@gmail.com) 
for Faunalia (http://www.faunalia.it) with funding from Regione Toscana - 
Sistema Informativo per la Gestione del Territorio e dell'Ambiente [RT-SIGTA]. 
For the project: "Sviluppo di prodotti software GIS open-source basati 
sui prodotti QuantumGIS e Postgis" (CIG 037728516E)
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

from PyQt4.QtCore import *
from PyQt4.QtGui import *

class QueryParser:

	DEBUG = False
	KEYWORDS = [' SELECT ', ' FROM ', ' WHERE ', ' GROUP BY ', ' HAVING ', ' ORDER BY ', ' LIMIT ']
	WORDBOUNDARY = [';']
	QUOTES = ["'", '"']
	COMMENTS = ['--', '/*']
	PARENTHESIS = ['(', '[', '{']

	def __init__(self, query = QString(), splittingKeys = None, parseNow = True, sanitize = False):
		self.query = QString(query).trimmed()
		self.parts = QStringList()
		self.valid = None
		self.sanitize = sanitize

		if splittingKeys == None:
			splittingKeys = self.KEYWORDS
		self.splittingKeys = splittingKeys

		rxKeysStr = self.escape( self.splittingKeys )
		rxKeysStr += '|%s' % self.escape( self.WORDBOUNDARY )
		rxKeysStr += '|%s' % self.escape( self.QUOTES )
		rxKeysStr += '|%s' % self.escape( self.COMMENTS )
		rxKeysStr += '|%s' % self.escape( self.PARENTHESIS )

		self.regexStr = "(?=\\b)*(?:%s)(?=\\b)*" % rxKeysStr

		if parseNow:
			self.valid = self.parse()

	def parseQuotedString(self, query = "", pos = 0, quote = '"'):
		rx = QRegExp( "%(q)s[^%(q)s]*(?:%(q)s{2}[^%(q)s]*)*%(q)s" % { "q" : QRegExp.escape(quote) } )
		start = rx.indexIn(query, pos)
		if start < 0:
			return -1

		length = len(quote)-1 + rx.matchedLength()
		end = start + length - 1
		if self.DEBUG:
			print "quoted string from", start, "to", end, ":", query.mid(start, length)
		return end

	def parseComment(self, query = "", pos = 0, comment = '--'):
		start = query.indexOf(comment, pos)
		if start < 0:
			return -1

		if comment == '--':
			rx = QRegExp( '[^\n]*' )
			pos = rx.indexIn(query, start+1)

			length = len(comment)-1 + rx.matchedLength()
			end = start + length - 1
			if self.DEBUG:
				print "comment from", start, "to", end, ":", query.mid(start, length)

			if self.sanitize:
				query.remove(start, length)
				end = start
			return end

		level = 1
		if comment == '/*':
			closed = '*/'

		rxStr = self.escape( ['/*', '*/'] )
		rx = QRegExp( rxStr )
		pos = rx.indexIn(query, start+1)

		while pos != -1:
			found = rx.cap(0)
			pos = rx.pos(0)

			if self.DEBUG:
				print "  "*(level+1) + "found:", found, "\tpos:", pos

			if found == comment:
				level += 1
			elif found == closed:
				level -= 1
			else:
				break

			if level == 0:
				if self.sanitize:
					length = pos + len(found) - start
					query.remove(start, length)
					pos = start
				return pos

			pos = rx.indexIn(query, pos+1)

		if self.DEBUG:
			print "ERROR on parseComment %s: exit from while with level = %d" % (comment, level)
		return -1

	def parseParenthesis(self, query = "", pos = 0, par = '('):
		start = query.indexOf(par, pos)
		if start < 0:
			return -1

		level = 1
		if par == '{':
			closed = '}'
		elif par == '[':
			closed = ']'
		else:
			closed = ')'

		rxStr = '[^%s]*(.)' % self.escape("{}[]()\"\'")
		rx = QRegExp( rxStr )
		pos = rx.indexIn(query, start+1)

		rxStrComment = '--|/*'
		rxComment = QRegExp( rxStrComment )
		posComment = rxComment.indexIn(query, start+1)

		if posComment < pos:
			found = rxComment.cap(0)
			pos = rxComment.pos(0)

			pos = self.parseComment(query, pos, found)
			if pos == -1:
				return -1

			rxStr = '[^%s]*(.)' % QRegExp.escape("()\"\'")
			rx = QRegExp( rxStr )
			pos = rx.indexIn(query, end+1)

		while pos != -1:
			found = rx.cap(1)
			pos = rx.pos(1)

			if self.DEBUG:
				print "  "*(level+1) + "found:", found, "\tpos:", pos

			if found == par:
				level += 1
			elif found == closed:
				level -= 1
			elif found in self.QUOTES:
				pos = self.parseQuotedString(query, pos, found)
				if pos == -1:
					break
			elif found in self.PARENTHESIS:
				pos = self.parseParenthesis(query, pos, found)
				if pos == -1:
					break
			else:
				break

			if level == 0:
				return pos

			pos = rx.indexIn(query, pos+1)

		if self.DEBUG:
			print "ERROR on parseParenthesis %s: exit from while with level = %d" % (par, level)
		return -1

	def parse(self, query = None):
		if query == None:
			query = self.query

		initPos = 0
		pos = 0

		rxKeys = QRegExp( self.regexStr )
		rxKeys.setCaseSensitivity(Qt.CaseInsensitive)

		pos = rxKeys.indexIn(query, initPos)
		while pos != -1:
			found = rxKeys.cap(0).toUpper().trimmed()

			if self.DEBUG:
				print "found:", found, "\tinitPos:", initPos, "\tpos:", pos

			if found in self.PARENTHESIS:
				pos = self.parseParenthesis(query, pos, found)
				if pos == -1:
					return False
			elif found in self.QUOTES:
				pos = self.parseQuotedString(query, pos, found)
				if pos == -1:
					return False
			elif found in self.COMMENTS:
				pos = self.parseComment(query, pos, found)
				if pos == -1:
					return False
			else:
				if pos != initPos:
					matched = query.mid( initPos, pos - initPos ).trimmed()
					if not matched.isEmpty():
						self.parts << matched

					if self.DEBUG:
						print "appended string from", initPos, "to", pos-1, ":", matched

				if found == ';':
					if self.sanitize:
						query.truncate(pos)
					return True

				initPos = pos

			pos = rxKeys.indexIn(query, pos + 1)

		rest = query.mid( initPos ).trimmed()
		if not rest.isEmpty():
			self.parts << rest
			if self.DEBUG:
				print "appended string from", initPos, "to", query.length(), ":", rest

		return True

	def indexOfPart(self, part):
		part = QString( part ).trimmed()
		escaped = self.escape( part )
		regex = QRegExp( "^" + escaped + "\\b+" )
		regex.setCaseSensitivity( Qt.CaseInsensitive )

		for i, p in enumerate(self.parts):
			if p.contains( regex ):
				return i

		return -1

	def getPart(self, part):
		index = self.indexOfPart( part )
		if index < 0:
			return None

		return self.parts[index]

	@classmethod
	def escape(self, values):
		if isinstance(values, list) or isinstance(values, tuple):
			rxStr = QString()
			for v in values:
				rxStr += "|%s" % self.escape( v )
			return rxStr.mid(1)

		return QRegExp.escape( values ).replace( " ", "(?:\\b|\\s)+" )


query = """
select users.user_id, users.email, count(*) as how_many, max(classified_ads{"((("([')'])}(("(((")).posted) as how_recent /* "(( */
from users, classified_ads
where users.user_id = classified_ads.user_id
group by users.user_id, users.email
order by how_recent desc, how_many desc;
"""

if __name__ == "__main__":
	import sys
	if len(sys.argv) < 2:
		print "No query passed as argument. Used the test query"
	else:
		query = sys.argv[1]

	QueryParser.DEBUG = True
	parser = QueryParser(query)
	for p in parser.parts:
		print "1> ", p
		for subp in QueryParser(p, [',', '=']).parts:
			print "  2> ", subp
