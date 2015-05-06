import datetime
import pexpect
import os
import time
import re
class pConnect():
    
    def __init__(self,host,user,pwd):
        self.connectStr = self.connectStr(host,user)
        self.debug = 0
        self.logged_in = 0
        self.host = host
        self.user = user
        self.pwd = pwd
        self.time_out = 60000
        self.xml_end = "]]>]]>"
        self.netconf = 'netconf format'
        self.sent_netconf = 0
        if self.debug:
            print("\nINIT()->pConnect() Called\n")

        ##### New pConnect attribute ( from ASR9kBase class ))
        self.DataDir = "./data/"
        
    def connectStr(self, host, user):
        return("".join(["ssh ",user ,"@",host]))

    def ExPyConnect(self):
        try:
            pEx9k = pexpect.spawn (self.connectStr, timeout=self.time_out, maxread=4096)    #1048567
        except Exception as e:
            print("ERROR !!!! : %s") % ( str(e) )
            return(e)
    
        pEx9k.expect('[p|P]assword:')
        pEx9k.sendline(self.pwd)
        pEx9k.expect(['#',pexpect.EOF])
        pEx9k.sendline("terminal length 0")
        pEx9k.expect(['#',pexpect.EOF])
        pEx9k.sendline("terminal width 512")
        pEx9k.expect(['#',pexpect.EOF])
        self.logged_in = 1
        return (pEx9k)
    
    def end_netconf(self):
        return("""<?xml version="1.0" encoding="UTF-8" ?>
        <rpc message-id="106" xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
            <close-session/>
        </rpc>""")

    ### Log out of Device
    def ssh_logout(self):
        if self.logged_in:
            self.logged_in = int(0)
            self.pEx9k.close()

    def run_commands(self, pConn, cmd, toFile = True):
        """
            generates a netconf query to a Cisco IOS-XR router from 
            a provided list of tags for the XML request
            Params: cmd = Command / XML to process
                    toFile = '' | File name to write out results
        """
        rpc_timeout = int(600)
        sleep_time = .5
        date = datetime.datetime.now().strftime('%Y-%m-%d')
	rpcReturn = ""
        command_type = ""
        cType = "C"
        command_list = dict()
        wait_for = ["#",']]>]]>',self.xml_end, pexpect.EOF, pexpect.TIMEOUT]

        ##### Iterate over inbound list
        ##### Set XML/TXT type for process and return
        ##### Build command_list dict() of Command:Type
        ##### Types : XML ( NetConf ), TXT (Textual), TML (CLI => XML out)

        for c in cmd:
            if self.debug:
                print("Command about to run: %s") % ( c ) 
            if "xml version" in c:
                command_type = "XML"
            elif " xml" in c:
                command_type = "TML"
                self.sent_netconf = 0
            else:
                command_type = "TXT"
                self.sent_netconf = 0

            command_list[c.strip()] = command_type
            if self.debug:
                print("Command Type to run: %s") % ( command_type )

        if self.debug:
            print("Cmd:Type is : %s:%s") % ( c.strip(), command_type )

        if not self.logged_in:
            pEx9k = self.ExPyConnect()

        if self.debug:
            print("Setting NetConf enable VAR:%d") % (self.sent_netconf)
        for cmds, command_type in command_list.iteritems():
            
            if self.debug:
                print("Execute command: %s(type:%s)" ) % ( cmds, command_list[cmds] )
        
            if toFile:
                if not os.path.isdir(self.DataDir):
                    try:
                        myDataDir = os.mkdir(self.DataDir)
                    except Exception as e:
                        return(str(e))

                if "terminal" not in cmds:
                    name_key = "OUTPUT_FILE_NAME"
                    if self.debug:
                        print name_key
                        print("XML through Text output type:%s)") % ( command_type )
                    if "XML" in command_type:
######                        name_key = asr9k.xml_output_name(cmds)
                        ###### NEED FILE NAME CODE #####A
                        name_key = "OUTPUT_FILE_NAME"
                        fname = self.DataDir + name_key.strip() +".xml"
                    else:
######                        name_key = asr9k.output_name(cmds)
                        if "ML" in command_list[cmds]:
                            fname = self.DataDir + name_key.strip() +".xml"
                        else:
                            fname = self.DataDir + name_key.strip() +".txt"
                    if self.debug:
		       	print name_key, fname 
                    cmd_out = open(fname,"w+")
                else:
                    time.sleep(1)
                    print 'sleeping'			

            if command_type == "XML" and not self.sent_netconf:
                if self.debug:
                    print("\n\n\n\n\n##############################################Sending NETCONF !##############################################\n\n\n\n\n")
                pEx9k.sendline(self.netconf)   # run a command
                time.sleep(sleep_time)
                pEx9k.expect(wait_for)
                if self.debug:
                    print("NetConf:%s (%d)") % ( pEx9k.before,self.sent_netconf )
                self.sent_netconf = 1
                if self.debug:
                    print("NetConf:%s") % ( pEx9k.after )

            if self.debug:
                print("What CMD is sent: %s (%s)") % ( cmds, command_list[cmds] )
            pEx9k.sendline(cmds)
            time.sleep(sleep_time)
        
            pEx9k.expect(wait_for)
            cmd_result = str(pEx9k.before)
            print cmd_result
            if "terminal" not in cmds:
                if toFile:
                    xmlregX = re.search('^\<\?xml\s*',cmd_result)
                    if xmlregX:
                        cmd_out.write(cmd_result[xmlregX.start():])
                    else:
                        cmd_out.write(cmd_result.strip())
                
                if toFile:
                    cmd_out.close()
            
        self.logged_in = 0
        if command_type == "XML":
            pEx9k.sendline(self.end_netconf()+self.xml_end)
            time.sleep(sleep_time)
            pEx9k.expect(wait_for)

        pEx9k.close()
        
        return(cmd_result.strip())

