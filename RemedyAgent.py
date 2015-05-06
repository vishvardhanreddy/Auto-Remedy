import sys
sys.path.insert(0, '/home/sharishc')
import logging
import Signature
from bson.objectid import ObjectId
import re
import pConnect
import datetime

class RemedyAgent:
        def __init__(self, signature):
                # Add any 'cmd' : 'parser' routine mapping, if required
                logging.info('Initializing Remedy Agent')
                self.parsers = {'show process memory | in sysdb_mc' : 'get_process_memory' }
                self.signature = signature

        def get_process_memory(self, output):
                logging.info('Getting process memory')

                mem_regex = re.compile("(\d+)\s+\d+\s+\d+\s+\d+\s+(\d+)\s+\S+")
                for line in output.split("\n"):
                        m = mem_regex.match(line)
                        if (m):
                                return m.group(2)
                return None

        def execute_command(self, cmd, host, user='cisco', password='cisco'): 
                logging.info("Executing command '%s' on host: '%s'", cmd, host)
                
                # hookup pconnect run command routine here
                pConn = pConnect.pConnect(host,user,password)
		output = pConn.run_commands(pConn, [cmd], toFile = True)
                #output = ""
                return output

	def process_steps(self, steps, event):
		p_cmds = []
		failed = False
		for val in steps:
			cmd = val['cmd']
			p_cmd = {"cmd":cmd}

			logging.info("Executing command: '%s'", cmd)

			output = self.execute_command(cmd, event['hostname'], 'cisco', 'cisco')
			p_cmd['output'] = output
			p_cmd['status'] = "Success"
		
			if ('expected_output' in val and output):
				logging.info("Got output: '%s'", output)

				if ( cmd in self.parsers and hasattr(self, self.parsers[cmd]) ):
					# if there is parser defined, call that and get the parsed 'output'
					# else, use the 'output' got from 'execute_command'
					method = getattr(self, self.parsers[cmd])
					output = method(output)
					p_cmd['output'] = output
					logging.info("Parsed output: '%s'", output)

				if (val['expected_output']):
					p_cmd['signature_cmp'] = 'output' + " '" + val['expected_output']['cmp'] + "' " + val['expected_output']['value']
					logging.info("Signature value to be compared: '%s'", val['expected_output']['value'])
					value_to_cmp = self.signature.resolve_var(event, val['expected_output']['value'])
					if (not value_to_cmp):
						logging.error("Failed to resolve variable: '%s'", val['expected_output']['value'])
					else:
						p_cmd['signature_cmp_val'] = output + " '" + val['expected_output']['cmp'] + "' " + str(value_to_cmp)
				
					logging.error("Comparing: '%s' '%s' '%s'", output, val['expected_output']['cmp'], value_to_cmp)
	
					status = self.signature.compare(str(value_to_cmp), output, val['expected_output']['cmp'])
					if (not status):
						logging.error("Failed to execute command")
						p_cmd['status'] = "Failed"
						failed = True
			p_cmds.append(p_cmd)
			if (failed):
				return False, p_cmds

			logging.debug("Command executed successfully")

		return True, p_cmds



        def process_remedy_steps(self,sign, event):
                logging.info("Processing remedy steps")
                steps = sign['remedy_steps']
                return self.process_steps(steps, event)

        def process_post_validation_steps(self, sign, event):
                logging.info("Processing post validation steps")
                steps = sign['post_validation_steps']
                return self.process_steps(steps, event)

        def update_status_to_db (self, db, event_id, signature_id, event_hostname, signature_type, status, r_cmd, p_cmd):
                logging.info("Updating remedy status into db")
		collection = db["remedy"]
		new_obj = {"event_id":event_id, "signature_id":signature_id, "hostname":event_hostname, "signature_type":signature_type, "status":status, "remedy_steps":r_cmd, "post_validation_steps":p_cmd, "createdtime":datetime.datetime.utcnow()}
		return collection.insert(new_obj)
		#db.db_insert('remedy', {"event_id":event_id, "signature_id":signature_id, "status":status, "status_message":status_msg})
