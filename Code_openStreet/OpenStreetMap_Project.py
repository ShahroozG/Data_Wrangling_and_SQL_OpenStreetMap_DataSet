
# coding: utf-8

# ### Necessary Libraries

# In[1]:

import xml.etree.cElementTree as ET
import pprint
import re
from collections import defaultdict
import csv
import codecs
import cerberus
import schemaa
import string
import phonenumbers
import requests
import validators
import sqlite3


# ### SourceFiles

# In[2]:

OSM_FILE = "C:/Users/Shahrooz/Desktop/OpenStreetMap/DataSource_openStreet/santaMonica.osm"
SAMPLE_FILE = "C:/Users/Shahrooz/Desktop/OpenStreetMap/DataSource_openStreet/sampleSantaMonica.osm"


# ### Looking at Smaller dataset

# In[15]:

k = 10 # Parameter: take every k-th top level element

def get_element(osm_file, tags=('node', 'way', 'relation')):
    """Yield element if it is the right type of tag

    Reference:
    http://stackoverflow.com/questions/3095434/inserting-newlines-in-xml-file-generated-via-xml-etree-elementtree-in-python
    """
    context = iter(ET.iterparse(osm_file, events=('start', 'end')))
    _, root = next(context)
    for event, elem in context:
        if event == 'end' and elem.tag in tags:
            yield elem
            root.clear()


with open(SAMPLE_FILE, 'wb') as output:
    output.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    output.write('<osm>\n  ')

    # Write every kth top level element
    for i, element in enumerate(get_element(OSM_FILE)):
        if i % k == 0:
            output.write(ET.tostring(element, encoding='utf-8'))

    output.write('</osm>')


# ###  Tags Variety

# In[16]:

# Counting different tags names in the OSM file:
# reference: Data Wrangling Course-Udacity
def count_tags(filename):
    output = defaultdict(int)
    for event, elem in ET.iterparse(filename):
        output[elem.tag] += 1
    return output

print "Tags Numbers: "
count_tags(OSM_FILE)


# ### Number of Contributers in this Map

# In[3]:

# Creating a set that contains contributers(Users) in this Map
# reference: Data Wrangling Course-Udacity

def process_map_users(filename):
    users = set()
    
    for _, element in ET.iterparse(filename):
        try:
            users.add(element.attrib['uid'])
        except KeyError:
            pass

    return users


# In[4]:

users = process_map_users(OSM_FILE)
print 'Number of Contributers: ', len(users)


# ### Tags Patterns

# In[5]:

# looking at tags Pattern and find how many of each we have in our OSM file;
# reference: Data Wrangling Course-Udacity

lower = re.compile(r'^([a-z]|_)*$')
lower_colon = re.compile(r'^([a-z]|_)*:([a-z]|_)*$')
problemchars = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')


def key_type(element, keys):
    if element.tag == "tag":
        k_value = element.attrib['k']
        
        if lower.search(k_value):
            keys["lower"] += 1
        elif lower_colon.search(k_value):
            keys["lower_colon"] += 1
        elif problemchars.search(k_value):
            keys["problemchars"] += 1
        else:
            keys["other"] += 1
        
    return keys

# in this function first we put keys as a dictionary with 0 values. So it is initializred and when I use key_type
# function I will traverse on all tags and increment the number of each category;

def process_map_tag_type(filename):
    keys = {"lower": 0, "lower_colon": 0, "problemchars": 0, "other": 0}
    for _, element in ET.iterparse(filename):
        keys = key_type(element, keys)

    return keys

keys = process_map_tag_type(OSM_FILE)
print "Tags Patterns are: "
pprint.pprint(keys)


# ### Types of : Street, State, Zip Code, HouseNumber, Phone

# In[7]:

# Which Street type are in the file?
# Street audit reference: Data Wrangling Course-Udacity

osm_file = open(OSM_FILE, "r")

street_type_re = re.compile(r'\b([a-z])+\.?$', re.IGNORECASE)
housenumber_type_re = re.compile(r'^\d+(-?\d)*$')

street_types = defaultdict(int)
def audit_street_type(street_types, street_name):
    m = street_type_re.search(street_name)
    if m:
        street_type = m.group()
        street_types[street_type] += 1
        
state_types = defaultdict(int)
def audit_state_type(state_types, state):
    state_types[state] += 1        

postcode_types = defaultdict(int)
def audit_postcode(postcode_types, postcode):
    postcode_types[postcode] += 1

