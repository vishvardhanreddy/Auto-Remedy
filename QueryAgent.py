from pymongo import MongoClient
import datetime
from datetime import date
from time import time, sleep
import re
import os
import time
import json
import socket
import sys
import RemedyAgent
import pConnect
from bson.objectid import ObjectId
sys.path.insert(0, '/home/sharishc')
import Signature
import logging





#def memory_issue(matched):

 #   asr9k_host = '8.19.0.15'
  #  connect = pConnect.pConnect(asr9k_host,'Cisco','Cisco') 
    #print matched
    
   # command_output = pConnect.run_commands(connect,
#def remedy_issue(matched):
    
 #   remedy =  matched['remedy_steps']
  #  print remedy[0]['cmd'] 
       
   # if 'sysdb_mc memory increase observed' in remedy[0]['cmd']: 
    #    print 'sysdb_mc  memory increase observed'
     #   memory_issue(matched)


    
def main():
    log_file = "Query_agent.log"
    log_level = logging.DEBUG
    logging.basicConfig(filename=log_file, level=log_level, format='[%(asctime)s] [%(levelname)s] %(module)s::%(funcName)s: %(message)s', datefmt='%a, %b %d %Y %H:%M:%S')
    logging.info('Started Remedy Agent')
    client = MongoClient('localhost', 27017)
    db = client['icair']
    
#Initianlizing Signature
    sign = Signature.Signature()
    #db = Signature.DBAgent(host = 'localhost', port = 27017, dbname = 'icair')
    eventcollection = db.events
    vals = []
    for post in db.event_status.find():
        vals.append(post['event_id'])    	     
    cursor = eventcollection.find({'_id':{'$nin':vals}},tailable=True)
    ra = RemedyAgent.RemedyAgent(sign)

    while cursor.alive:
        try:
	    start = time.clock()
            doc = cursor.next()
            db.event_status.insert({'event_id':doc['_id'],'processed': True})
            print 'New event recieved:', doc
	    is_match, matched = sign.verify_signature(doc)
	    print "signature match clock ends", time.clock() - start
            #matched = db['signatures'].find({"_id":ObjectId('53da716646d99f59f93239aa')})[0]
	    if (is_match):
		print 'Matching Signature found:', matched
                status = True
		status_msg = "Remediation completed successfully"
		print "Remedy Clock starts"
		start = time.clock()
		r_status, r_cmd = ra.process_remedy_steps(matched, doc)
		print "Remedy Clock ends:", time.clock() - start
		if (r_status):
			print "Process post validation steps Clock"
			start = time.clock()
			p_status,p_cmd = ra.process_post_validation_steps(matched, doc)
                        print "Post validation steps Clock ends", time.clock()-start
			if (not p_status):
                                status = False
                                status_msg = "Failed post validation command" +str(p_cmd)
                else:
                        status = False
                        status_msg = "Failed remedy command: " + r_cmd
                print "update status to DB Clock starts"
		start = time.clock()
                ra.update_status_to_db(db, doc['_id'], matched['_id'], doc['hostname'], matched['issue_type'], status, r_cmd, p_cmd)
		print 'Status to DB Clock ends:', status_msg, time.clock()-start
       	    else:
		status_msg = 'Matching Signature not found'
		print 'Status:', status_msg
            #sys.exit()
        except StopIteration:
            sleep(1)

if __name__ == '__main__':
    main()

