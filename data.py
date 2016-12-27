# -*- coding: utf-8 -*-
"""
Created on Tue Dec 06 00:16:27 2016
Stand-alone extract from ProjectCode.ipynb to audit, clean and convert to CSV

@author: eric
"""

# Importing libraries
import xml.etree.cElementTree as ET
import pprint
import re
from collections import defaultdict
import csv
import codecs
import cerberus
import schema

# Creating sample file as original OSM is 424 MB unzipped.
# Parameter: take every k-th top level element
# I used k = 8 for my sample file to reach the required minimum size of 50 MB (~53 MB) as
# indicated in Project Specification
# https://review.udacity.com/#!/rubrics/25/view

#OSM_FILE = "boston_massachusetts.osm"
#SAMPLE_FILE = "boston_massachusetts_sample.osm"
#
#k = 8
#
#def get_element(osm_file, tags=('node', 'way', 'relation')):
#    '''Yield element if it is the right type of tag
#
#    Reference:
#    http://stackoverflow.com/questions/3095434/inserting-newlines-in-xml-file-generated-via-xml-etree-elementtree-in-python
#    '''
#    context = iter(ET.iterparse(osm_file, events=('start', 'end')))
#    _, root = next(context)
#    for event, elem in context:
#        if event == 'end' and elem.tag in tags:
#            yield elem
#            root.clear()
#
#
#with open(SAMPLE_FILE, 'wb') as output:
#    output.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
#    output.write(b'<osm>\n  ')
#
#    # Write every kth top level element
#    for i, element in enumerate(get_element(OSM_FILE)):
#        if i % k == 0:
#            output.write(ET.tostring(element, encoding='utf-8'))
#
#    output.write(b'</osm>')


''' STEP #1: Load dataset and search for incorrect street abbreviations.

As a first step, the dataset is searched for incorrect abbreviations of street suffix.
ex: 'St' in 'Main St'.
Reference: USPS Street Suffix Abbreviations
http://pe.usps.gov/text/pub28/28apc_002.htm
'''

# Load the sample OSM file as provided in GitHub repository
OSMFILE = "boston_massachusetts_sample.osm"
street_type_re = re.compile(r'\b\S+\.?$', re.IGNORECASE)

expected = ["Street", "Avenue", "Boulevard", "Drive", "Court", "Place", "Square", "Lane", "Road", 
            "Trail", "Parkway", "Commons", "Way", "Circle", "Terrace", "Bend", "Manor", "Run", "Highway",
            "Isle", "Hollow", "Cove", "Lake", "Trace", "Crescent"]


# Create a group of auditing functions for street suffix
def audit_street_type(street_types, street_name):
    '''Checks if street name contains incorrect abbreviations, if so, adds it to the dictionary.'''
    m = street_type_re.search(street_name)
    if m:
        street_type = m.group()
        if street_type not in expected:
            street_types[street_type].add(street_name)

def is_street_name(elem):
    '''Returns a Boolean value'''
    return (elem.attrib['k'] == "addr:street")

def audit(osmfile):
    '''Iterates through document tags, and returns dictionary
    of incorrect abbreviations (keys) and street names (value) that contain these abbreviations.
    '''
    osm_file = open(osmfile, "r")
    street_types = defaultdict(set)
    for event, elem in ET.iterparse(osm_file, events=("start",)):
        if elem.tag == "node" or elem.tag == "way":
            for tag in elem.iter("tag"):
                if is_street_name(tag):
                    audit_street_type(street_types, tag.attrib['v'])
    osm_file.close()
    return street_types
# Run audit and print results
st_types = audit(OSMFILE)
pprint.pprint(dict(st_types))


# Function to correct street names using wrong suffix
def update_name(name, mapping):
    '''Substitutes incorrect abbreviation with correct one.'''
    m = street_type_re.search(name)
    if m:
        street_type = m.group()
        temp= 0
        try:
            temp = int(street_type)
        except:
            pass
        if street_type not in expected and temp == 0:
            try:
                name = re.sub(street_type_re, mapping[street_type], name)
            except:
                pass
    return name


