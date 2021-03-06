import os
import re
import socket
import datetime
import json
import urllib2
import ssl
import itertools
import logging
import fabric_access
import interfaces
from multiprocessing.dummy import Pool as ThreadPool
import program_globals

def multithreading_request(func, maplist, threadpoolnum=10, parameters=None):
    pool = ThreadPool(int(threadpoolnum))
    if parameters and isinstance(parameters,dict):
        results = pool.map(lambda x : func(x, **parameters), maplist)
    elif parameters and isinstance(parameters,list):
        results = pool.map(lambda x : func(x, *parameters), maplist)
    else:
        results = pool.map(func, maplist)
    pool.close()
    pool.join()
    return results

#import interfaces.switchpreviewutil as switchpreviewutil

# Create a custom logger
# Allows logging to state detailed info such as module where code is running and 
# specifiy logging levels for file vs console.  Set default level to DEBUG to allow more
# grainular logging levels
logger = logging.getLogger('aciops.' + __name__)



def return_configured_ports_for_display_per_leaf(leaf,apic,cookie):
    switchpfound, fexes = fabric_access.display_switch_to_leaf_structure.return_physical_programmed_ports_perleaf(leaf, apic, cookie)
    interfaces_with_APS_defined = []
    fexfound = []
    for switchp in switchpfound:
        for leafp in switchp.leafprofiles:
            interfaces_with_APS_defined.append((switchp.allleafs,leafp.allports))
            for portlist in leafp.infraHPortSlist:
                for x in fexes:
                    if portlist.infraRsAccBaseGrp.tDn != '' and  x.dn in portlist.infraRsAccBaseGrp.tDn:
                        if portlist.infraFexPlist:
                            fexfound.append((x,portlist.infraRsAccBaseGrp.fexId))
    for fex in fexfound:
        interfaces_with_APS_defined.append((fex[1],fex[0].allports))
    compiledports = []
    for interface in interfaces_with_APS_defined:
        if type(interface[0]) != unicode:
            for templeaf in interface[0]:
                for modulenum, ports in interface[1].items():
                    for port in ports:  
                        compiledports.append(('eth' + str(modulenum) + '/' + str(port)))
        else:
            for modulenum, ports in interface[1].items():
                for port in ports:
                    compiledports.append(('eth' + str(interface[0]) + '/' + str(modulenum) + '/' + str(port)))
    compiledports = list(set(compiledports))
    newlist = []
    for x in compiledports:
        newlist.append(l1PhysIf(id = x, shortnum = x.split('/')[-1][0]))
    return (leaf,compiledports)

def location_banner(location):
    banner = ("######################################\n"
            + "#{:^36}#\n".format('')
            + "#{:^36}#\n".format(location)
            + "#{:^36}#\n".format('')
            + "######################################\n")
    print(banner)

def askconfirmation(text):
    while True:
        confirmation = custom_raw_input("{text} [y]: ".format(text=text)) or 'y'
        if confirmation != '' and confirmation[0].lower() == 'y':
            return True
        elif confirmation != '' and confirmation[0].lower() == 'n':
            return False
        else:
            print('\nInvalid option...')


def custom_raw_input(inputstr):
    r = raw_input(inputstr).strip().lstrip()
    if r == 'exit':
        raise KeyboardInterrupt
    else:
        return r
        
def clear_screen():
    if os.name == 'posix':
        os.system('clear')
    else:
        os.system('cls')

def time_difference(current_time, event_time):
    currenttime = datetime.datetime.strptime(current_time, '%Y-%m-%d %H:%M:%S.%f')
    ref_event_time = datetime.datetime.strptime(event_time, '%Y-%m-%d %H:%M:%S.%f')
    calculatedtime = str(currenttime - ref_event_time)
    if '.' in calculatedtime:
        return calculatedtime[:-7]
    else:
        return calculatedtime


def get_APIC_clock(apic,cookie):
    if apic == 'localhost':
        serverhostname = socket.gethostname()
        url = """https://{apic}/api/node/class/topSystem.json?query-target-filter=or(eq(topSystem.name,"{serverhostname}"))""".format(apic=apic,serverhostname=serverhostname)
    elif not re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$",apic.strip().lstrip()):
        apicip = socket.gethostbyname(apic)
        url = """https://{apic}/api/node/class/topSystem.json?query-target-filter=or(eq(topSystem.oobMgmtAddr,"{apicip}"),eq(topSystem.inbMgmtAddr,"{apicip}"))""".format(apic=apic,apicip=apicip)
    else:
        url = """https://{apic}/api/node/class/topSystem.json?query-target-filter=or(eq(topSystem.oobMgmtAddr,"{apic}"),eq(topSystem.inbMgmtAddr,"{apic}"))""".format(apic=apic)
    logger.info(url)
    result = GetResponseData(url,cookie)
    if result == []:
        url = """https://{apic}/api/mo/info.json""".format(apic=apic)
        result = GetResponseData(url,cookie)
        return result[0]['topInfo']['attributes']['currentTime'][:-7].replace('T', ' ')
    return result[0]['topSystem']['attributes']['currentTime'][:-7].replace('T', ' ')