problemNumbers = []
def audit_housenumber(problemNumbers, number):
    m = housenumber_type_re.search(number)
    if not m:
        problemNumbers.append(number)

notValidPhones = []
def audit_phone(notValidPhones, phone):
    if phone.startswith("+"):
        phone = phone[1:]
    z = phonenumbers.parse(phone, "US")
    v = phonenumbers.is_possible_number(z)
    if not v:
        notValidPhones.append(phone)

# This function is based on request method and it catches many valid websites; So I don't use it and use the other function
# but the idea behind it is good and it's about how to use request method so I keep it here for learning purposes;
#problemWebsite = set()
#def audit_website(problemWebsite, website): 
#    if not website.startswith('http'):
#        website = 'http://' + website
#    try:
#        request = requests.get(website)
#        if request.status_code != 200:
#            problemWebsite.add(website)
#    except:
#        problemWebsite.add(website)

problemWebsite = []
def audit_website(problemWebsite, website):
    if not website.startswith('http'):
        website = 'http://' + website
    if not validators.url(website):
        problemWebsite.append(website)
    
def is_street_name(elem):
    return (elem.tag == "tag") and (elem.attrib['k'] == "addr:street")

def is_state(elem):
    return (elem.tag == "tag") and (elem.attrib['k'] == "addr:state" or elem.attrib['k'] == "is_in:state_code")

def is_postcode(elem):
    return (elem.tag == "tag") and (elem.attrib['k'] == "addr:postcode")

def is_housenumber(elem):
    return (elem.tag == "tag") and (elem.attrib['k'] == "addr:housenumber")

def is_phone(elem):
    return (elem.tag == "tag") and (elem.attrib['k'] == 'phone')

def is_website(elem):
    return (elem.tag == "tag") and (elem.attrib['k'] == "website" or elem.attrib['k'] == "url" or                                     (elem.attrib['k'] == "source" and elem.attrib['v'].startswith("http")))


def audit():
    for event, elem in ET.iterparse(osm_file):
        if is_street_name(elem):
            audit_street_type(street_types, elem.attrib['v'])
        elif is_state(elem):
            audit_state_type(state_types, elem.attrib['v'])
        elif is_postcode(elem):
            audit_postcode(postcode_types, elem.attrib['v'])
        elif is_housenumber(elem):
            audit_housenumber(problemNumbers, elem.attrib['v'])
        elif is_phone(elem):
            audit_phone(notValidPhones, elem.attrib['v'])
        elif is_website(elem):
            audit_website(problemWebsite, elem.attrib['v'])
        
    print "Street Types: "        
    pprint.pprint(street_types)
    print""
    print "State Types: "
    pprint.pprint(state_types)
    print""
    print "PostCode Types: "
    pprint.pprint(postcode_types)
    print""
    print "Problematic House Numbers: "
    pprint.pprint(problemNumbers)
    print""
    print "Problematic Phone Numbers: "
    pprint.pprint(notValidPhones)
    print""
    print "Problematic Website addresses: "
    pprint.pprint(problemWebsite)

audit()


# ### Improving Data Quality

# In[3]:

# reference for Street Part: Data Wrangling Course-Udacity
street_type_re = re.compile(r'\b([a-z])+\.?$', re.IGNORECASE)

# catching direction abbreviations at the first of an address: E, W, N, S
street_abbrev_re = re.compile(r'^([a-z]){1}\.?(\s)+', re.IGNORECASE)

# catching house numbers as part of street address
housenumber_in_street_re = re.compile(r'^(\d)+(\s)+')

expected = ["Street", "Avenue", "Boulevard", "Drive", "Court", "Place", "Square", "Lane", "Road", 
            "Trail", "Parkway", "Commons", "Broadway", "Promenade", "Way", "Highway", "Walk"]

# I consider the file and found problematic street names and create this map
mapping_street = { "St": "Street",
            "St.": "Street",
            "Ave": "Avenue",
            "Rd.": "Road",
            "Blvd" : "Boulevard",
            "Blvd." : "Boulevard",
            "Bd." : "Boulevard",
            "Bvd" : "Boulevard",
            "Dr" : "Drive",
            "Ln" : "Lane",
            "Pico" : "Pico Boulevard",
            "Sepulveda" : "Sepulveda Boulevard",
            "Center" : "Center Drive",
            }