# Dictionary mapping incorrect abbreviations to correct one.
mapping = { "St": "Street",
            "St.": "Street",
            "ST": "Street",
            "st": "Street",
            "Rd.": "Road",
            "Rd": "Road",
            "RD": "Road",
            "Ave": "Avenue",
            "Ave.": "Avenue",
            "Blvd": "Boulevard",
            "BLVD": "Boulevard",
            "Cir": "Circle",
            "Ct": "Court",
            "Dr": "Drive",
            "Trl": "Trail",
            "Ter": "Terrace",
            "Pl": "Place",
            "Pkwy": "Parkway",
            "Bnd": "Bend",
            "Mnr": "Manor",
            "Ln": "Lane",
            "street": "Street",
            "AVE": "Avenue",
            "Blvd.": "Boulevard",
            "Cirlce": "Circle",
            "DRIVE": "Drive",
            "Cv": "Cove",
            "Dr.": "Drive",
            "Druve": "Drive",
            "Holw": "Hollow",
            "Hwy": "Highway",
            "HWY": "Highway",
            "Pt": "Point",
            "Trce": "Trace",
            "ave": "Avenue",
            "Cres": "Crescent"
}


# Apply corrections where incorrect detected v. mapping.
for st_type, ways in st_types.iteritems():
    for name in ways:
        better_name = update_name(name, mapping)
        print name, "=>", better_name



''' STEP #2: Checking format and compatibility of postal codes with the area

US postal codes follow the 5-digit format.
Some codes may differ due to additional signs such as 'MA 02118' or '02136-2460'.
Also some postal codes may not be compatible with the Boston, MA area codes who start with "01xxx" or "02xxx".
Such as '03079' (Salem in New Hampshire).
Or they represent some other entry, such as '(617) 495-1000' is a phone number (Harvard U.).

Note: some of these discrepancies may not appear in the sample file but are present in
the original 424 MB OSM file.
'''

# Create a group of auditing functions for postal codes
def audit_postcode(post_code, digits):
    '''Checks if postal code is incompatible and adds it to the list if so.'''
    if len(digits) != 5 or (digits[0:2] != '01' and digits[0:2] != '02'):
        post_code.append(digits)

def is_postalcode(elem):
    '''Returns a Boolean value.'''
    return (elem.attrib['k'] == "addr:postcode")

def audit(osmfile):
    '''Iterates and returns list of inconsistent postal codes found in the document.'''
    osm_file = open(osmfile, "r")
    post_code = []
    for event, elem in ET.iterparse(osm_file, events=("start",)):
        if elem.tag == "node" or elem.tag == "way":
            for tag in elem.iter("tag"):
                if is_postalcode(tag):
                    audit_postcode(post_code, tag.attrib['v'])
    osm_file.close()
    return post_code


# Run audit and print results
postal_codes = audit(OSMFILE)
print postal_codes


# Function to correct format of postal codes
def update_zip(post_code):
    '''Extracts 5-digit postal codes from postal codes in different formats
    and deletes postal codes that do not correspond to Massachussets area.'''
    if post_code[0:2] == 'Ma' or post_code[0:2] == 'MA':
        post_code = post_code[3:].strip()
    if len(post_code) >5 and len(post_code) == 10 and (post_code[0:2] == '01' or post_code[0:2] == '02'):
        post_code = post_code[0:5]
    elif len(post_code) < 5 or (post_code[0:2] != '01' and post_code[0:2] != '02') :
        post_code = ''
    elif len(post_code) > 5 and post_code[5]==' ':
        post_code = post_code[0:5]
    elif len(post_code)>5:
        post_code = ''
    return post_code


# Apply corrections where incorrect detected
for code in postal_codes:
    better_code = update_zip(code)
    print code, "=>", better_code