def refreshToken(apic,icookie):
    ssl._create_default_https_context = ssl._create_unverified_context
    url = "https://{apic}/api/aaaRefresh.json".format(apic=apic)
    logger.info(url)
    cookies = 'APIC-cookie=' + icookie
    request = urllib2.Request(url)
    request.add_header("Cookie", cookies)
    response = urllib2.urlopen(request, timeout=45)
    result = json.loads(response.read())
    program_globals.TOKEN = result["imdata"][0]["aaaLogin"]["attributes"]["token"]
    return program_globals.TOKEN

#############################################################################################################################################
#                               What does this program do
#                               What are you trying to accomplish
#                               Who program the thing
#                               What version you are on
#                               Date Created
#                               Date Last time modify
#############################################################################################################################################

#############################################################################################################################################
#                               What does this def do period
#                               Who program the thing
#                               What version you are on
#                               Date Created
#                               Date Last time modify
#############################################################################################################################################


def GetRequest(url, icookie, timeout=45):
    # Function to Perform HTTP Get REST calls and return server recieved data in an http object
    method = "GET"
    # icookie comes from the GetResponseData fuction that references 'cookie' which is a global variable from reading /.aci/.sessions/.token
    cookies = 'APIC-cookie=' + icookie
    # create urllib2 object to add headers and cookies
    request = urllib2.Request(url)
    # Function needs APIC cookie for authentication and what content format you need in returned http object (example JSON)
    # need to add header one at a time in urllib2
    request.add_header("cookie", cookies)
    request.add_header("Content-Type", "application/json")
    request.add_header('Accept', 'application/json')
    return urllib2.urlopen(request, context=ssl._create_unverified_context(), timeout=int(timeout))

def GetResponseData(url, cookie, timeout=0, return_count=False):
    # Fuction to take JSON and load it into Python Dictionary format and present all JSON inside the 'imdata' level
    # Perform a GetRequest function to perform a GET REST call to server and provide response data
    if timeout > 0:
        response = GetRequest(url, cookie, timeout=int(timeout)) # here for this
    else:
        response = GetRequest(url, cookie) # here for this
    # the 'response' is an urllib2 object that needs to be read for JSON data, this loads the JSON to Python Dictionary format
    result = json.loads(response.read()) # here for this
    # return only infomation inside the dictionary under 'imdata'
    #logger.debug(result)
    if return_count == True:
        return result['imdata'], result['totalCount']
    else:
        return result['imdata'] #here for this

def PostandGetResponseData(url, data, cookie):
    # Fuction to submit JSON and load it into Python Dictionary format and present all JSON inside the 'imdata' level
    # Perform a POSTRequest function to perform a POST REST call to server and provide response data
    response, error = POSTRequest(url, data, cookie)
    # the 'response' is an urllib2 object that needs to be read for JSON data, this loads the JSON to Python Dictionary format
        # return only infomation inside the dictionary under 'imdata'.  If response is a string rether than a urllib object return str with error
    if isinstance(response,str):
        return response, error
    else:
        result = json.loads(response.read())
        return result['imdata'], error

def POSTRequest(url, data, icookie):
    # Function to Perform HTTP POST call to update and create objects and return server data in an http object
    # POST in urllib2 is special because it doesn't exist as a built-in method for the urllib2 object you need to make a function (aka lambda) and refrence this method
    method = "POST"
    # icookie comes from the PostandGetResponseData fuction that references 'cookie' which is a global variable from reading /.aci/.sessions/.token
    cookies = 'APIC-cookie=' + icookie
    # notice 'data' is going to added to the urllib2 object, unlike GET requests
    request = urllib2.Request(url, data)
    # Function needs APIC cookie for authentication and what content format you need in returned http object (example JSON)
    # need to add header one at a time in urllib2
    request.add_header("cookie", cookies)
    request.add_header("Content-type", "application/json")
    request.add_header('Accept', 'application/json')
    # Mandate the urllib request is a POST instead of default GET request
    request.get_method = lambda: method
    try:
        return urllib2.urlopen(request, context=ssl._create_unverified_context()), None
    except urllib2.HTTPError as httpe:
        failure_reason = json.loads(httpe.read())
        failure_reason = failure_reason['imdata'][0]['error']['attributes']['text'].strip()
        return 'invalid', failure_reason
    except urllib2.URLError as urle:
        #print(urle.code)
        failure_reason = json.loads(urle.read())
        return 'invalid', failure_reason