def main():
        log_file = "remedy_agent.log"
        log_level = logging.DEBUG

        logging.basicConfig(filename=log_file, level=log_level, format='[%(asctime)s] [%(levelname)s] %(module)s::%(funcName)s: %(message)s', datefmt='%a, %b %d %Y %H:%M:%S')
        logging.info('Started Remedy Agent')

        sign = Signature.Signature()
        db = Signature.DBAgent(host="localhost", port=27017, dbname='icair')
        ra = RemedyAgent(sign)


        # Below steps should be for each new even:w
        # The logic should:
        # foreach new event, call sign.verify_signature(event)
        # if there 'is_match', then execute 'remedy_steps' and 'post_validation_steps' (if available)
        # for both the 'remedy_steps' and 'post_validation_steps', validate the result with expected_output
        # finally update the status in the db

        # This is for unit test only
        #event = db.db_find('events',{"_id":ObjectId("53dfd381414e7304b364fb47")})
        event = { "_id" : ObjectId("53da64f4414e736962c3035a"), "hostname" : "PR-ASR9K-BNG-1", "log" : { "timestamp" : "Thu Jul 31 05:46:08 UTC 2014", "message" : "Configuration committed by user 'cisco'. Use 'show configuration commit changes 1000000341' to view the changes. ", "processor" : "RP/0/RSP0/CPU0" }, "install_summary" : [ "disk0:asr9k-mini-px-4.3.4", "disk0:asr9k-bng-px-4.3.4", "disk0:asr9k-9000v-nV-px-4.3.4", "disk0:asr9k-k9sec-px-4.3.4", "disk0:asr9k-mgbl-px-4.3.4", "disk0:asr9k-mpls-px-4.3.4", "disk0:asr9k-mcast-px-4.3.4", "disk0:asr9k-doc-px-4.3.4", "disk0:asr9k-optic-px-4.3.4", "disk0:asr9k-services-px-4.3.4", "disk0:asr9k-video-px-4.3.4", "disk0:asr9k-fpd-px-4.3.4" ], "issue_id" : "CSCuo10444", "version" : { "osversion" : "4.3.4", "os" : "IOS XR", "chassis" : "ASR-9006 AC", "memory" : "12582912K" }, "createdtime" : "2014-07-31T15:47:00.198Z", "log_file" : "/var/log/autoremedy/CSCuo10444/PR-ASR9K-BNG-1/issue_12434312801406785571.out", "after" : { "timestamp" : "Thu Jul 31 05:46:13.142 UTC 2014", "JID" : "419", "heap_size" : "8900608" }, "before" : { "before4" : { "timestamp" : "Thu Jul 31 05:46:13.142 UTC 2014", "JID" : "419", "heap_size" : "7800608" }, "before5" : { "timestamp" : "Thu Jul 31 05:46:13.142 UTC 2014", "JID" : "419", "heap_size" : "8600608" }, "before1" : { "timestamp" : "Thu Jul 31 05:46:13.142 UTC 2014", "JID" : "419", "heap_size" : "10608" }, "before2" : { "timestamp" : "Thu Jul 31 05:46:13.142 UTC 2014", "JID" : "419", "heap_size" : "6600608" }, "before3" : { "timestamp" : "Thu Jul 31 05:46:13.142 UTC 2014", "JID" : "419", "heap_size" : "7100608" } } }

        is_match, matched = sign.verify_signature(event)
        if (is_match):
                status = True
                status_msg = "Remediation completed successfully"

                r_status,r_cmd = ra.process_remedy_steps(matched, event)
                if (r_status):
			p_status,p_cmd = ra.process_post_validation_steps(matched, event)
                        if (not p_status):
                                status = False
                                status_msg = "Failed post validation command" + p_cmd
                else:
                        status = False
                        status_msg = "Failed remedy command: " + r_cmd
                ra.update_status_to_db(db, event['_id'], matched['_id'], status, status_msg)

        logging.info('Remedy Agent stopped')


if __name__ == '__main__':
        main()

                                                                                                                                                                         

                  