''' STEP #3: Analyzing U.S. state entry

All state entries should either contain the official abbreviation for Massachusetts, 'MA',
as opposed to 'Mass', 'mass', 'ma', and 'Ma' to 'MA';
or an empty string, if the state entry is not related to 'MA', such as 'New York', 'NH', ...
'''

# Create a group of auditing functions for state entry
def audit_state(states, state):
    '''Checks if state entry is inconsistent and, if so, adds it to the list.'''
    if state != 'MA':
        states.append(state)

def is_state(elem):
    '''Returns a Boolean value.'''
    return (elem.attrib['k'] == "addr:state")

def audit(osmfile):
    '''Iterates and returns list of inconsistent state entris found in the document.'''
    osm_file = open(osmfile, "r")
    states = []
    for event, elem in ET.iterparse(osm_file, events=("start",)):
        if elem.tag == "node" or elem.tag == "way":
            for tag in elem.iter("tag"):
                if is_state(tag):
                    audit_state(states, tag.attrib['v'])
    osm_file.close()
    return states


# Run audit and print results
states = audit(OSMFILE)
print states


# Function to correct state entries
def update_state(state):
    '''Deletes U.S. state entries not related to Massachussets and formats all remaining to 'MA'.'''
    if state.startswith('ma') or state.startswith('Ma') or state.startswith('MA') or state == 'M':
        state = 'MA'
    else:
        state = ''
    return state


# Apply corrections where incorrect detected
for state in states:
    better_state = update_state(state)
    print state, "=>", better_state



''' STEP #4: Convert XML to CSV format

Using some code from the "Case Study: OpenStreetMap Data[SQL]".
Follows the schema provided in Project Details instructions
https://gist.github.com/swwelch/f1144229848b407e0a5d13fcb7fbbd6f '''


NODES_PATH = "nodes.csv"
NODE_TAGS_PATH = "nodes_tags.csv"
WAYS_PATH = "ways.csv"
WAY_NODES_PATH = "ways_nodes.csv"
WAY_TAGS_PATH = "ways_tags.csv"


NODE_FIELDS = ['id', 'lat', 'lon', 'user', 'uid', 'version', 'changeset', 'timestamp']
NODE_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_FIELDS = ['id', 'user', 'uid', 'version', 'changeset', 'timestamp']
WAY_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_NODES_FIELDS = ['id', 'node_id', 'position']


# Regular expression compiler patterns.
LOWER_COLON = re.compile(r'^([a-z]|_)+:([a-z]|_)+')
PROBLEMCHARS = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')
SCHEMA = schema.schema


# Check if input element is a "node" or a "way" then clean, shape and parse to corresponding dictionary.
def shape_element(element, node_attr_fields=NODE_FIELDS, way_attr_fields=WAY_FIELDS,
                  problem_chars=PROBLEMCHARS, default_tag_type='regular'):
    '''Clean and shape node or way XML element to Python dict'''
    node_attribs = {}
    way_attribs = {}
    way_nodes = []
    tags = []  # Handle secondary tags the same way for both node and way elements

    if element.tag == 'node':
        for field in node_attr_fields:
            node_attribs[field] = element.attrib[field]

    if element.tag == 'way':
        for field in way_attr_fields:
            way_attribs[field] = element.attrib[field]
        position = 0
        temp = {}
        for tag in element.iter("nd"):
            temp['id'] = element.attrib["id"]
            temp['node_id'] = tag.attrib["ref"]
            temp['position'] = position
            position += 1
            way_nodes.append(temp.copy())

    temp = {}

    for tag in element.iter("tag"):
        temp['id'] = element.attrib["id"]
        if ":" in tag.attrib["k"]:
            newKey = re.split(":",tag.attrib["k"],1)
            temp['key'] = newKey[1]
            if temp['key'] == 'postcode':
                temp['value'] = update_zip(tag.attrib["v"])
            elif temp['key'] == 'state':
                temp['value'] = update_state(tag.attrib["v"])
            elif temp['key'] == 'street':
                temp['value'] = update_name(tag.attrib["v"],mapping)
            else:
                temp['value'] = tag.attrib["v"]
            temp["type"] = newKey[0]
        else:
            temp['key'] = tag.attrib["k"]
            if temp['key'] == 'postcode':
                temp['value'] = update_zip(tag.attrib["v"])
            elif temp['key'] == 'state':
                temp['value'] = update_state(tag.attrib["v"])
            elif temp['key'] == 'street':
                temp['value'] = update_name(tag.attrib["v"],mapping)
            else:
                temp['value'] = tag.attrib["v"]
            temp["type"] = default_tag_type
        tags.append(temp.copy())

    if element.tag == 'node':
        return {'node': node_attribs, 'node_tags': tags}
    elif element.tag == 'way':
        return {'way': way_attribs, 'way_nodes': way_nodes, 'way_tags': tags}