mapping_abbrev = { 'W ': 'West ', 'S ': 'South ', 'N ': 'North ', 'E ': 'East ',                   'W. ': 'West ', 'S. ': 'South', 'N. ': 'North ', 'E. ': 'East '}

state_list = ["Ca", "CA,"]

def audit_street_type(street_types, street_name):
    m = street_type_re.search(street_name)
    if m:
        street_type = m.group()
        if street_type not in expected:
            street_types[street_type].add(street_name)


def is_street_name(elem):
    return (elem.attrib['k'] == "addr:street")


def audit(osmfile):
    osm_file = open(osmfile, "r")
    street_types = defaultdict(set)
    for event, elem in ET.iterparse(osm_file, events=("start",)):
        if elem.tag == "node" or elem.tag == "way":
            for tag in elem.iter("tag"):
                if is_street_name(tag):
                    # this is an exception in our street naming: Donald Douglas Loop North and Donald Douglas Loop South are 
                    # Corrcet addresses and I don't want to change them;
                    if not tag.attrib['v'].startswith("Donald Douglas Loop"):
                        audit_street_type(street_types, tag.attrib['v'])
    osm_file.close()
    return street_types


def update_name(name, mapping_street, mapping_abbrev):
    m = street_type_re.search(name)
    if m:
        street_type = m.group()
        #If the name exist in mapping keys, it means that's a problem and we should fix it.
        if street_type in mapping_street.keys():
            name = re.sub(street_type, mapping_street[street_type], name)
    # Updating W , E, N, S to West, East, North, South; if they are at the begining of an address.
    m_1 = street_abbrev_re.search(name)
    if m_1:
        street_abbrev = m_1.group()
        if street_abbrev in mapping_abbrev.keys():
            name = re.sub(street_abbrev, mapping_abbrev[street_abbrev], name)
    # capitalizing first letter of all words in problematic address
    name = string.capwords(name)
    return name


def update_state(state, state_list):
    if state in state_list:
        state = "CA"
    return state


# In[4]:

st_types = audit(OSM_FILE)
pprint.pprint(dict(st_types))
print ""

for st_type, ways in st_types.iteritems():
    for name in ways:
        better_name = update_name(name, mapping_street, mapping_abbrev)
        print name, "=>", better_name


# ### Fixing problems and Preparing Data for Database

# In[5]:

