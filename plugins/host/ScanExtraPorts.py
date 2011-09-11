from core import conf, utils
import re, httplib, sys

"""
Plugin : ScanExtraPorts
Description :
	Scan for other HTTP services on the same host.
	If any ports are open, they could serve for future scans with tachyon.
"""

__author__ =  'h3xStream'
__version__=  '1.0'

# Ports are structure with tuples ([ports], description)

COMMON_HTTP_PORTS= [
	([80],   "Default port"),
	([81,82,8080,8081,8090], 
	         "Common alternate port"),
	
	([591],  "FileMaker"),
	([593],  "Microsoft Exchange Server RPC"),
	([4848], "Glassfish admin port"),
	([8000], "Django default port"),
	([3100], "Tatsoft"),
	([3101], "BlackBerry Enterprise Server"),
	([3128], "Squid Web caches"),
	([4567], "Sinatra default port"),
	([4711], "McAfee Web Gateway 7"),
	([5104], "IBM Tivoli Framework NetCOOL/Impact"),
	([5800,5801,5802],
	         "VNC Web interface"),
	([7001], "BEA WebLogic Server"),
	([8280], "Apache Synapse"),
	([8887], "HyperVM"),
	([8888], "Common alternate port / GNUmp3d / LoLo Catcher / AppEngine development"),
	([9990], "JBoss admin port"),
	([10041],"WebSphere Portal administration"),
	
	([8008], "IBM HTTP Server Admin"),
	([9060], "WebSphere admin console"),
	([9080], "WebSphere http"),
	
	([7777], "Oracle HTTP Server"),
	([7779], "Oracle9iAS Web Cache"),
	([8007], "Oracle HTTP Server Jserv")
	]

COMMON_HTTPS_PORTS= [
	([443],  "Default port"),
	
	([981],  "Check Point FireWall-1 management"),
	([987],  "Windows SharePoint Services"),
	([1311], "Dell OpenManage"),
	([1920], "IBM Tivoli Monitoring Console"),
	([4712], "McAfee Web Gateway 7"),
	([7000], "Vuze Bittorrent tracker"),
	([7002], "BEA WebLogic Server"),
	([8243], "Apache Synapse"),
	([8888], "HyperVM"),
	
	([9043], "WebSphere admin console"),
	([9443], "WebSphere https"),
	
	([4443], "Oracle HTTP Server"),
	([4444], "Oracle9iAS Web Cache")
	]

# Sources for the common ports list
# 1. http://www.red-database-security.com/whitepaper/oracle_default_ports.html
# 2. http://publib.boulder.ibm.com/infocenter/wasinfo/v6r0/index.jsp?topic=%2Fcom.ibm.websphere.express.doc%2Finfo%2Fexp%2Fae%2Frins_portnumber.html
# 3. http://en.wikipedia.org/wiki/List_of_TCP_and_UDP_port_numbers

LOG_PREFIX = " - ScanExtraPorts Plugin: "

def logInfo(message,prefix=LOG_PREFIX):
	utils.output_info("%s%s" % (prefix,message))

def logDebug(message,prefix=LOG_PREFIX):
	utils.output_debug("%s%s" % (prefix,message))

def logRewrite(message):
	sys.stdout.write("\r%s" % (message))

def clearLine():
	sys.stdout.write("\r");


def genericScan(listPortsInfos,host,skipPort=80,visitor= lambda host,port: (),results=[],label=""):
	"""Generic Scan loop that take a visitor to do the actual connection.
	
	Arguments:
	listPortsInfos -- List of ports info (COMMON_HTTP_PORTS, COMMON_HTTPS_PORTS)
	host -- Remote host
	skipPort -- The plugin will not probe the port of the current scan for files.
	visitor -- Function that will try to connect to a port and throw an exception if it failed.
	httpResults -- Results are append to this list
	"""
	i=0
	total=len(listPortsInfos)
	
	for portGroupInfo in listPortsInfos :
		i+=1
		
		for scanPort in portGroupInfo[0]:
			
			if scanPort == skipPort:
				continue #Avoid suggesting the port initially specified
			
			#Testing if the the port is open and is a HTTP service.
			portOpen = False
			
			logRewrite("(%i/%i) Scanning %s port %i " % (i,total,label,scanPort))
			
			try:
				visitor(host,scanPort)
				
				portOpen = True
			except:
				pass
			
			if portOpen :
				results.append((scanPort,portGroupInfo[1],label))
	
	clearLine(); #Clear the loading info (Scanning..)

def execute():
	
	logInfo("Starting a quick port scan")
	
	re_host = re.search('(https://|http://)([^/:]+)(:([0-9]+))?',conf.target_host)
	
	currentHost = re_host.group(2)
	
	#Extract port otherwise default port
	currentPort = int(re_host.group(4)) if re_host.group(4) else 80 \
		if conf.target_host.startswith('http://') else 443
	
	
	#List containing tuples (port,description,label=(HTTP|HTTPS))
	globalResults = []
	
	#Scanning for HTTP services
	
	def httpVisitor(host,port):
		conn = httplib.HTTPConnection(host,port,timeout=2)
		conn.request("GET", "/"); #Response is ignore
		conn.close()
	
	genericScan(COMMON_HTTP_PORTS,currentHost,currentPort,httpVisitor,globalResults,"HTTP")
	
	#Scanning for HTTPS services
	
	def httpsVisitor(host,port):
		conn = httplib.HTTPSConnection(host,port,timeout=2)
		conn.request("GET", "/"); #Response is ignore
		conn.close()
	
	genericScan(COMMON_HTTPS_PORTS,currentHost,currentPort,httpsVisitor,globalResults,"HTTPS")
	
	#Printing the final results
	
	logInfo("%i extra port(s) open" % (len(globalResults)));
	
	for res in globalResults:
		logInfo("Port %i is open. | %s (%s)" % res,"")


#For testing purpose
if __name__ == "__main__":
	conf.target_host = 'http://localhost/'
	execute()