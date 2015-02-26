#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Faraday Penetration Test IDE
Copyright (C) 2013  Infobyte LLC (http://www.infobytesec.com/)
See the file 'doc/LICENSE' for the license information

'''
from __future__ import with_statement
from plugins import core
from model import api
import re
import os
import pprint
import sys

try:
    import xml.etree.cElementTree as ET
    import xml.etree.ElementTree as ET_ORIG
    ETREE_VERSION = ET_ORIG.VERSION
except ImportError:
    import xml.etree.ElementTree as ET
    ETREE_VERSION = ET.VERSION
                      
ETREE_VERSION = [int(i) for i in ETREE_VERSION.split(".")]

current_path = os.path.abspath(os.getcwd())

__author__     = "Francisco Amato"
__copyright__  = "Copyright (c) 2013, Infobyte LLC"
__credits__    = ["Francisco Amato"]
__license__    = ""
__version__    = "1.0.0"
__maintainer__ = "Francisco Amato"
__email__      = "famato@infobytesec.com"
__status__     = "Development"

                           
                                                                     
                      

class OpenvasXmlParser(object):
    """
    The objective of this class is to parse an xml file generated by the openvas tool.

    TODO: Handle errors.
    TODO: Test openvas output version. Handle what happens if the parser doesn't support it.
    TODO: Test cases.

    @param openvas_xml_filepath A proper xml generated by openvas
    """
    def __init__(self, xml_output):
        self.target = None
        self.port = "80"
        self.host = None

        tree = self.parse_xml(xml_output)
        
        if tree:
            self.items = [data for data in self.get_items(tree)]
        else:
            self.items = []
            

    def parse_xml(self, xml_output):
        """
        Open and parse an xml file.

        TODO: Write custom parser to just read the nodes that we need instead of
        reading the whole file.

        @return xml_tree An xml tree instance. None if error.
        """
        try:
            tree = ET.fromstring(xml_output)
        except SyntaxError, err:
            print "SyntaxError: %s. %s" % (err, xml_output)
            return None

        return tree

    def get_items(self, tree):
        """
        @return items A list of Host instances
        """
        bugtype=""
        
                                           
        node = tree.findall('report')[0]
        node2 = node.findall('results')[0]
            
        for node in node2.findall('result'):
            yield Item(node)
                                  


                 
def get_attrib_from_subnode(xml_node, subnode_xpath_expr, attrib_name):
    """
    Finds a subnode in the item node and the retrieves a value from it

    @return An attribute value
    """
    global ETREE_VERSION
    node = None
    
    if ETREE_VERSION[0] <= 1 and ETREE_VERSION[1] < 3:
                                                           
        match_obj = re.search("([^\@]+?)\[\@([^=]*?)=\'([^\']*?)\'",subnode_xpath_expr)
        if match_obj is not None:
            node_to_find = match_obj.group(1)
            xpath_attrib = match_obj.group(2)
            xpath_value = match_obj.group(3)
            for node_found in xml_node.findall(node_to_find):
                if node_found.attrib[xpath_attrib] == xpath_value:
                    node = node_found
                    break
        else:
            node = xml_node.find(subnode_xpath_expr)

    else:
        node = xml_node.find(subnode_xpath_expr)

    if node is not None:
        return node.get(attrib_name)

    return None


                 


class Item(object):
    """
    An abstract representation of a Item


    @param item_node A item_node taken from an openvas xml tree
    """
    def __init__(self, item_node):
        self.node = item_node

        self.host = self.get_text_from_subnode('host')
        self.subnet = self.get_text_from_subnode('subnet')


        if self.subnet  is '':
            self.subnet = self.host

        self.description = self.get_text_from_subnode('description')
        self.port ="None"
        self.severity = self.get_text_from_subnode('threat')
        self.service=""
        self.protocol=""
        port = self.get_text_from_subnode('port')
       
        if (re.search("^general",port) is None):
            mregex = re.search("([\w]+) \(([\d]+)\/([\w]+)\)",port)
            if mregex is not None:
                self.service = mregex.group(1)
                self.port = mregex.group(2)
                self.protocol = mregex.group(2)
            else:
                info = port.split("/")
                self.port = info[0]
                self.protocol = info[1]                
        else:
            info = port.split("/")
            self.service = info[0]
            self.protocol = info[1]
            
            
        self.nvt = self.node.findall('nvt')[0]
        self.node = self.nvt 
        self.id=self.node.get('oid')
        self.name = self.get_text_from_subnode('name')
        self.cve = self.get_text_from_subnode('cve') if self.get_text_from_subnode('cve') != "NOCVE" else ""
        self.bid = self.get_text_from_subnode('bid') if self.get_text_from_subnode('bid') != "NOBID" else ""
        self.xref = self.get_text_from_subnode('xref') if self.get_text_from_subnode('xref') != "NOXREF" else ""
        
    def do_clean(self,value):
        myreturn =""
        if value is not None:
            myreturn = re.sub("\n","",value)
        return myreturn
        
    def get_text_from_subnode(self, subnode_xpath_expr):
        """
        Finds a subnode in the host node and the retrieves a value from it.

        @return An attribute value
        """
        sub_node = self.node.find(subnode_xpath_expr)
        if sub_node is not None and sub_node.text is not None:
            return sub_node.text

        return ''



class OpenvasPlugin(core.PluginBase):
    """
    Example plugin to parse openvas output.
    """
    def __init__(self):
        core.PluginBase.__init__(self)
        self.id              = "Openvas"
        self.name            = "Openvas XML Output Plugin"
        self.plugin_version         = "0.0.2"
        self.version   = "2.0"
        self.framework_version  = "1.0.0"
        self.options         = None
        self._current_output = None
        self.target = None
        self._command_regex  = re.compile(r'^(openvas|sudo openvas|\.\/openvas).*?')

        global current_path
        self._output_file_path = os.path.join(self.data_path,
                                             "openvas_output-%s.xml" % self._rid)
                                  

    def parseOutputString(self, output, debug = False):
        """
        This method will discard the output the shell sends, it will read it from
        the xml where it expects it to be present.

        NOTE: if 'debug' is true then it is being run from a test case and the
        output being sent is valid.
        """                                                                               

        parser = OpenvasXmlParser(output)

        web=False
        ids={}
        for item in parser.items:
            if item.name is not None:
                ref=[]
                if item.cve:
                    ref.append(item.cve.encode("utf-8"))
                if item.bid:
                    ref.append(item.bid.encode("utf-8"))
                if item.xref:
                    ref.append(item.xref.encode("utf-8"))
                
                if ids.has_key(item.subnet):
                    h_id=ids[item.host]
                else:
                    h_id = self.createAndAddHost(item.subnet)
                    ids[item.subnet] = h_id
                    
                if item.port == "None":
                    v_id = self.createAndAddVulnToHost(h_id,item.name.encode("utf-8"),desc=item.description.encode("utf-8"),
                                                       ref=ref)
                else:
                    
                    if item.service:
                        web=True if re.search(r'^(www|http)',item.service) else False
                    else:
                        web=True if item.port in ('80','443','8080') else False
                    
                    if ids.has_key(item.subnet+"_"+item.subnet):
                        i_id=ids[item.subnet+"_"+item.subnet]
                    else:

                                        
                        if self._isIPV4(item.subnet):
                            i_id = self.createAndAddInterface(h_id, item.subnet, ipv4_address=item.subnet,hostname_resolution=item.host)
                        else:
                            i_id = self.createAndAddInterface(h_id, item.subnet, ipv6_address=item.subnet,hostname_resolution=item.host)
                            
                        ids[item.subnet+"_"+item.subnet] = i_id
                        
                    
                    if ids.has_key(item.subnet+"_"+item.port):
                        s_id=ids[item.subnet+"_"+item.port]
                    else:
                        s_id = self.createAndAddServiceToInterface(h_id, i_id, item.service,
                                   item.protocol, 
                                   ports = [str(item.port)],
                                   status = "open")
                        ids[item.subnet+"_"+item.port] = s_id
                        if web:
                            n_id = self.createAndAddNoteToService(h_id,s_id,"website","")
                            n2_id = self.createAndAddNoteToNote(h_id,s_id,n_id,item.host,"")

                    if item.name:                                        
                        if web:
                            v_id = self.createAndAddVulnWebToService(h_id, s_id, item.name.encode("utf-8"),
                                                    desc=item.description.encode("utf-8"),website=item.host,
                                                    severity=item.severity.encode("utf-8"),ref=ref)
                        else:
                            v_id = self.createAndAddVulnToService(h_id, s_id, item.name.encode("utf-8"),
                                                    desc=item.description.encode("utf-8"),severity=item.severity.encode("utf-8"),ref=ref)

        del parser
        
                      
                                             
                    

    def _isIPV4(self, ip):
        if len(ip.split(".")) == 4:
            return True
        else:
            return False

                                                                              
    def processCommandString(self, username, current_path, command_string):
        return None
        

    def setHost(self):
        pass


def createPlugin():
    return OpenvasPlugin()

if __name__ == '__main__':
    parser = OpenvasXmlParser(sys.argv[1])
    for item in parser.items:
        if item.status == 'up':
            print item