"""
After auditing is complete the next step is to prepare the data to be inserted into a SQL database.
To do so you will parse the elements in the OSM XML file, transforming them from document format to
tabular format, thus making it possible to write to .csv files.  These csv files can then easily be
imported to a SQL database as tables.

The process for this transformation is as follows:
- Use iterparse to iteratively step through each top level element in the XML
- Shape each element into several data structures using a custom function
- Utilize a schema and validation library to ensure the transformed data is in the correct format
- Write each data structure to the appropriate .csv files

We've already provided the code needed to load the data, perform iterative parsing and write the
output to csv files. Your task is to complete the shape_element function that will transform each
element into the correct format. To make this process easier we've already defined a schema (see
the schema.py file in the last code tab) for the .csv files and the eventual tables. Using the 
cerberus library we can validate the output against this schema to ensure it is correct.

## Shape Element Function
The function should take as input an iterparse Element object and return a dictionary.

### If the element top level tag is "node":
The dictionary returned should have the format {"node": .., "node_tags": ...}

The "node" field should hold a dictionary of the following top level node attributes:
- id
- user
- uid
- version
- lat
- lon
- timestamp
- changeset
All other attributes can be ignored

The "node_tags" field should hold a list of dictionaries, one per secondary tag. Secondary tags are
child tags of node which have the tag name/type: "tag". Each dictionary should have the following
fields from the secondary tag attributes:
- id: the top level node id attribute value
- key: the full tag "k" attribute value if no colon is present or the characters after the colon if one is.
- value: the tag "v" attribute value
- type: either the characters before the colon in the tag "k" value or "regular" if a colon
        is not present.

Additionally,

- if the tag "k" value contains problematic characters, the tag should be ignored
- if the tag "k" value contains a ":" the characters before the ":" should be set as the tag type
  and characters after the ":" should be set as the tag key
- if there are additional ":" in the "k" value they and they should be ignored and kept as part of
  the tag key. For example:

  <tag k="addr:street:name" v="Lincoln"/>
  should be turned into
  {'id': 12345, 'key': 'street:name', 'value': 'Lincoln', 'type': 'addr'}

- If a node has no secondary tags then the "node_tags" field should just contain an empty list.

The final return value for a "node" element should look something like:

{'node': {'id': 757860928,
          'user': 'uboot',
          'uid': 26299,
       'version': '2',
          'lat': 41.9747374,
          'lon': -87.6920102,
          'timestamp': '2010-07-22T16:16:51Z',
      'changeset': 5288876},
 'node_tags': [{'id': 757860928,
                'key': 'amenity',
                'value': 'fast_food',
                'type': 'regular'},
               {'id': 757860928,
                'key': 'cuisine',
                'value': 'sausage',
                'type': 'regular'},
               {'id': 757860928,
                'key': 'name',
                'value': "Shelly's Tasty Freeze",
                'type': 'regular'}]}

### If the element top level tag is "way":
The dictionary should have the format {"way": ..., "way_tags": ..., "way_nodes": ...}

The "way" field should hold a dictionary of the following top level way attributes:
- id
-  user
- uid
- version
- timestamp
- changeset

All other attributes can be ignored

The "way_tags" field should again hold a list of dictionaries, following the exact same rules as
for "node_tags".

Additionally, the dictionary should have a field "way_nodes". "way_nodes" should hold a list of
dictionaries, one for each nd child tag.  Each dictionary should have the fields:
- id: the top level element (way) id
- node_id: the ref attribute value of the nd tag
- position: the index starting at 0 of the nd tag i.e. what order the nd tag appears within
            the way element

The final return value for a "way" element should look something like:

{'way': {'id': 209809850,
         'user': 'chicago-buildings',
         'uid': 674454,
         'version': '1',
         'timestamp': '2013-03-13T15:58:04Z',
         'changeset': 15353317},
 'way_nodes': [{'id': 209809850, 'node_id': 2199822281, 'position': 0},
               {'id': 209809850, 'node_id': 2199822390, 'position': 1},
               {'id': 209809850, 'node_id': 2199822392, 'position': 2},
               {'id': 209809850, 'node_id': 2199822369, 'position': 3},
               {'id': 209809850, 'node_id': 2199822370, 'position': 4},
               {'id': 209809850, 'node_id': 2199822284, 'position': 5},
               {'id': 209809850, 'node_id': 2199822281, 'position': 6}],
 'way_tags': [{'id': 209809850,
               'key': 'housenumber',
               'type': 'addr',
               'value': '1412'},
              {'id': 209809850,
               'key': 'street',
               'type': 'addr',
               'value': 'West Lexington St.'},
              {'id': 209809850,
               'key': 'street:name',
               'type': 'addr',
               'value': 'Lexington'},
              {'id': '209809850',
               'key': 'street:prefix',
               'type': 'addr',
               'value': 'West'},
              {'id': 209809850,
               'key': 'street:type',
               'type': 'addr',
               'value': 'Street'},
              {'id': 209809850,
               'key': 'building',
               'type': 'regular',
               'value': 'yes'},
              {'id': 209809850,
               'key': 'levels',
               'type': 'building',
               'value': '1'},
              {'id': 209809850,
               'key': 'building_id',
               'type': 'chicago',
               'value': '366409'}]}
"""

OSM_PATH = "C:/Users/Shahrooz/Desktop/OpenStreetMap/DataSource_openStreet/santaMonica.osm"

NODES_PATH = "C:/Users/Shahrooz/Desktop/OpenStreetMap/DataSource_openStreet/nodes.csv"
NODE_TAGS_PATH = "C:/Users/Shahrooz/Desktop/OpenStreetMap/DataSource_openStreet/nodes_tags.csv"
WAYS_PATH = "C:/Users/Shahrooz/Desktop/OpenStreetMap/DataSource_openStreet/ways.csv"
WAY_NODES_PATH = "C:/Users/Shahrooz/Desktop/OpenStreetMap/DataSource_openStreet/ways_nodes.csv"
WAY_TAGS_PATH = "C:/Users/Shahrooz/Desktop/OpenStreetMap/DataSource_openStreet/ways_tags.csv"

LOWER_COLON = re.compile(r'^([a-z]|_)+:([a-z]|_)+')
PROBLEMCHARS = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')
# finding housenumber in addreses
housenumber_in_street_re = re.compile(r'^(\d)+(\s)+')
# finding ste or suite phrase in street address
ste_re = re.compile(r'ste', re.IGNORECASE)
suite_re = re.compile(r'suite', re.IGNORECASE)
# an expression for catching state in postcode; like: CA 90405;
state_in_postcode_re = re.compile(r'^([A-Z]){2}\s{1}', re.IGNORECASE)