# ================================================== #
#               Helper Functions                     #
# ================================================== #
def get_element(osm_file, tags=('node', 'way', 'relation')):
    '''Yield element if it is the right type of tag'''
    context = ET.iterparse(osm_file, events=('start', 'end'))
    _, root = next(context)
    for event, elem in context:
        if event == 'end' and elem.tag in tags:
            yield elem
            root.clear()

def validate_element(element, validator, schema=SCHEMA):
    '''Raise ValidationError if element does not match schema'''
    if validator.validate(element, schema) is not True:
        field, errors = next(validator.errors.iteritems())
        message_string = "\nElement of type '{0}' has the following errors:\n{1}"
        error_strings = (
            "{0}: {1}".format(k, v if isinstance(v, str) else ", ".join(v))
            for k, v in errors.iteritems()
        )
        raise cerberus.ValidationError(
            message_string.format(field, "\n".join(error_strings))
        )

class UnicodeDictWriter(csv.DictWriter, object):
    '''Extend csv.DictWriter to handle Unicode input'''

    def writerow(self, row):
        super(UnicodeDictWriter, self).writerow({
            k: (v.encode('utf-8') if isinstance(v, unicode) else v) for k, v in row.iteritems()
        })

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


# ================================================== #
#               Main Function                        #
# ================================================== #
def process_map(file_in, validate):
    '''Iteratively process each XML element and write to csv(s)'''

    with codecs.open(NODES_PATH, 'w') as nodes_file, \
         codecs.open(NODE_TAGS_PATH, 'w') as nodes_tags_file, \
         codecs.open(WAYS_PATH, 'w') as ways_file, \
         codecs.open(WAY_NODES_PATH, 'w') as way_nodes_file, \
         codecs.open(WAY_TAGS_PATH, 'w') as way_tags_file:

        nodes_writer = UnicodeDictWriter(nodes_file, NODE_FIELDS)
        node_tags_writer = UnicodeDictWriter(nodes_tags_file, NODE_TAGS_FIELDS)
        ways_writer = UnicodeDictWriter(ways_file, WAY_FIELDS)
        way_nodes_writer = UnicodeDictWriter(way_nodes_file, WAY_NODES_FIELDS)
        way_tags_writer = UnicodeDictWriter(way_tags_file, WAY_TAGS_FIELDS)

        nodes_writer.writeheader()
        node_tags_writer.writeheader()
        ways_writer.writeheader()
        way_nodes_writer.writeheader()
        way_tags_writer.writeheader()

        validator = cerberus.Validator()

        for element in get_element(file_in, tags=('node', 'way')):
            el = shape_element(element)
            if el:
                if validate is True:
                    validate_element(el, validator)

                if element.tag == 'node':
                    nodes_writer.writerow(el['node'])
                    node_tags_writer.writerows(el['node_tags'])
                elif element.tag == 'way':
                    ways_writer.writerow(el['way'])
                    way_nodes_writer.writerows(el['way_nodes'])
                    way_tags_writer.writerows(el['way_tags'])


process_map(OSMFILE, validate=False)




































    
    
