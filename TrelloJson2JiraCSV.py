#! /usr/bin/python

# MIT License

# Copyright (c) 2016 Harry Rose - Semaeopus Ltd.

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


# User Configuration

# maps list names to statuses
STATUSES = {
	'Backlog' : 'To Do',
	'Doing' : 'In Progress',
	'Done' : 'In Review',
	'Test' : 'In Review',
	'Shipit!' : 'Done',
}

STATUS_WHEN_CLOSED = 'Done'
RESOLUTION_WHEN_CLOSED = 'Done'

MAX_LABELS = 8
MAX_ATTACHMENTS = 5
MAX_COMMENTS = 20


# -----------------------------------------------------------------------


import sys
import json
import optparse
import dateutil.parser
from datetime import datetime
from pytz import timezone

# Add an item to the csv row
# Will re-encode to utf8 and wrap quotes around text that contains quotes
def AddCSVItem(str):
	global csvData
	finalStr = str.encode("utf8")
	finalStr = finalStr.replace("\"", "\"\"")
	csvData += "\"{0}\",".format(finalStr)

# Iterate a tasks checklist and generate subtasks
def AddCheckListAsSubTasks(checkListIDs, parentID):
	if not checkListIDs:
		return

	for checkListID in checkListIDs:
		for item in checklistDict[checkListID]:
			checkListName = checklistNames[checkListID]

			status = "Done" if item["state"] == "complete" else "To Do"
			resolution = "Done" if status == "Done" else ""
			created = parse_timestamp(item["id"])
			summary = item["name"]

			if checkListName != 'Checklist':
				summary = checkListName + " - " + summary

			AddIssue("Sub-Task", "", parentID, created, "", status, resolution, summary, "", "", "", None, None)

# End the csv row with a simple newline
def EndCSVLine():
	global csvData
	csvData += "\n"

def format_date(date):
	date = date.astimezone(timezone('US/Pacific'))

	date = "{0:02d}/{1:02d}/{2} {3:02d}:{4:02d}:{5:02d}".format(
		date.day, date.month, date.year,
		date.hour, date.minute, date.second
	)

	return date

def parse_date(datestring):
	date = dateutil.parser.parse(datestring)
	return format_date(date)

def parse_timestamp(string):
	timestamp = int(string[0:8], 16)
	timestamp = datetime.fromtimestamp(timestamp)
	timestamp = timezone('UTC').localize(timestamp)

	return format_date(timestamp)


# Take all the information for an issue and convert it into a csv line
def AddIssue(issuetype, IssueID, ParentID, Created, Updated, Status, resolution, summary, description, attachments, component, labels, comments):
	AddCSVItem(issuetype)
	AddCSVItem(IssueID)
	AddCSVItem(ParentID)
	AddCSVItem(Created)
	AddCSVItem(Updated)
	AddCSVItem(Status)
	AddCSVItem(resolution)
	AddCSVItem(summary)
	AddCSVItem(description)
	AddCSVItem(component)

	# handle attachments
	attachments = attachments or []
	numAttachments = len(attachments)

	if numAttachments > MAX_ATTACHMENTS:
		print("\tError! - {0} Attachments found in \"{1}\". Card will be skipped, only {2} will be handled. Update header line and MAX_ATTACHMENTS value".format(numAttachments, summary, MAX_ATTACHMENTS))
		return 1

	for attachment in attachments:
		AddCSVItem(attachment["url"])

	for _ in xrange(numAttachments, MAX_ATTACHMENTS):
		AddCSVItem("")


	# handle labels
	labels = labels or []
	numLabels = len(labels)

	if numLabels > MAX_LABELS:
		print("\tError! - {0} labels found in \"{1}\". Card will be skipped, only {1} will be handled. Update MAX_LABELS value".format(numLabels, summary, MAX_LABELS))
		return 1

	for label in labels:
		label = label["name"]
		label = label.replace(" ", "_")
		AddCSVItem(label)

	for _ in xrange(numLabels, MAX_LABELS):
		AddCSVItem("")


	# handle comments
	comments = comments or []
	numComments = len(comments)

	if numComments > MAX_COMMENTS:
		print("\tError! - {0} comments found in \"{1}\". Card will be skipped, only {1} will be handled. Update MAX_COMMENTS value".format(numComments, summary, MAX_COMMENTS))
		return 1

	for comment in comments:
		AddCSVItem(comment)

	for _ in xrange(numComments, MAX_COMMENTS):
		AddCSVItem("")


	EndCSVLine()