# loading schema from schemaa file; The schemaa file is placed in the same directory that this notebook is placed;
SCHEMA = schemaa.schema

# Make sure the fields order in the csvs matches the column order in the sql table schema
NODE_FIELDS = ['id', 'lat', 'lon', 'user', 'uid', 'version', 'changeset', 'timestamp']
NODE_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_FIELDS = ['id', 'user', 'uid', 'version', 'changeset', 'timestamp']
WAY_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_NODES_FIELDS = ['id', 'node_id', 'position']

def add_new_line(key, value, tags, element, types = 'addr'):
    temp= {}
    temp['id'] = element.attrib['id']
    temp['key'] = key
    temp['type'] = types
    # using Uppercase for first letter of all words
    temp['value'] = string.capwords(value)
    tags.append(temp)

def shape_element(element, node_attr_fields=NODE_FIELDS, way_attr_fields=WAY_FIELDS,
                  problem_chars=PROBLEMCHARS, default_tag_type='regular'):
    """Clean and shape node or way XML element to Python dict"""

    node_attribs = {}
    way_attribs = {}
    way_nodes = []
    tags = []  # Handling secondary tags the same way for both node and way elements
    
    for el_tag in element.iter('tag'):
        key_tag = el_tag.attrib['k']
        
        # for cleaning data from problematic characters
        if problem_chars.search(key_tag):
            continue
        
        # Fixing Street names
        if is_street_name(el_tag):
            
            # updating problematic words with defined maps
            el_tag.attrib['v'] = update_name(el_tag.attrib['v'], mapping_street, mapping_abbrev)
            
            # adding a new line for housenumber, if it's mentioned in street address
            if housenumber_in_street_re.search(el_tag.attrib['v']):
                value_list_1 = el_tag.attrib['v'].split(' ')
                # keeping housenumber for creating a new line and deleting it from street address
                housenumber = value_list_1.pop(0)
                el_tag.attrib['v'] = ' '.join(value_list_1)
                add_new_line('housenumber', housenumber, tags, element)
            
            # adding a new line for suite, if it's mentioned in street address
            if (ste_re.search(el_tag.attrib['v'])) or (suite_re.search(el_tag.attrib['v'])):
                value_list_2 = el_tag.attrib['v'].split(' ')
                # keeping suite number for creating  a new line
                suite_number = value_list_2.pop(-1)
                # removing the suite word from the address
                value_list_2.remove(value_list_2[-2])
                el_tag.attrib['v'] = ' '.join(value_list_2)
                # adding suite line
                add_new_line('Suite', suite_number, tags, element)
                
        # Fixing House Numbers problems
        if is_housenumber(el_tag):
            # fixing the only housenumber that contains the whole address
            if el_tag.attrib['v'].startswith('1850 Sawtelle Boulevard'):
                value_list_3 = el_tag.attrib['v'].split(', ')
                el_tag.attrib['v'] = value_list_3[0].split(' ')[0]
                # adding suite line
                add_new_line('Suite', value_list_3[1].split(' ')[-1], tags, element)
                
                # adding city line
                add_new_line('city', value_list_3[2], tags, element)
                
                # adding state line
                add_new_line('state', value_list_3[3].split(' ')[0], tags, element)
                
            
            # adding a new line for suite, if it's mentioned in housenumber
            elif (ste_re.search(el_tag.attrib['v'])) or (suite_re.search(el_tag.attrib['v'])):
                value_list_2 = el_tag.attrib['v'].split(' ')
                # keeping suite number for creating  a new line
                suite_number = value_list_2[-1]
                el_tag.attrib['v'] = value_list_2[0]
                # adding new line for suite
                add_new_line('Suite', suite_number, tags, element)
                
        # Fixing State
        if is_state(el_tag):
            el_tag.attrib['v'] = update_state(el_tag.attrib['v'], state_list)
        
        # Fixing Post Codes
        if is_postcode(el_tag):
            # finding problematic postcodes that contain state as part of postcode
            if state_in_postcode_re.search(el_tag.attrib['v']):
                value_list_4 = el_tag.attrib['v'].split(' ')
                el_tag.attrib['v'] = value_list_4[1]
                # adding new line for state
                add_new_line('state', value_list_4[0], tags, element)
                
        # Fixing Phone numbers and format them 
        if is_phone(el_tag):
            if el_tag.attrib['v'] in notValidPhones:
                el_tag.attrib['v'] = el_tag.attrib['v'].replace('0', '+', 1)
            # Uniform all phones the same like this: +13102606308
            if el_tag.attrib['v'].startswith("+"):
                el_tag.attrib['v'] = el_tag.attrib['v'][1:]
            z = phonenumbers.parse(el_tag.attrib['v'], "US") 
            el_tag.attrib['v'] = phonenumbers.format_number(z, phonenumbers.PhoneNumberFormat.E164)
                
        # changing key = 'url' to key = 'website'; because there are many \
        # website addresses and only 4 urls as keys;
        if key_tag == 'url':
            key_tag = 'website'
        
        # fixing problematic websites
        if key_tag == 'source':
            if el_tag.attrib['v'] in problemWebsite:
                el_tag.attrib['v'] = el_tag.attrib['v'].split(',')[0]
                
        temp = {}
        temp['id'] = element.attrib['id']
        temp['key'] = key_tag
        temp['type'] = default_tag_type           
        temp['value'] = el_tag.attrib['v']
        
        if LOWER_COLON.search(key_tag):
            key_tag_list = key_tag.split(":")
            temp['type'] =  key_tag_list.pop(0)
            temp['key'] = ":".join(key_tag_list)
            
        if temp['type'] == 'addr':
            # using Uppercase for first letter of all words in address related values; like street , city , ...
            temp['value'] = string.capwords(temp['value'])
        
        tags.append(temp)
        
    if element.tag == 'node':
        for field in node_attr_fields:
            node_attribs[field] = element.attrib[field]
        return {'node': node_attribs, 'node_tags': tags}
        
    elif element.tag == 'way':
        for field in way_attr_fields:
            way_attribs[field] = element.attrib[field]
        counter = -1
        for nd_tag in element.iter('nd'):
            counter += 1
            temp = {}
            temp['id'] = element.attrib['id']
            temp['node_id'] = nd_tag.attrib['ref']
            temp['position'] = counter
            way_nodes.append(temp)
            
        return {'way': way_attribs, 'way_nodes': way_nodes, 'way_tags': tags}