class json_collector(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def interface_menu():
    while True:
        print("\nSelect type of interface(s): \n\n" + \
          "\t1.) Physical Interfaces \n" + \
          "\t2.) PC Interfaces \n" + \
          "\t3.) VPC Interfaces \n")
        selection = custom_raw_input("Select number: ")
        print('\r')
        if selection.isdigit() and selection != '' and 1 <= int(selection) <= 3:
            break
        else:
            continue
    return selection 

class epgformater():
    def __init__(self, epgdn):
        self.dnsplit = epgdn.split('/')
        self.tenant = self.dnsplit[1]
        self.app = self.dnsplit[2]
        self.epg = self.dnsplit[3]
        self.clean = '|'.join((self.tenant.replace('tn-',''),self.app.replace('ap-',''),self.epg.replace('epg-','')))
    def __repr__(self):
        return self.clean
    def __str__(self):
        return self.clean

class fabricPathEp(object):
    def __init__(self, descr=None, dn=None,name=None, number=None):
        self.name = name
        self.descr = descr
        self.dn = dn
        self.number = number
        self.epgfvRsPathAttlist = []
        self.leaf =  dn.split('/')[2].replace('paths','leaf')
        self.shortname = name.replace('eth1/','')
        self.removedint = '/'.join(dn.split('/')[:-2])
        if 'extpaths' in self.dn:
            self.fex = self.dn.split('/')[3].replace('extpaths','fex')
            self.fexethname = self.name[:3]+ self.dn.split('/')[3].replace('extpaths-','') + '/' + self.name[3:]
        else:
            self.fex = None
            self.fexethname = None
    def __repr__(self):
        return self.dn
    def __getitem__(self, number):
        if number in self.dn:
            return self.dn
        else:
            return None

class l1PhysIf():
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        self.fex = None
        self.typefex = None 
        self.uplink = None 
        self.pctype = None
       # self.
        self.pc_mbmr = []
        self.children = []
    def __repr__(self):
        return self.id
    def __setitem__(self, a,b):
        setattr(self, a, b)
    def add_child(self, obj):
        self.children.append(obj)
    def __getitem__(self, x):
        if x == self.id:
            return True
    def add_portchannel(self, p):
        self.pc_mbmr.append(p) 
    def port_adminstatus_color(self):
        if self.adminSt == 'up':
            return '\x1b[1;37;42m{:2}\x1b[0m'.format(self.shortnum)
        else:
            return '\x1b[3;47;40m{:2}\x1b[0m'.format(self.shortnum)
    def port_epgusage_color(self):
        if 'epg' in self.usage:
            #return '\x1b[1;37;42m{:2}\x1b[0m'.format(self.shortnum)
            return '\x1b[1;37;42m{:2}\x1b[0m'.format(self.shortnum)
        else:
            #return '\x1b[2;30;47m{:2}\x1b[0m'.format(self.shortnum)
            return '\x1b[3;47;40m{:2}\x1b[0m'.format(self.shortnum)            
    def port_status_color(self):
        if self.portstatus == 'up/up' and self.switchingSt == 'enabled':
            return '\x1b[1;37;42m{:2}\x1b[0m'.format(self.shortnum)
        elif self.portstatus == 'up/up' and self.switchingSt == 'disabled':
            return '\x1b[0;30;43m{:2}\x1b[0m'.format(self.shortnum)
        elif self.portstatus == 'admin-down':
            #2;30;47
            return '\x1b[2;30;47m{:2}\x1b[0m'.format(self.shortnum)
            #return '\x1b[0;37;45m{:2}\x1b[0m'.format(self.shortnum)
        else:
            return '\x1b[1;37;41m{:2}\x1b[0m'.format(self.shortnum)
    def port_type_color(self):
        if not 'not-a-span-dest' in self.spanMode:
            return '\x1b[1;31;40m{:2}\x1b[0m'.format(self.shortnum)
        elif 'controller' in self.usage:
            return '\x1b[1;37;45m{:2}\x1b[0m'.format(self.shortnum)
        elif self.layer == "Layer2" and self.pcmode == 'off' and self.epgs_status == 'yes':
            return '\x1b[2;30;42m{:2}\x1b[0m'.format(self.shortnum)
        elif self.layer == "Layer2" and not self.pcmode == 'off' and self.pctype == 'pc':
            return '\x1b[2;30;42m{:2}\x1b[0m'.format(self.shortnum)
        elif self.layer == "Layer2" and not self.pcmode == 'off' and self.pctype == 'vpc':
            return '\x1b[2;37;44m{:2}\x1b[0m'.format(self.shortnum)
        elif 'fabric' in self.usage:
            return '\x1b[3;30;47m{:2}\x1b[0m'.format(self.shortnum)
        elif self.layer == "Layer3":
            return '\x1b[2;30;43m{:2}\x1b[0m'.format(self.shortnum)
        elif self.fex == True:
            return '\x1b[2;30;41m{:2}\x1b[0m'.format(self.shortnum)
        else:
            return '\x1b[2;30;37m{:2}\x1b[0m'.format(self.shortnum)
    def port_error_color(self):
        if self.allerrors <= 100:
            return '\x1b[2;30;47m{:2}\x1b[0m'.format(self.shortnum)        
        elif 1000 <= self.allerrors >= 101:
            return '\x1b[2;30;43m{:2}\x1b[0m'.format(self.shortnum)
        elif self.allerrors >= 1001:
            return '\x1b[1;37;41m{:2}\x1b[0m'.format(self.shortnum)          
        else:
            return '\x1b[1;37;42m{:2}\x1b[0m'.format(self.shortnum)
    def custom_matched_port_color(self, interfacelist):
        if self.id in interfacelist:
            return '\x1b[1;37;42m{:2}\x1b[0m'.format(self.shortnum)
        else:
            return '{:2}'.format(self.shortnum)

def grouper(iterable, n, fillvalue=''):
    "Collect data into fixed-length chunks or blocks"
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx"
    args = [iter(iterable)] * n  # creates list * n so args is a list of iters for iterable
    return itertools.izip_longest(*args, fillvalue=fillvalue)

def goodspacing(column):
    if column.fex:
        return column.leaf + ' ' + column.fex + ' ' + str(column.name)
    elif column.fex == None:
        return column.leaf + ' ' + str(column.name)

def get_column_sizes(rowlist, objcolumnwidthfind=None, minimum=5, baseminimum=[],alreadysorted=False):
    sizelist = []
    if alreadysorted:
        for num,column in enumerate(rowlist):
            maxfound = len(str(max(column, key=lambda x:len(str(x)))))
            if maxfound >= len(baseminimum[num]):
                sizelist.append(maxfound)
            else:
                sizelist.append(len(baseminimum[num]))
        return sizelist
    if objcolumnwidthfind:
        for num,column in enumerate(objcolumnwidthfind):
            nestedlist = False
            c_rowlist = filter(lambda x: hasattr(x, column), rowlist)
            if c_rowlist == [] or c_rowlist == None:
                try:
                    sizelist.append(len(str(column)))    
                except:
                    sizelist.append(minimum)
    
            else:
                currentcolumnmaxobj = max(c_rowlist, key=lambda x: len(str(getattr(x, column))))
               # print(getattr(currentcolumnmaxobj,column))
                if type(getattr(currentcolumnmaxobj, column)) == list:
                    currentcolumnmaxobj = max(c_rowlist, key=lambda x: len(','.join(str(getattr(x, column)))))
                    insidelistmax = len(','.join(getattr(currentcolumnmaxobj,column)))
                    #print(','.join(getattr(currentcolumnmaxobj,column)))
                    nestedlist = True
                if nestedlist:
                    if insidelistmax < 1:
                        if baseminimum == []:
                            sizelist.append(minimum)
                        else:
                            sizelist.append(minimum)
                    else:
                        sizelist.append(insidelistmax)
                else:
                    if len(str(getattr(currentcolumnmaxobj, column))) < 1:
                        if baseminimum == []:
                            sizelist.append(minimum)
                        else:
                            sizelist.append(len(baseminimum[num]))
                    else:
                        if baseminimum == [] and len(str(getattr(currentcolumnmaxobj, column))) < minimum:
                            sizelist.append(minimum)
                        elif baseminimum != [] and len(str(getattr(currentcolumnmaxobj, column))) < len(baseminimum[num]):
                            sizelist.append(len(baseminimum[num]))
                        elif baseminimum != [] and len(str(getattr(currentcolumnmaxobj, column))) > len(baseminimum[num]):
                            sizelist.append(len(str(getattr(currentcolumnmaxobj, column))))
                        else:
                            sizelist.append(len(str(getattr(currentcolumnmaxobj, column))))
        return sizelist
    else:
        temprowlist = rowlist[:]
       # temprowlist = list(rowlist[:])
        temprowlist.append(baseminimum)
        columns = zip(*temprowlist)
        del(temprowlist)
        for column in columns:
            sizelist.append(len(str(max(column, key=lambda x:len(str(x))))))
        return sizelist


def display_and_select_epgs(choseninterfaceobjectlist, allepglist):
    numepgdict = {}
    print("\n{:>4} | {:8}|  {:15}|  {}".format("#","Tenant","App-Profile","EPG"))
    print("-"* 65)
    allepglist = sorted(allepglist)
    for num,epg in enumerate(allepglist,1):
        numepgdict[num] = epg
        egpslit = epg.split('/')[1:]
        print("{:4}.) {:8}|  {:15}|  {}".format(num,egpslit[0][3:],egpslit[1][3:],egpslit[2][4:]))
    while True:
        askepgnum = custom_raw_input("\nWhich number(s)?: ")
        print('\r')
        if askepgnum.strip().lstrip() == '':
            continue
        epgsinglelist = parseandreturnsingelist(askepgnum,numepgdict)
        if epgsinglelist == 'invalid':
            continue
        chosenepgs = [allepglist[x-1] for x in epgsinglelist]
        break
    return chosenepgs, choseninterfaceobjectlist


def physical_leaf_selection(all_leaflist, apic, cookie, leafnum=None):
    if leafnum == None:
        nodelist = [node['fabricNode']['attributes']['id'] for node in all_leaflist]
        nodelist.sort()
        for num,node in enumerate(nodelist,1):
            print("{}.) {}".format(num,node))
        while True:
            asknode = custom_raw_input('\nWhich leaf(s): ')
            print('\r')
            returnedlist = parseandreturnsingelist(asknode, nodelist)
            if returnedlist == 'invalid':
                continue
            chosenleafs = [nodelist[int(node)-1] for node in returnedlist]
            break
    else:
        chosenleafs = [leafnum]
    return chosenleafs

def physical_interface_selection(apic, cookie, chosenleafs, provideleaf=False, provided_interfacelist=None, returnlistonly=False):
    if provided_interfacelist == None:
        compoundedleafresult = []
        for leaf in chosenleafs:
            url = """https://{apic}/api/node/class/fabricPathEp.json?query-target-filter=and(not(wcard(fabricPathEp.dn,%22__ui_%22)),""" \
                  """and(eq(fabricPathEp.lagT,"not-aggregated"),eq(fabricPathEp.pathT,"leaf"),wcard(fabricPathEp.dn,"topology/pod-1/paths-{leaf}/"),""" \
                  """not(or(wcard(fabricPathEp.name,"^tunnel"),wcard(fabricPathEp.name,"^vfc")))))&order-by=fabricPathEp.dn|desc""".format(leaf=leaf,apic=apic)
            logger.info(url)
            result = GetResponseData(url, cookie)
            logger.debug(result)
            compoundedleafresult.append(result)
        result = compoundedleafresult
        interfacelist = []
        interfacelist2 = []
        for x in result:
            for pathep in x:
                dn = pathep['fabricPathEp']['attributes']['dn']
                name = pathep['fabricPathEp']['attributes']['name']
                descr = pathep['fabricPathEp']['attributes']['descr']
                if 'extpaths' in dn:
                    interfacelist2.append(fabricPathEp(descr=descr, dn=dn ,name=name))
                else:
                    interfacelist.append(fabricPathEp(descr=descr, dn=dn ,name=name))
                
        interfacelist2 = sorted(interfacelist2, key=lambda x: (x.fex, int(x.shortname)))
        interfacelist = sorted(interfacelist, key=lambda x: int(x.shortname))
        interfacenewlist = interfacelist2 + interfacelist
        interfacelist = []
        interfacelist2 = []
        finalsortedinterfacelist = sorted(interfacenewlist, key=lambda x: x.removedint)
        if returnlistonly:
            return finalsortedinterfacelist
    else:
        finalsortedinterfacelist = provided_interfacelist
    interfacedict = {}
    for num,interf in enumerate(finalsortedinterfacelist,1):
        if interf != '':
           interfacedict[interf] = str(num) + '.) '
           interf.number = num
    listlen = len(finalsortedinterfacelist) / 2
    if len(finalsortedinterfacelist) % 2 != 0:
        listlen += 1
    firstgrouped = [x for x in grouper(finalsortedinterfacelist,listlen)]
    finalgrouped = zip(*firstgrouped)
    print("{:7}{:25}{:32}{:28}{}".format('',"Interface","Description","Interface","Description"))
    print("   {:90}".format('-'* 105))
    for column1,column2 in finalgrouped:
        a = column1.number
        if len(goodspacing(column1) + '  ') >= 22:
            b = goodspacing(column1) + '  ' + '\x1b[1;33;40m' + column1.descr[:24] + '\x1b[0m'
        else:
            b = goodspacing(column1) + '  ' + '\x1b[1;33;40m' + column1.descr[:32] + '\x1b[0m'
        if column2 != '':
            c = column2.number
            if len(goodspacing(column2) + '  ') >= 22:
                d = goodspacing(column2) + '  ' + '\x1b[1;33;40m' + column2.descr[:24] + '\x1b[0m'
            else:
                d = goodspacing(column2) + '  ' + '\x1b[1;33;40m' + column2.descr[:32] + '\x1b[0m'
        else:
            c = ''
       # if column3 == '' or column3 == None:
       #     e = ''
       # f = ''
       # else:
       #     e = column3.number
       #     if len(goodspacing(column3) + '  ') >= 22:
       #         f = goodspacing(column3) + '  ' + '\x1b[1;33;40m' + column3.descr[:24] + '\x1b[0m'
       #     else:
       #         f = goodspacing(column3) + '  ' + '\x1b[1;33;40m' + column3.descr[:32] + '\x1b[0m'
        #if f != '':
        #    print('{:4}.) {:65} {}.) {:65} {}.) {}'.format(a,b,c,d,e,f))
        if c == '':
            print('{:4}.) {:65}'.format(a,b))
        else:
            print('{:4}.) {:65} {}.) {:65}'.format(a,b,c,d))
    while True:
        selectedinterfaces = custom_raw_input("\nSelect interface(s) by number: ")
        print('\r')
        if selectedinterfaces.strip().lstrip() == '':
            continue
        intsinglelist = parseandreturnsingelist(selectedinterfaces,finalsortedinterfacelist)
        if intsinglelist == 'invalid':
            continue
        if provideleaf == False:
            choseninterfaceobjectlist = filter(lambda x: x.number in intsinglelist, finalsortedinterfacelist)
            return choseninterfaceobjectlist
        else:
            #chosenleafs
            choseninterfaceobjectlist = filter(lambda x: x.number in intsinglelist, finalsortedinterfacelist)
            return choseninterfaceobjectlist, chosenleafs


def port_channel_location(pcname, apic, cookie, pctype='vpc'):
    if pctype == 'vpc':
        url = """https://{apic}/api/class/pcAggrIf.json?query-target-filter=eq(pcAggrIf.name,"{pcname}")&rsp-subtree=full&rsp-subtree-class=pcRsMbrIfs""".format(apic=apic,pcname=pcname)
        result = GetResponseData(url, cookie)
    else:
        url = """https://{apic}/api/class/pcAggrIf.json?query-target-filter=eq(pcAggrIf.name,"{pcname}")&rsp-subtree=full&rsp-subtree-class=pcRsMbrIfs""".format(apic=apic,pcname=pcname)
        result = GetResponseData(url, cookie)
    all_locationlist = []
    for pcaggrif in result:
        pcdn = pcaggrif['pcAggrIf']['attributes']['dn']
        pcsplit = pcdn.split('/')
        pcdn_pod = pcsplit[1]
        pcdn_node = pcsplit[2]
        #pcdn_pcnum = pcsplit[4]
        nodelocation = '{}, {}'.format(pcdn_pod,pcdn_node)
        #print('pcnum {}'.format(pcdn_pcnum))
        if pcaggrif['pcAggrIf']['children']:
            interfacelist = []
            for child in pcaggrif['pcAggrIf']['children']:
                childtdn = child['pcRsMbrIfs']['attributes']['tDn']
                pcaggrif_begin = childtdn.find('[')
                pcaggrif_end = childtdn.find(']')
                pcinterface = childtdn[pcaggrif_begin+1:pcaggrif_end]
                interfacelist.append(pcinterface)
        interfacelist.sort()
        all_locationlist.append((nodelocation, interfacelist))
    #import pdb; pdb.set_trace()
    return all_locationlist

class pcObject():
    def __init__(self, name=None, dn=None, number=None):
        self.name = name
        self.dn = dn
        self.number = number
        self.epgfvRsPathAttlist = []
    def __repr__(self):
        return self.dn
    def __get__(self, num):
        if num in self.number:
            return self.name
        else:
            return None

def port_channel_selection(allpclist):
    pcobjectlist = []
    for pc in allpclist:
        pcobjectlist.append(pcObject(name = pc['fabricPathEp']['attributes']['name'],
                                     dn = pc['fabricPathEp']['attributes']['dn'] ))
    print("\n{:>4} |  {}".format("#","Port-Channel Name"))
    print("-"* 65)
    pcobjectlist = sorted(pcobjectlist, key=lambda x:x.name)
    #import pdb; pdb.set_trace()
    for num,pc in enumerate(pcobjectlist,1):
        print("{:>4}.) {}".format(num,pc.name))
        pc.number = num
    while True:
        try:
            askpcnum = custom_raw_input("\nWhich number(s)?: ")
            print('\r')
            if askpcnum.strip().lstrip() == '':
                continue
            pcsinglelist = parseandreturnsingelist(askpcnum,pcobjectlist)
            if pcsinglelist == 'invalid':
                continue
            choseninterfaceobjectlist = filter(lambda x: x.number in pcsinglelist, pcobjectlist)
            break
        except ValueError:
            print("\n\x1b[1;37;41mInvalid format and/or range...Try again\x1b[0m\n")
    return choseninterfaceobjectlist

def parseandreturnsingelist(liststring, collectionlist=None):
    try:
        rangelist = []
        singlelist = []
        seperated_list = liststring.split(',')
        for x in seperated_list:
            if '-' in x:
                rangelist.append(x)
            else:
                singlelist.append(int(x))
        if len(rangelist) >= 1:
            for foundrange in rangelist:
                tempsplit = foundrange.split('-')
                for i in xrange(int(tempsplit[0]), int(tempsplit[1])+1):
                    singlelist.append(int(i))
   #     print(sorted(singlelist))
        if collectionlist:
            if max(singlelist) > len(collectionlist) or min(singlelist) < 1:
                print('\n\x1b[1;37;41mInvalid format and/or range...Try again\x1b[0m\n')
                return 'invalid'
        return list(set(singlelist)) 
    except ValueError as v:
        print('\n\x1b[1;37;41mInvalid format and/or range...Try again\x1b[0m\n')
        return 'invalid'
#class vlanCktEp():
#    def __init__(self, **kwargs):
#        self.__dict__.update(kwargs)
#    def __repr__(self):
#        if self.name != '':
#            return self.name
#        else:
#            return self.epgDn

class vlanCktEp():
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        self.tenant = self.epgDn.split('/')[1].replace('tn-','')
        self.app = lambda x : '/'.join(self.epgDn.split('/')[2:]) if 'LDevInst' in self.epgDn.split('/')[2] else self.epgDn.split('/')[2].replace('ap-','')
        self.epg = '/'.join(self.epgDn.split('/')[3:]).replace('epg-','')
    def __repr__(self):
        if self.name != '':
            return self.name
        else:
            return self.epgDn

class moContainer():
    primaryKey = 'dn'
    def __init__(self,primaryKey):
        self.containerset = set()
    #def __setitem__(self, k,v):
    #    setattr(self, k, v)
    #    self.containerset.add(k)
    def add(self,item):
        self.containerset.add(item)
        self[getattr(item,primaryKey)] = item
    def __getitem__(self,key):
        return getattr(self,key)
    def __repr__(self):
        return repr(self.containerset)

class foundobj():
    def __init__(self, kwargs):
        self.__dict__.update(**kwargs)
    def __setitem__(self, k,v):
        setattr(self, k, v)
    def __getitem__(self,key):
        return getattr(self,key)
    def __repr__(self):
        return repr({k:v for k,v in self.__dict__.items()})
        

def grab_lowest_MO_keyvalues(x, primaryKey=None, keys=None, scope_set=None, returnlist=None,cObject=None):
    if returnlist is None:
        returnlist = []
    if keys is None:
        keys = []
    if cObject == None:
        cObject = foundobj
    if scope_set is None:
        scope_set = set()
    if isinstance(x, list):
        for y in x:
            grab_lowest_MO_keyvalues(y, primaryKey, keys, scope_set, returnlist)
    elif isinstance(x, dict):
        for k,v in x.items():
            if isinstance(v, list):
                grab_lowest_MO_keyvalues(v, primaryKey, keys, scope_set, returnlist)
            elif isinstance(v, dict):
                grab_lowest_MO_keyvalues(v, primaryKey, keys, scope_set, returnlist)
            else:
                if not x[primaryKey] in scope_set:
                    scope_set.add(x[primaryKey])
                    fo = cObject({primaryKey:x[primaryKey]})
                    for kk in keys:
                        fo[kk] = x[kk]
                    returnlist.append(fo)
    return returnlist

class parentobj():
    def __init__(self,objectname):
        self.objectname = objectname
        self.children = []
    def add_child(self,childobj):
        self.children.append(childobj)
    def __getitem__(self,key):
        return getattr(self,key)
    def __setitem__(self, k,v):
        setattr(self, k, v)
    def __eq__(self,item):
        return type(self) == type(item)
    def __hash__(self):
        return hash(self.objectname)
    def __repr__(self):
        return repr(self.objectname)

class childobj():
    def __init__(self, childname):
        self.childname = childname
        #self.__dict__.update(**kwargs)
    def __setitem__(self, k,v):
        setattr(self, k, v)
    def __getitem__(self,key):
        return getattr(self,key)
    def __repr__(self):
        if hasattr(self, 'name'):
            return self.name
        else:
            return self.childname
#        return repr({k:v for k,v in self.__dict__.items()})


def grab_lowest_MO_keyvalues2(x, parentclass=None, parentid=None, parent_keys=None, childclass=None, childid =None,child_keys=None, parent_dict=None,child_set=None, returnlist=None,pObject=None,cObject=None):
    if returnlist is None:
        returnlist = []
    if parent_keys is None:
        parent_keys = []
    if child_keys is None:
        child_keys = []
    if child_set is None:
        child_set = set()
    if cObject is None:
        CO = childobj
    else:
        CO = cObject
    if pObject is None:
        PO = parentobj
    else:
        PO = pObject
    if parent_dict is None:
        parent_dict = dict()
    if isinstance(x, list):
        for y in x:
            grab_lowest_MO_keyvalues2(y, parentclass, parentid, parent_keys, childclass, childid,child_keys, parent_dict,child_set, returnlist, PO,CO)
    elif isinstance(x, dict):
        if not isinstance(PO,parentobj):
            PO = PO(x[parentclass]['attributes'][parentid])
        for k,v in x.items():
            if isinstance(v, list):
                grab_lowest_MO_keyvalues2(v, parentclass,parentid, parent_keys, childclass, childid,child_keys, parent_dict,child_set, returnlist, PO,CO)
            elif isinstance(v, dict):
                if k == 'attributes':
                    grab_lowest_MO_keyvalues2(v, parentclass,parentid, parent_keys, childclass, childid,child_keys, parent_dict,child_set, returnlist, PO,CO)
                if CO == childobj and k != parentclass and k != 'attributes':
                    CO = CO(v['attributes'][childid])
                    grab_lowest_MO_keyvalues2(v, parentclass,parentid, parent_keys, childclass, childid,child_keys, parent_dict,child_set, returnlist, PO,CO)
                else:
                    grab_lowest_MO_keyvalues2(v, parentclass,parentid, parent_keys, childclass, childid,child_keys, parent_dict,child_set, returnlist, PO,CO)
            else:
                if isinstance(PO,parentobj) and not isinstance(CO,childobj):
                    PO[k] = v
                    for k in parent_keys:
                        PO[k] = x[k]
                    if PO.objectname not in parent_dict:
                        parent_dict[PO.objectname] = PO
                    return
                if isinstance(PO,parentobj) and isinstance(CO,childobj):
                    if (PO.objectname + CO.childname) not in child_set:
                        child_set.add(PO.objectname + CO.childname)
                        if PO.objectname in parent_dict:
                            for k in child_keys:
                                CO[k] = x[k]
                            parent_dict[PO.objectname].add_child(CO)
                            
                            return
            
    return parent_dict


def pull_vlan_info_for_leaf(apic, cookie, leaf):
    url = """https://{apic}/api/node/class/topology/pod-1/node-{leaf}/vlanCktEp.json""".format(apic=apic, leaf=leaf)
    logger.info(url)
    result = GetResponseData(url, cookie)
    vlanlist = [vlanCktEp(**x['vlanCktEp']['attributes']) for x in result]
    return vlanlist

def get_All_vlanCktEp(apic, cookie, return_count=False):
    url = """https://{apic}/api/node/class/vlanCktEp.json""".format(apic=apic)
    logger.info(url)
    if return_count == True:
        return GetResponseData(url, cookie, return_count=True)
       # return [vlanckt['vlanCktEp']['attributes']['dn'] for vlanckt in result], totalcount
    else:
        return GetResponseData(url, cookie)
        #return [vlanckt['vlanCktEp']['attributes']['dn'] for vlanckt in result]


def get_All_EGPs_names(apic, cookie, return_count=False):
    url = """https://{apic}/api/node/class/fvAEPg.json""".format(apic=apic)
    logger.info(url)
    if return_count == True:
        result, totalcount = GetResponseData(url, cookie, return_count=True)
        return [epg['fvAEPg']['attributes']['dn'] for epg in result], totalcount
    else:
        result = GetResponseData(url, cookie)
        return [epg['fvAEPg']['attributes']['dn'] for epg in result]

def get_All_EGPs_data(apic, cookie, return_count=False):
    url = """https://{apic}/api/node/class/fvAEPg.json""".format(apic=apic)
    logger.info(url)
    if return_count == True:
        result, totalcount = GetResponseData(url, cookie, return_count=True)
        return [epg for epg in result], totalcount
    else:
        result = GetResponseData(url, cookie)
        return [epg for epg in result]


def get_All_PCs(apic, cookie, return_count=False):
    url = """https://{apic}/api/node/class/fabricPathEp.json?query-target-filter=and(not(wcard(fabricPathEp.dn,%22__ui_%22)),""" \
          """eq(fabricPathEp.lagT,"link"))""".format(apic=apic)
    logger.info(url)
    if return_count == True:
        result, totalcount = GetResponseData(url, cookie, return_count=True)
        return result, totalcount
    else:
        result = GetResponseData(url, cookie)
        return result

def get_All_l2BDs(apic, cookie, return_count=False):
    url = """https://{apic}/api/class/l2BD.json""".format(apic=apic)
    logger.info(url)
    if return_count == True:
        result, totalcount = GetResponseData(url, cookie, return_count=True)
        return result, totalcount
    else:
        result = GetResponseData(url, cookie)
        return result

def get_All_BDs(apic, cookie, return_count=False):
    url = """https://{apic}/api/class/fvBD.json""".format(apic=apic)
    logger.info(url)
    if return_count == True:
        result, totalcount = GetResponseData(url, cookie, return_count=True)
        return result, totalcount
    else:
        result = GetResponseData(url, cookie)
        return result


def get_portchannel_by_name(name, apic, cookie, type='vpc'):
    if type=='vpc':
        url = """https://{apic}/api/node/class/fabricPathEp.json?query-target-filter=and(not(wcard(fabricPathEp.dn,%22__ui_%22)),""" \
                """and(eq(fabricPathEp.lagT,"node"),wcard(fabricPathEp.dn,"^topology/pod-[\d]*/protpaths-"),eq(fabricPathEp.name,"{name}")))""".format(apic=apic,name=name)
        results = GetResponseData(url, cookie)
        #url = 'https://{apic}/api/node/class/fabricPathEp.json?query-target-filter=eq(fabricPathEP.dn,"{name}"),wcard(fabricPathEp.dn,"^topology/pod-[\d]*/protpaths-")'
    elif type=='pc':
        url = """https://{apic}/api/node/class/fabricPathEp.json?query-target-filter=and(not(wcard(fabricPathEp.dn,%22__ui_%22)),""" \
                """and(eq(fabricPathEp.lagT,"link"),wcard(fabricPathEp.dn,"^topology/pod-[\d]*/protpaths-"),eq(fabricPathEp.name,"{name}")))""".format(apic=apic,name=name)
    else:
        raise NotImplementedError
    result = GetResponseData(url, cookie)
    return result

def get_All_vPCs(apic, cookie, return_count=False):
    url = """https://{apic}/api/node/class/fabricPathEp.json?query-target-filter=and(not(wcard(fabricPathEp.dn,%22__ui_%22)),""" \
          """and(eq(fabricPathEp.lagT,"node"),wcard(fabricPathEp.dn,"^topology/pod-[\d]*/protpaths-")))""".format(apic=apic)
    logger.info(url)
    if return_count == True:
        result, totalcount = GetResponseData(url, cookie, return_count=True)
        return result, totalcount
    else:
        result = GetResponseData(url, cookie)
        return result


def get_All_leafs(apic, cookie, return_count=False):
    url = """https://{apic}/api/node/class/fabricNode.json?query-target-filter=and(not(wcard(fabricNode.dn,%22__ui_%22)),""" \
          """and(eq(fabricNode.role,"leaf"),eq(fabricNode.fabricSt,"active"),ne(fabricNode.nodeType,"virtual")))""".format(apic=apic)
    logger.info(url)
    if return_count == True:
        result, totalcount = GetResponseData(url, cookie, return_count=True)
        return result, totalcount
    else:
        result = GetResponseData(url, cookie)
        return result
