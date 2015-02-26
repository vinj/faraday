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

                           
                                                                     
                      

class BurpXmlParser(object):
    """
    The objective of this class is to parse an xml file generated by the burp tool.

    TODO: Handle errors.
    TODO: Test burp output version. Handle what happens if the parser doesn't support it.
    TODO: Test cases.

    @param burp_xml_filepath A proper xml generated by burp
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
        
        for node in tree.findall('issue'):
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


    @param item_node A item_node taken from an burp xml tree
    """
    def __init__(self, item_node):
        self.node = item_node

        name = item_node.findall('name')[0]
        host_node = item_node.findall('host')[0]
        path = item_node.findall('path')[0]
        location = item_node.findall('location')[0]
        severity = item_node.findall('severity')[0]
        request = item_node.findall('./requestresponse/request')[0].text if len(item_node.findall('./requestresponse/request'))  >0  else ""
        response = item_node.findall('./requestresponse/response')[0].text if len(item_node.findall('./requestresponse/response')) > 0 else ""

        detail = self.do_clean(item_node.findall('issueDetail'))
        remediation = self.do_clean(item_node.findall('remediationBackground'))
        
        self.url=host_node.text
        rhost = re.search("(http|https|ftp)\://([a-zA-Z0-9\.\-]+(\:[a-zA-Z0-9\.&amp;%\$\-]+)*@)*((25[0-5]|2[0-4][0-9]|[0-1]{1}[0-9]{2}|[1-9]{1}[0-9]{1}|[1-9])\.(25[0-5]|2[0-4][0-9]|[0-1]{1}[0-9]{2}|[1-9]{1}[0-9]{1}|[1-9]|0)\.(25[0-5]|2[0-4][0-9]|[0-1]{1}[0-9]{2}|[1-9]{1}[0-9]{1}|[1-9]|0)\.(25[0-5]|2[0-4][0-9]|[0-1]{1}[0-9]{2}|[1-9]{1}[0-9]{1}|[0-9])|localhost|([a-zA-Z0-9\-]+\.)*[a-zA-Z0-9\-]+\.(com|edu|gov|int|mil|net|org|biz|arpa|info|name|pro|aero|coop|museum|[a-zA-Z]{2}))[\:]*([0-9]+)*([/]*($|[a-zA-Z0-9\.\,\?\'\\\+&amp;%\$#\=~_\-]+)).*?$", self.url)
        self.protocol = rhost.group(1)
        self.host = rhost.group(4)
        
        self.port=80
        if self.protocol == 'https':
            self.port=443
            
        if rhost.group(11) is not None:
            self.port = rhost.group(11)
       
        self.name = name.text
        self.location = location.text
        self.path = path.text

        self.ip = host_node.get('ip')
        self.url = self.node.get('url')
        self.severity = severity.text
        self.request = request
        self.response = response
        self.detail = detail
        self.remediation = remediation 
    
    
    def do_clean(self,value):
        myreturn =""
        if value is not None:
            if len(value) > 0:
                myreturn = value[0].text
        return myreturn
        
    def get_text_from_subnode(self, subnode_xpath_expr):
        """
        Finds a subnode in the host node and the retrieves a value from it.

        @return An attribute value
        """
        sub_node = self.node.find(subnode_xpath_expr)
        if sub_node is not None:
            return sub_node.text

        return None



class BurpPlugin(core.PluginBase):
    """
    Example plugin to parse burp output.
    """
    def __init__(self):
        core.PluginBase.__init__(self)
        self.id              = "Burp"
        self.name            = "Burp XML Output Plugin"
        self.plugin_version         = "0.0.2"
        self.version   = "1.6.05 BurpPro"
        self.framework_version  = "1.0.0"
        self.options         = None
        self._current_output = None
        self.target = None
        self._command_regex  = re.compile(r'^(sudo burp|\.\/burp).*?')

        global current_path
        self._output_file_path = os.path.join(self.data_path,
                                             "burp_output-%s.xml" % self._rid)
                                  

    def parseOutputString(self, output, debug = False):
        
        parser = BurpXmlParser(output)
        for item in parser.items:

            h_id = self.createAndAddHost(item.ip)
            i_id = self.createAndAddInterface(h_id, item.ip,ipv4_address=item.ip, hostname_resolution=item.host)
            s_id = self.createAndAddServiceToInterface(h_id, i_id, item.protocol,
                                                "tcp",
                                                ports = [str(item.port)],
                                                status = "open")
            
                         
            n_id = self.createAndAddNoteToService(h_id,s_id,"website","")
            n2_id = self.createAndAddNoteToNote(h_id,s_id,n_id,item.host,"")
            
                               
            item.response=""
            desc=item.detail
            resolution=item.remediation if item.remediation else ""

            v_id = self.createAndAddVulnWebToService(h_id, s_id, item.name,
                                                     desc=desc,severity=item.severity,website=item.host,
                                                     path=item.path,request=item.request,response=item.response,
                                                     resolution=resolution)

        del parser
        
    def processCommandString(self, username, current_path, command_string):
        return None
        

    def setHost(self):
        pass


def createPlugin():
    return BurpPlugin()

if __name__ == '__main__':
    parser = BurpXmlParser(sys.argv[1])
    for item in parser.items:
        if item.status == 'up':
            print item