# ================================================== #
#               Helper Functions                     #
# ================================================== #
def get_element(osm_file, tags=('node', 'way', 'relation')):
    """Yield element if it is the right type of tag"""

    context = ET.iterparse(osm_file, events=('start', 'end'))
    _, root = next(context)
    for event, elem in context:
        if event == 'end' and elem.tag in tags:
            yield elem
            root.clear()


def validate_element(element, validator, schema=SCHEMA):
    """Raise ValidationError if element does not match schema"""
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
    """Extend csv.DictWriter to handle Unicode input"""

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
    """Iteratively process each XML element and write to csv(s)"""

    with codecs.open(NODES_PATH, 'w') as nodes_file,         codecs.open(NODE_TAGS_PATH, 'w') as nodes_tags_file,         codecs.open(WAYS_PATH, 'w') as ways_file,         codecs.open(WAY_NODES_PATH, 'w') as way_nodes_file,         codecs.open(WAY_TAGS_PATH, 'w') as way_tags_file:

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


# In[8]:

process_map(OSM_FILE, validate=True)


# ### Creating Database and it's Tables

# In[16]:

# Creating a database with this name: openStreet.db
db = sqlite3.connect('C:/Users/Shahrooz/Desktop/OpenStreetMap/DataSource_openStreet/openStreet.db')
c = db.cursor()


# #### Creating nodes Table

# In[17]:

create_node_table = """CREATE TABLE IF NOT EXISTS nodes(
                                id INTEGER primary key,
                                lat REAL,
                                lon REAL,
                                user INTEGER,
                                uid TEXT,
                                version TEXT,
                                changeset INTEGER,
                                timestamp TEXT
                                );"""
c.execute(create_node_table)


# #### Inserting Data from CSV file into nodes Table

# In[18]:

with open(NODES_PATH,'rb') as source:
    dic = csv.DictReader(source) # comma is default delimiter
    to_db = [(i['id'], i['lat'],i['lon'], i['user'].decode("utf-8"), i['uid'], i['version'], i['changeset'], i['timestamp']) for i in dic]
# insert the formatted data
c.executemany("INSERT INTO nodes(id, lat, lon, user, uid, version, changeset, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?);", to_db)
# commit the changes
db.commit()


