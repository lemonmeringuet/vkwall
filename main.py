#!/usr/bin/env python2

"""Save everything from your VK wall"""

__author__	  = "Rast"

import logging
import argparse
import json
import urllib2
from urllib import urlencode
import json
import os
import os.path
import getpass
import sys
import re
from time import sleep
from collections import defaultdict

app_id = "3713087"
access_rights = ["wall", 
				]

def arg_parse():
	parser = argparse.ArgumentParser()
	parser.add_argument("-d", "--dir",
						type = str,
						help = "Directory to store dumped data",
						dest = "directory",
						required = False,
						default = ".")
	parser.add_argument("-i", "--id",
						type = int,
						help = "User ID to dump. To dump a group, specify its ID with '-' prefix",
						metavar = "USER_ID|-GROUP_ID",
						dest = "id",
						required = False,
						default = 0)
	parser.add_argument("-t", "--token",
						type = str,
						help = "Access token, generated by VK for session",
						dest = "token",
						required = False,
						default = "")
	parser.add_argument("-a", "--app_id",
						type = int,
						help = "Your application ID to access VK API",
						dest = "app_id",
						required = True)
	parser.add_argument("-s", "--start",
						type = int,
						help = "Post number to start from (first is 1)",
						dest = "start",
						required = False,
						default = 1)
	parser.add_argument("-e", "--end",
						type = int,
						help = "Post number to end at (0 = all posts)",
						dest = "end",
						required = False,
						default = 0)
	parser.add_argument("-v", "--verbose", action="store_true",
						help="Print more info to STDOUT while processing")

	args = parser.parse_args()
	return args

def auth(args):
	"""Interact with user to get access_token"""

	url = "https://oauth.vk.com/oauth/authorize?" + \
	"redirect_uri=https://oauth.vk.com/blank.html&response_type=token&" + \
	"client_id=%s&scope=%s&display=wap" % (args.app_id, ",".join(access_rights))

	print("Please open this url:\n\n\t{}\n".format(url))
	raw_url = raw_input("Grant access to your acc and copy resulting URL here: ")
	res = re.search('access_token=([0-9A-Fa-f]+)',raw_url,re.I)
	if res is not None:
		return res.groups()[0]
	else:
		return None

def call_api(method, params, token):
	if isinstance(params, list):
		params_list = [kv for kv in params]
	elif isinstance(params, dict):
		params_list = params.items()
	else:
		params_list = [params]
	params_list.append(("access_token", token))
	url = "https://api.vk.com/method/%s?%s" % (method, urlencode(params_list)) 
	result = json.loads(urllib2.urlopen(url).read())
	if result.has_key(u'error'):
		raise RuntimeError("API call resulted in error ({}): {}".format(result[u'error'][u'error_code'], result[u'error'][u'error_msg']))

	if not result.has_key(u'response'):
		raise RuntimeError("API call result has no response")
	else:
		return result[u'response']

def process_post(loud, number, post_data):
	"""Post-processing :)"""
	if loud:  # print info table
		# print header
		if number % 10 == 0 or number == 1:
			print "{:^4} {:^6} {:^12} {:^12} {:^12} {:^12} {:^12} {:^12} {:^12}".format(
													"num", 'id', 'to_id',
													'from_id', 'date', 'signer_id',
													'copy_owner_id', 'copy_post_id', 'len(copy_text)'
												)

		data = defaultdict(lambda: "-", post_data[1])
		print "{:^4} {:^6} {:^12} {:^12} {:^12} {:^12} {:^12} {:^12} {:^12}".format(
													number, data['id'], data['to_id'],
													data['from_id'], data['date'], data['signer_id'],
													data['copy_owner_id'], data['copy_post_id'], len(data['copy_text'])
												)
	
	"""
		parse post - store useful data:
			id (of the post)
			to_id (always user?)
			from_id (post author)
			date (unix timestamp, convert to time)
			text (unicode)
			attachments: (multimedia!)
				type (type name)
				<type>:
					...
			comments: (obvious)
				count
				can_post (0|1)
			likes: (people list)
				count
				user_likes (if user liked it)
				can_like
				can_publish
			reposts: (people list)
				count
				user_reposted (0|1)
			signer_id (if group, and if post is signed)
			copy_owner_id (if repost, author's id)
			copy_post_id (if repost, original post id)
			copy_text (if repost, user's response)


	"""

def main():
	"""Main function"""

	args = arg_parse()
	args.token = auth(args) if args.token is None else args.token
	if args.token is None:
		raise RuntimeError("Access token not found")
	
	#determine posts count
	response = call_api("wall.get", [("owner_id", args.id), ("count", 1), ("offset", 0)], args.token)
	count = response[0]
	logging.info("Total posts: {}".format(count))
	if args.end == 0:
		args.end = count
	if not 0 < args.start < count+1:
		raise RuntimeError("Start argument not in valid range")
	if not args.start <= args.end <= count:
		raise RuntimeError("End argument not in valid range")
	logging.info("Parsing posts from {} to {}".format(args.start, args.end))
	args.end += 1  # for xrange() generator
	print len(xrange(args.start, args.end))
	total = args.end - args.start
	for x in xrange(args.start, args.end):
		if x % 5 == 0:
			sleep(1)
			print("Done: {:.2%} ({})".format(float(x)/total, x))
		post = call_api("wall.get", [("owner_id", args.id), ("count", 1), ("offset", x)], args.token)
		process_post(args.verbose, x, post)
	print("Done: {:.2%} ({})".format(float(x)/total, x))

if __name__ == '__main__':
	ok = False
	try:
		logging.basicConfig(format = u"""%(filename)s[LINE:%(lineno)d]#%(levelname)-8s [%(asctime)s] %(message)s""",
							level = logging.DEBUG,
							filename = u'report.log')
		logging.info("Start")
		main()
		logging.info("End")
		ok = True
	except KeyboardInterrupt:
		logging.critical("Interrupted by keystroke")
		print "\nWhy, cruel world?.."
	finally:
		if not ok:
			logging.critical("Fail")