# Set up the parser for options
parser = optparse.OptionParser(version='TrelloJson2JiraCSV v1.0.0')
parser.add_option('-j', '--json'        , dest="jsonPath"   	, action="store"         , help="The path to the trello json file")

opts, args = parser.parse_args()

if not opts.jsonPath:
	parser.print_help()
	exit(1)

# Set up variables
jsonPath 		= opts.jsonPath
csvPath 		= jsonPath.replace(".json", ".csv")
listDict 		= {}
checklistDict 	= {}
checklistNames 	= {}
commentsForCard = {}
csvData 		= ""
headerLine 		= "issuetype, Issue ID, Parent ID, Created, Modified, Status, Resolution, summary, description, component" + (", attachment" * MAX_ATTACHMENTS) + (", label" * MAX_LABELS) + (", comment" * MAX_COMMENTS) + "\n"

print "Loading " + jsonPath

# Load json data
with open(jsonPath) as data_file:
    data = json.load(data_file)

# Build up our list of list ids to names as trello items only contain ids, we'll use this to map between the two
for list in data["lists"]:
	listDict[list["id"]] = list["name"]

# Same as above to checklists, build up a id to name map
for checkList in data["checklists"]:
	checklistDict[checkList["id"]] = checkList["checkItems"]
	checklistNames[checkList["id"]] = checkList["name"]

# Dump some useful information about the board
print("Trello Board: {0} ({1})".format(data["name"], data["url"]))
print("\t{0} lists found".format(len(data["lists"])))
print("\t{0} cards found".format(len(data["cards"])))
print("\t{0} checklists found".format(len(data["checklists"])))
print("\t{0} labels found".format(len(data["labels"])))


# extract comments where possible
for action in data["actions"]:
	action_type = action["type"]

	if action_type == "commentCard":
		card_id = action["data"]["card"]["id"]
		text = action["data"]["text"]
		author = action["memberCreator"]["username"]
		date = parse_date(action["date"])

		text = u"{0}; {1}; {2}".format(date, author, text)
		comments_list = commentsForCard.get(card_id)

		if not comments_list:
			comments_list = []
			commentsForCard[card_id] = comments_list

		comments_list.append(text)


# Core loop
for card in data["cards"]:
	card_id 	= card["id"]
	listName 	= listDict[card["idList"]]

	# Grab all the core data we'll need from the card
	issueID 	= card_id
	cardName 	= card["name"].strip()
	shortURL 	= card["shortUrl"].strip()
	cardDesc 	= card["desc"].strip()
	labels 		= card["labels"]
	attachments = card["attachments"]
	created		= parse_timestamp(card_id)
	updated		= parse_date(card["dateLastActivity"])
	comments	= commentsForCard.get(card_id)

	if card["closed"]:
		status = STATUS_WHEN_CLOSED
		resolution = RESOLUTION_WHEN_CLOSED
	else:
		status = STATUSES.get(listName)
		resolution = ""

	if not status:
		status = "To Do"
		component = listName
	else:
		component = ""


	# Append URL to description
	cardDesc += "\n\n" if cardDesc else ""
	cardDesc += "Generated from: " + shortURL

	AddIssue("task", issueID, "", created, updated, status, resolution, cardName, cardDesc, attachments, component, labels, comments)
	AddCheckListAsSubTasks(card["idChecklists"], issueID)

# Write out csv file
with open(csvPath, "w") as csvFile:
	csvFile.write(headerLine)
	csvFile.write(csvData)
	print("")
	print("\tData written to {0}".format(csvPath))
	print("\tSimpleDateFormat is: dd/MM/yyyy HH:mm:ss")