# In[76]:

query = "SELECT id FROM nodes LIMIT 2;"
c.execute(query)
rows = c.fetchall()
print rows

#### Creating nodes_tags Table
# In[20]:

create_node_tags_table = """CREATE TABLE IF NOT EXISTS nodes_tags(
                                id INTEGER references nodes(id),
                                key TEXT,
                                value TEXT,
                                type TEXT
                                );"""
c.execute(create_node_tags_table)


# #### Inserting Data from CSV file into nodes_tags Table

# In[22]:

with open(NODE_TAGS_PATH,'rb') as source:
    dic = csv.DictReader(source) # comma is default delimiter
    to_db = [(i['id'], i['key'],i['value'].decode("utf-8"), i['type']) for i in dic]
# insert the data to the table
c.executemany("INSERT INTO nodes_tags(id, key, value, type) VALUES (?, ?, ?, ?);", to_db)
# commit the changes
db.commit()


# #### Creating ways Table

# In[27]:

create_way_table = """CREATE TABLE IF NOT EXISTS ways(
                                id INTEGER primary key,
                                user INTEGER,
                                uid TEXT,
                                version TEXT,
                                changeset INTEGER,
                                timestamp TEXT
                                );"""
c.execute(create_way_table)


# #### Inserting Data from CSV file into ways Table

# In[28]:

with open(WAYS_PATH,'rb') as source:
    dic = csv.DictReader(source) # comma is default delimiter
    to_db = [(i['id'], i['user'].decode("utf-8"),i['uid'], i['version'], i['changeset'], i['timestamp']) for i in dic]
# insert the data to the table
c.executemany("INSERT INTO ways(id, user, uid, version, changeset, timestamp) VALUES (?, ?, ?, ?, ?, ?);", to_db)
# commit the changes
db.commit()


# #### Creating ways_nodes Table

# In[30]:

create_way_nodes_table = """CREATE TABLE IF NOT EXISTS ways_nodes(
                                id INTEGER references ways(id),
                                node_id INTEGER references nodes(id),
                                position INTEGER
                                );"""
c.execute(create_way_nodes_table)


# #### Inserting Data from CSV file into ways_nodes Table

# In[32]:

with open(WAY_NODES_PATH,'rb') as source:
    dic = csv.DictReader(source) # comma is default delimiter
    to_db = [(i['id'], i['node_id'], i['position']) for i in dic]
# insert the data to the table
c.executemany("INSERT INTO ways_nodes(id, node_id, position) VALUES (?, ?, ?);", to_db)
# commit the changes
db.commit()


# #### Creating ways_tags Table

# In[36]:

create_way_tags_table = """CREATE TABLE IF NOT EXISTS ways_tags(
                                id INTEGER references ways(id),
                                key TEXT,
                                value TEXT,
                                type TEXT
                                );"""
c.execute(create_way_tags_table)


# #### Inserting Data from CSV file into ways_tags Table

# In[37]:

with open(WAY_TAGS_PATH,'rb') as source:
    dic = csv.DictReader(source) # comma is default delimiter
    to_db = [(i['id'], i['key'], i['value'].decode("utf-8"), i['type']) for i in dic]
# insert the data to the table
c.executemany("INSERT INTO ways_tags(id, key, value, type) VALUES (?, ?, ?, ?);", to_db)
# commit the changes
db.commit()


# ## Looking at Data in Data Base

# #### looking at 'postcode' field

# In[39]:

query_post_code = "SELECT value FROM nodes_tags WHERE key = 'postcode';"
c.execute(query_post_code)
rows = c.fetchall()
pprint.pprint(rows)


# #### Checking 'postcode' for problems

# In[40]:

c.execute("SELECT * FROM (SELECT * FROM nodes_tags UNION ALL SELECT * FROM ways_tags) as tags             WHERE (tags.value LIKE 'CA %' AND tags.key = 'postcode');")
rows = c.fetchall()
pprint.pprint(rows)


# #### Checking for existance of 'url' as key

# In[41]:

c.execute("SELECT * FROM nodes_tags WHERE key = 'url';")
rows = c.fetchall()
pprint.pprint(rows)


# #### Checking for fixed street name that contains housenumber

# In[44]:

c.execute("SELECT * FROM nodes_tags WHERE (key = 'street' AND value = '1200 South Sepulveda');")
rows = c.fetchall()
pprint.pprint(rows)


# #### Checking Street Names Uniformity

# In[45]:

c.execute("SELECT DISTINCT tags.value           FROM (SELECT * FROM nodes_tags UNION ALL                SELECT * FROM ways_tags) tags           WHERE key = 'street';")
rows = c.fetchall()
pprint.pprint(rows)


# ### Cities exist in Santa Monica Region

# In[43]:

city_query = """SELECT tags.value, COUNT(*) as count                FROM (SELECT * FROM nodes_tags UNION ALL                SELECT * FROM ways_tags) tags                WHERE tags.key = 'city'                GROUP BY tags.value                ORDER BY count DESC;"""
c.execute(city_query)
rows = c.fetchall()
pprint.pprint(rows)


# ### Which kind of amenities are in Santa Monica Region?

# In[95]:

c.execute("SELECT tags.value, count(*) as count           FROM (SELECT * FROM nodes_tags UNION ALL SELECT * FROM ways_tags) as tags            WHERE tags.key = 'amenity'            GROUP BY value            ORDER BY count DESC            LIMIT 10;")
rows = c.fetchall()
pprint.pprint(rows)


# ### Which restaurant Cuisines are popular in this region?

# In[96]:

c.execute("SELECT nodes_tags.value, COUNT(*) as count            FROM (SELECT tags.id FROM (SELECT * FROM nodes_tags UNION ALL SELECT * FROM ways_tags)            as tags            WHERE tags.value = 'restaurant') as restaurant_tags, nodes_tags           WHERE restaurant_tags.id = nodes_tags.id AND nodes_tags.key = 'cuisine'           GROUP BY nodes_tags.value           ORDER BY count DESC            LIMIT 10;")
rows = c.fetchall()
pprint.pprint(rows)


# ## Which religions are related to Worship Places?

# In[62]:

c.execute("SELECT nodes_tags.value, COUNT(*) as count           FROM (SELECT tags.id FROM (SELECT * FROM nodes_tags UNION ALL SELECT * FROM ways_tags) as tags           WHERE tags.value = 'place_of_worship') as worship_place, nodes_tags           WHERE worship_place.id = nodes_tags.id AND nodes_tags.key = 'religion'           GROUP BY nodes_tags.value           ORDER BY count DESC;")
            
rows = c.fetchall()
pprint.pprint(rows)


# ## Denomination of Worship Places

# In[63]:

c.execute("SELECT nodes_tags.value, COUNT(*) as count           FROM (SELECT tags.id FROM (SELECT * FROM nodes_tags UNION ALL SELECT * FROM ways_tags) as tags           WHERE tags.value = 'place_of_worship') as worship_place, nodes_tags           WHERE worship_place.id = nodes_tags.id AND nodes_tags.key = 'denomination'           GROUP BY nodes_tags.value           ORDER BY count DESC;")
            
rows = c.fetchall()
pprint.pprint(rows)


# ## Coffee Shop brands in Santa Monica

# In[97]:

c.execute("SELECT nodes_tags.value, COUNT(*) as count            FROM (SELECT tags.id FROM (SELECT * FROM nodes_tags UNION ALL SELECT * FROM ways_tags) as tags           WHERE tags.value = 'cafe') as cafe, nodes_tags           WHERE cafe.id = nodes_tags.id AND nodes_tags.key = 'name'           GROUP BY nodes_tags.value           ORDER BY count DESC           LIMIT 5;")
            
rows = c.fetchall()
pprint.pprint(rows)


# ## Top Contributer Users 

# In[82]:

c.execute("SELECT user, COUNT(*) as count           FROM nodes           GROUP BY user           ORDER BY count DESC           LIMIT 10;")
            
rows = c.fetchall()
pprint.pprint(rows)


# ##  Number of Users Contribute Only Once

# In[94]:

c.execute("SELECT user, COUNT(user) as count           FROM nodes           GROUP BY user            HAVING count = 1;")
            
rows = c.fetchall()
print "Number of one time Contributers: ", len(rows)


# ## Most common PostCodes

# In[83]:

c.execute("SELECT tags.value, COUNT(*) as count            FROM (SELECT * FROM nodes_tags UNION ALL SELECT * FROM ways_tags) as tags           WHERE tags.key = 'postcode'           GROUP BY tags.value           ORDER BY count DESC           LIMIT 5;")

rows = c.fetchall()
pprint.pprint(rows)


# In[98]:

db.close()

