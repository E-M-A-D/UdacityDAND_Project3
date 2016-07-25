# -*- coding: utf-8 -*-

import xml.etree.cElementTree as ET
import re
import pymongo as mongoDB


problemchars = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')

CREATED = [ "version", "changeset", "timestamp", "user", "uid"]


########################################################################################################################
#                                          Dictionaries And Word Lists
french_naming = ["Rue", "rue", \
                 "Avenue", "avenue", "Ave.", "Ave", "ave.", "ave", \
                 "Boulevard", "boulevard", "Boul.", "Boul", 'boul.', "boul", "Boulvard", "boulvard", \
                 "Autoroute", "autoroute", \
                 "Chemin", "chemin", "ch.", "ch", "Ch.", "Ch", \
                 "1e", "2e", "3e", "4e", "5e", "6e", "7e", "8e", "9e",\
                 "Place", "place", \
                 "Route", "route", \
                 "Ruelle", "ruelle", \
                 "Quai", "quai", "Quai-", "quai-", \
                 "Voie", "Court", "Rang", "rang", "Descente", u"Montée", "Croissant", u"Carré", "Impasse", "Promenade", "Cercle", "Terrasse"]

english_naming = "Street street St St. st st. West W. w. W w East E. e. E e".split()

abbreviations_list = [ "Ave.", "Ave", "ave.", "ave", "Boul.", "Boul", 'boul.', "boul", "ch.", "ch", "Ch.", "Ch", "St", "st", "St.", "st.", "St-", "ste.", "Ste." ]

# This will be a separate dictionary because the abbreviation of the word Saint can be found in both English and French
# naming. This comes from the local convention (and probably a global convention, actually)
saint_abbreviations_list = "St Ste St. Ste. Sainte".split()

english_street_abbreviations_dict = {"st." : "Street", "st" : "Street", "St." : "Street", "St" : "Street"}

english_directions_abbreviation_dict = {"W." : "West", "w." : "West", "W" : "West", "w" : "West",\
                              "E." : "East", "e." : "East", "E" : "East", "e" : "East"}

french_abbreviations_dict = {"St" : "Saint", "St." : "Saint", "Ste." : "Saint", "ste" : "Saint", \
                             "E.": "Est", "e." : "Est", " e " : "Est", " E " : "Est", \
                             "O.": "Ouest", "o." : "Ouest", " o " : "Ouest", " O " : "Ouest" }

french_to_english = { "Rue" : "Street", "Avenue" : "Avenue", "Boulevard" : "Boulevard", "Place" : "Square", \
                      "Chemin" : "Road", "Est" : "East", "Ouest" : "West", "Quai" : "Pier"}

# Also will include tags that start with contact
tags_we_care_about = "amenity cuisine name phone denomination religion wheelchair operator".split()



########################################################################################################################
#                                          Suporting Functions

# A function that checks if the passed parameter contains a problemchars
def is_unclean(name):
    if problemchars.match(name):
        return True
    else:
        return False


# A function to connect to a MongoDB server running over the local host.
def connect_to_local_db():
    print "Connecting..."
    # Try to connect
    try:
        handle = mongoDB.MongoClient()

    # If connection fails, alert the user and quit
    except mongoDB.errors.ConnectionFailure, e:
        print "Could not connect to MongoDB: %s" % e
        return None

    print "Connection Successful"
    return handle

# This function has more of an esthetic role than any real added value. It just makes the code more readable to me.
def open_db(handle, db_name):
    return handle[db_name]

# Same here, esthetic
def open_collection(collection_name, db_name):
    return db_name[collection_name]

# Still, an esthetic function
def add_document(document, collection_name):
    collection_name.insert(document)


# Shape element has the same role as the function within the exercises of the course. Of course there were added
# functionalities.
def shape_element(element):
    node = {}

    if element.tag == "node" or element.tag == "way" :
        # YOUR CODE HERE

        node["created"] = {}
        node["type"] = element.tag

        # A variable to hold longitude\latitude. It was done that way to always preserve order
        # and to not add them to the node unless both are present (In case of a corrupt node that has only
        # one of them.
        temp_coordinates = []

        for attrib_key in element.attrib:
            # check if any if the attributes are not clean
            if is_unclean(attrib_key):
                print attrib_key + "in element ID: " + element.attrib["id"] + ' contains a problematic character, skipping'
                continue

            # handle special keys
            ## longitude\latitude
            if attrib_key in ["lon", "lat"]:
                if attrib_key == "lon":
                    temp_coordinates.append( float(element.attrib[attrib_key]) )

                if attrib_key == "lat":
                    temp_coordinates.insert(0, float(element.attrib[attrib_key]) )

                if len(temp_coordinates) == 2:
                    node["pos"] = temp_coordinates

            ## Created
            elif attrib_key in CREATED:
                node["created"][attrib_key] = element.attrib[attrib_key]

            ## Anything else
            else:
                node[attrib_key] = element.attrib[attrib_key]

        # Assume that it is not an amenity. If this is not correct, we will update it when we find out
        node["is_amenity"] = False

        # process the sub-elements for the node or way
        for sub_elem in element.iter():
            # nd
            if sub_elem.tag == "nd":
                # Add the refs to node_refs
                if "ref" in sub_elem.attrib: # Can a node have refs too ? Or only ways have refs?
                    if "node_refs" in node:
                        node["node_refs"].append(sub_elem.attrib["ref"])
                    else:
                        node["node_refs"] = [sub_elem.attrib["ref"]]

            # tag
            elif sub_elem.tag == "tag":

                # If it's an address tag, extract it and add it to the address dictionary
                if sub_elem.attrib["k"].startswith("addr:"):
                    address_elements = sub_elem.attrib["k"].split(":")
                    # Process only if the value of the key has only one column, ignore the rest (As per requirement)
                    if len(address_elements) < 3:
                        if "address" in node:
                            node["address"][ address_elements[1] ] = sub_elem.attrib["v"]
                        else:
                            node["address"] = {}
                            node["address"][ address_elements[1] ] = sub_elem.attrib["v"]

                elif sub_elem.attrib["k"].startswith("contact:"):
                    contact_elements = sub_elem.attrib["k"].split(":")

                    if "info" in node:
                        node["info"][ contact_elements[1] ] = sub_elem.attrib["v"]
                    else:
                        node["info"] = {}
                        node["info"][ contact_elements[1] ] = sub_elem.attrib["v"]

                else:
                    if sub_elem.attrib["k"] in tags_we_care_about:
                        # Update the is_amenity to be true
                        if sub_elem.attrib["k"] == "amenity":
                            node["is_amenity"] = True

                        if "info" in node:
                            node["info"][sub_elem.attrib["k"] ] =  sub_elem.attrib["v"]
                        else:
                            node["info"] = {}
                            node["info"][sub_elem.attrib["k"] ] = sub_elem.attrib["v"]

        return node

    # We are not interested in processing other nodes, so just return None
    else:
        return None


# A function to clear all the contents of a collection. Used when we want to rerun the program after making some changes,
# so we clear the data before reentering them, otherwise we would have a duplicate database
def clear_collection(db_name, collection_name):
    if db_name[collection_name].count() != 0:
        db_name[collection_name].drop()


# A function that is used to handle detected corrupt fields. It raises a flag called "has_corrupt_data" to be True, and
# appends the corrupt field to a newly created field "corrupt_field". This way, we can later query where changes has been
# made, and maybe manually correct the data.
def process_corrupt_data(db_name, collection_name, object_id, corrupt_field):
    # Mark the document to have corrupt data
    db_name[collection_name].update_one( {
                                        "_id" : object_id
                                    },
                                    {
                                        "$set" :
                                            {
                                                "has_corrupt_data" : True
                                            }
                                    }
                                   )

    # Append the corrupt data to the corrupt_fields field for manual inspection later
    db_name[collection_name].update_one( {
                                        "_id" : object_id
                                    },
                                    {
                                        "$set" :
                                            {
                                                "corrupt_fields" : corrupt_field
                                            }
                                    }
                                   )



# A function that opens the map XML file and loads it into a running MongoDB server on the local host..
# The last parameter for that function is by default false. If set to true, the function will delete all the contents
# of the collection before loading the XML data.
def insert_xml_map_to_db(filename, db_name, collection_name, clean_up = False):
    db_server_handle = connect_to_local_db()
    if db_server_handle == None:
        print "Could not connect, XML map file loading failed"
        return

    # Open the databse
    db = open_db(db_server_handle, db_name)
    #Clear the collection if requested
    if clean_up:
        clear_collection(db, collection_name)

    # A dictionary to hold the unique encountered tags and their count, just for exploration purposes.
    tag_count = {}

    # a buffer to hold a certain amount of documents to be inserted. It is used to take advantage of the performance
    # benefits of batch inserting.  The size will be 10,000 (ten thousands) document batch per insert
    buffer = []

    # counter of how many documents were inserted
    counter = 1

    # Set for efficient parsing. Parsing will not be by building a tree as usual, but by truly iteravily check an item
    # and then discarding it, thus saving a lot of RAM The method is to get the root node before looping, start looping
    # and then clear the root node, and by that the tree is destroyed (Or so is how I understand it)
    # The older method's problem was that it never deleted the node, it just cleared its contents, and therefore
    # cramming the RAM with a huge number of empty nodes, which still take a lot of space when the file is huge. The old
    # method is:
    # for event, child in ET.iterparse(filename, events=("start", )):

    # Get an iterable over the tree
    tree_iterable = ET.iterparse(filename, events=("start", ))

    # Turn the iterable into an iterator
    tree_iterator = iter(tree_iterable)

    # get the root element, so we can delete it
    event, root = tree_iterator.next()


    # ITERATE OVER XML FILE
    for event, child in tree_iterator:
        if child.tag in tag_count:
            tag_count[child.tag] += 1
        else:
            tag_count[child.tag] = 1

        shaped_element = shape_element(child)
        if shaped_element:
            buffer.append(shaped_element)
            if len(buffer) == 10000:
                db[collection_name].insert_many(buffer)
                buffer = []
                print str(counter*10000) + " documents inserted so far"
                counter += 1

        # Clear the root, and save RAM!
        root.clear()

    # Insert the last batch of nodes that were not inserted because the data finished before that buffer reached 1000
    db[collection_name].insert_many(buffer)

    print "Data Loading Finished."
    print "A total of " + str(db[collection_name].count() ) + " elements loaded."
    print "Tags found and their count: "
    print tag_count

    # Clean up
    db_server_handle.close()

def get_data(data):
    # A function to extract the data in question that can come in different formatting. For example, if the data is
    # still freshly loaded, it might be represented by a string. If the data was already loaded within the database and
    # was processed before, the field might become a list. This function will extract the data no matter how is the
    # could have been represented by the program before
    # If the data was already formatted as an array\list, convert it to a string so that we can perform regex on it
    data_str = ""
    if type(data) == list:
        data_str = " ".join(data)
    elif type(data) == basestring or type(data) == unicode:
        data_str = data
    else:
        print "Unexpected type for phone number: " + type(data)
        return
    return data_str

# A function that uses regex to extract phone number and then standardizing them into the following format:
# +1 (XXX) XXX-XXXX
def standardize_phone_number(number):
    phone_regex = re.compile(r"\(?\+?(1)?\)?[- .]?\(?(\d\s?\d\s?\d)?\)?[- .]?(\d{3})[- .]?(\d\s?\d\s?\d\s?\d)")

    # If the data was already formatted as an array\list, convert it to a string so that we can perform regex on it

    str_number = get_data(number)

    all_phones = re.findall(phone_regex, str_number)
    result = []

    if all_phones == []:
        print "Corrupt phone number: ", number
        return

    for nums in all_phones:
        number_is_corrupt = False

        # This will always be +1, we can just discard it, because it will not always be there:
        # country_code = nums[0]

        # Area code is a must, because Montreal has multiple ones (514, 450, 438..etc)
        area_code = nums[1]
        if (area_code == "") or (len(area_code) != 3):
            is_number_corrupt = True
            print ''.join(nums) + " phone number is corrupt: No area code found, area code is not equal to 3 digits or there is a missing digit"
            print "    deleting..."

        if not number_is_corrupt:
            formatted_number = "+1 (" + area_code + ") " + str(nums[2]) + "-" + str(nums[3])
            result.append(formatted_number)

    # return a list of all phone numbers
    return result


# THis function gets all fields with phone numbers, attempts to standardize them. If the operation fails, it declares
# the document to be containing a corrupt data (phone number in this case), calls process_corrupt_data() then deletes
# the corrupt phone field
def clean_phone_numbers(db_name, collection_name):
    print "Starting phone numbers cleanup."
    db_server_handle = connect_to_local_db()
    db = open_db(db_server_handle, db_name)

    cursor = db[collection_name].find( {"info.phone": {"$exists": True}} )

    for docs in cursor:
        doc_id = docs["_id"]

        phones = standardize_phone_number(docs["info"]["phone"])

        # If phone is valid, ie there was a result passed back from the standardized_phone_number() function
        if phones:
            db[collection_name].update_one( {
                                                "_id" : doc_id
                                            },
                                            {
                                                "$set" :
                                                    {
                                                        "info.phone" : phones
                                                    }
                                            }
                                           )
        # No valid phones were found, delete the phone field
        else:
            print "No valid phone number found, removing the phone field.."
            print docs["info"]["phone"]
            process_corrupt_data(db, collection_name, doc_id, docs["info"]["phone"] )

            db[collection_name].update_one( {
                                                "_id" : doc_id
                                            },
                                            {
                                                "$unset" :
                                                    {
                                                        "info.phone" : ""
                                                    }
                                            }
                                           )

    db_server_handle.close()
    #delete fields with null values


# A function that detects the postal codes and standardizes them to the following format LDL-DLD (Where D means Digit and
# L means Letter). This is the standard format of postal codes in Canada.
def standardize_postal_code(code):

    # If the data was already formatted as an array\list, convert it to a string so that we can perform regex on it
    str_code = get_data(code)

    postal_code_regex = re.compile(r"(\w\d\w)[\s\-\.]{0,2}(\d\w\d)")

    all_postal_codes = re.findall(postal_code_regex, str_code)

    result = []
    for postal_codes in all_postal_codes:
        result.append(postal_codes[0] + " " + postal_codes[1])

    return result


# A function that looks for abbreviated English street components, like St. for street ..etc and expands this abbreviation
# to the full word using a dictionary defining the rules for that.
def expand_english_abbreviations(street_name):
    # Assuming tht the passed street is already English
    street_list = street_name.split()

    # If the street ends with a direction abbreviated (W. for West..etc), replace it and then check if the word before
    # it is an abbreviated street name
    if street_list[-1] in english_directions_abbreviation_dict:
        street_list[-1] = english_directions_abbreviation_dict[street_list[-1]]

        if street_list[-2] in english_street_abbreviations_dict:
            street_list[-2] = english_street_abbreviations_dict[street_list[-2]]

    # Else if the last word is an abbreviated street, then replace it with a full
    elif street_list[-1] in english_street_abbreviations_dict:
        street_list[-1] = english_street_abbreviations_dict[street_list[-1]]

    return " ".join(street_list)


# A function that detects if the passed street name is English or not. This is done by checking if it contains an English
# road qualifier (like street, road, boulevard..etc) at the END of the passed street name
def is_street_in_english(street_name):

    is_english = False

    # Sometimes the street is named in a numberical form, like 5th street. If it detects a number followed by th, nd..etc
    # it will assume that this is an English street name
    street_num_regex = re.compile(r"[\d]+(th|rd|nd|st)")

    if re.findall(street_num_regex, street_name):
        is_english = True

    for english_end in english_naming:
        if english_end == street_name.split()[-1]:
            is_english = True

    return is_english


# A function that tries to detect if the street name was written by French, ie if it includes French street qualifiers
# like Rue, Boulevard..etc written at the START of the street_name
def is_street_in_french(street_name):
    # A variable to hold the return value
    is_french = False

    # A regular expression to catch streets named in numbers in French (eg 24e . THis is equivalent to 24th in English)
    street_num_regex = re.compile(r"\d+[Ee]")

    if re.findall(street_num_regex, street_name):
        is_french = True

    for french_start in french_naming:
        if street_name.startswith(french_start):
            is_french = True

    return is_french


# A function to call French and English abbreviation expansion functions
def expand_abbreviations(street_name):
    # We process English abbreviations first. This is because there is a potential conflict in the abbreviations:
    # St. can be Saint (Coming from the French convention) or street in English. If we find St. and the address is
    # English, we expand it to Street, and then handle any St to be Saint

    # English abbreviation handling
    if is_street_in_english(street_name):
        if street_name != expand_english_abbreviations(street_name):
            street_name =  expand_english_abbreviations(street_name)


    # We are sure now to have gotten rid of st abbreviations denoting street, so now any st found would represent the
    # word Saint, not Street.
    # Expand the abbreviation of the word Saint, if available.

    street_name_list = street_name.split()
    for saint_abbreviation in saint_abbreviations_list:
        if saint_abbreviation in street_name_list:
            street_name_list[street_name_list.index(saint_abbreviation)] = "Saint"
            #street_name = street_name.replace(saint_abbreviation, "Saint")

    # French abbreviations handling
    if is_street_in_french(street_name):
        for abbrv in french_abbreviations_dict:
            if abbrv in street_name_list:
                print "Abbrv found: " + abbrv + " in : " + street_name
                street_name_list[ street_name_list.index(abbrv)] = french_abbreviations_dict[abbrv]
                print " ".join(street_name_list)

    street_name = " ".join(street_name_list)

    return street_name



# THis function converts French street naming to an English equivalent.
def translate_french_to_english(street_name):
    french_to_english
    # This function assumes that the passed name is already in French. Also, it assumes that all abbreviations has been
    # expanded.
    street_name_list = street_name.split()

    # Add to the end the English equivalent of the street name. Also, using pop will delete the first element, which is
    # intended to be removed as part of converting the name into English
    # This will be done only if we have a valid translation. I was not able to translate all of the French namings. But
    # all along we update the french_to_english dictionary, this part will work better
    if street_name_list[0] in french_to_english:
        street_name_list.append(french_to_english[street_name_list.pop(0)])


    # If the street contains a direction (Ouest, Est..etc), append its English equivalent to the end
    for direction in ["Est", "Ouest"]:
        if direction in street_name_list:
            street_name_list.append(french_to_english[direction])
            street_name_list.remove(direction)

    street_name = " ".join(street_name_list)

    # The final step: convert street numbers to English --> 23e --> 23rd
    num_pattern = re.compile(r"(?<=\d)([Ee])")
    esthetic_pattern = re.compile(r"(\d)[Ee]")
    french_number_street = re.findall(esthetic_pattern, street_name)

    # What we are going to substitute the e at the end of the number with. This is just an esthetical part. In french,
    # we can use e after any number, but in English, 1 uses 'st' after (1st), 2 is 'nd,' 3 is 'rd' and the rest is 'th'
    e_substitute = "th"

    if french_number_street:
        if french_number_street[0] == '1':
            e_substitute = "st"
        elif french_number_street[0] == '2':
            e_substitute = "nd"
        elif french_number_street[0] == '3':
            e_substitute = "rd"
    street_name = num_pattern.sub(e_substitute, street_name)

    return street_name

def standardize_address_info(address):
    # All addresses will have a province and country information, even if they are not there.
    # Sometimes the province's value was included under the key state and some other times province. It will be
    # all standardized to province

    # Note: To my surprise, there were buildings that had TWO postal codes. That will force us to have postal codes standardized as a list

    # The corrupt addresses will not be deleted, but there will be a flag added that the item is corrupt and that way we can
    # query these documents and maybe manually check them

    # if "state" is in address, remove it. Canada's equivalent of a state is province, and it is a valid tag in OSM
    address.pop("state", None)

    # I was tempted to do this part in the shape element function, but then prefered to separate the shape function and
    # the clean function (Although I think it might have had a performance advantage to clean the data on the fly before
    # inserting it. But I thought that for the sake of the project (since it is a MongoDB project), I will clean from the
    # database.

    if "postcode" in address:
        #clean the post code
        formatted_postcode = standardize_postal_code(address["postcode"])
        if formatted_postcode:
            address["postcode"] = formatted_postcode
        else:
            print "Corrupt postal code: " + address["postcode"]

    # If we have a street name within the address, and it is NOT an empty field
    if ("street" in address) and address["street"] != "":
        # The province and country will have the two character code, and not the full name
        address["province"] = "QC"
        address["country"] = "CA"

        # A variable to hold the street name. All changes will be made to that variable, and at the end we do only
        # one update to the database
        street_name = address["street"].title()

        # Check if the address contains something that would imply it is more than just the street's name.
        # But we will do nothing about it, as there is, for example, a street called Canada in the city of Montreal
        for suspect in [',', 'QC', 'Quebec', 'Montreal', 'Canada']:
            if  suspect in address["street"]:
                print "Warning, a potentially long address: " + street_name

        # Remove all the dashes -  in the street name. The - is heavily used in French naming, like St-Cathering Street
        # It will be replaced by a space
        street_name = street_name.replace("-", " ")

        # Expand all the abbreviations in the street_name, if there are ones
        street_name = expand_abbreviations(street_name)

        # Translate the street_name to English if it's in French
        if is_street_in_french(street_name):
            street_name = translate_french_to_english(street_name)

    else:
        #THis is tricky an address without a street. Npthing to be done for that for now
        #print "An address without a street!"
        #print address
        street_name = ""

    address["street"] = street_name

    return address



# A function that calls all the cleaning processes for a street name. If the street name was detected to be corrupt and
# cannot be worked with, the corrupt data flag is created, the corrupt street name is apended to the corrupt data field
# and is removed from the info field.
def clean_address_info(db_name, collection_name):
    db_server_handle = connect_to_local_db()
    db = open_db(db_server_handle, db_name)

    cursor = db[collection_name].find( {"address": {"$exists": True}} )

    for docs in cursor:
        doc_id = docs["_id"]

        current_address = standardize_address_info(docs["address"])

        # If address is valid, ie there was a result passed back from the standardize_address_info() function
        if current_address:
            db[collection_name].update_one( {
                                                "_id" : doc_id
                                            },
                                            {
                                                "$set" :
                                                    {
                                                        "address" : current_address
                                                    }
                                            }
                                           )
        # No valid phones were found, delete the phone field
        else:
            print "No valid address found in, removing the phone field to the document's corrupt_fields field"
            #db[collection_name]["contains_corrupted_data"] = True
            print docs["address"]
            process_corrupt_data(db, collection_name, doc_id,docs["address"] )

            db[collection_name].update_one( {
                                                "_id" : doc_id
                                            },
                                            {
                                                "$unset" :
                                                    {
                                                        "address" : ""
                                                    }
                                            }
                                           )
        #print db[collection_name].find( {"_id" : doc_id} )[0]

    db_server_handle.close()


# Just for organizational purpose, calls the other cleaning functions
def clean_osm_data(db_name, collection_name):
    clean_phone_numbers(db_name, collection_name)
    clean_address_info(db_name, collection_name)


# Map statistics used in the project's report
def map_stats(db_name, collection_name):
    db_server_handle = connect_to_local_db()
    db = open_db(db_server_handle, db_name)

    # That's the example in the sample project, but it was really what I needed.
    # These queries are very similar to the point that I was tempted to make a function for them. But I preferred to
    # write the quesries manually as a way of exercising, to memorize them.
    users_frequency = db[collection_name].aggregate( [
                                                      {"$group" : {"_id" : "$created.user", "count" : {"$sum" : 1} } },
                                                      {"$sort" : {"count" : -1 } }
                                                      ] )

    users_contributing_once = db[collection_name].aggregate( [
                                                      {"$group" : {"_id" : "$created.user", "count" : {"$sum" : 1} } },
                                                      {"$match" : {"count" : 1} }
                                                      ] )

    print len(list(users_contributing_once))
    # For some reason when I use the command list(users_frequency), the second time I use it it returns an empty list. Not
    # sure what is going on. To overcome this, I will hold the result in a variable and use that variable
    users_freq_list =  list(users_frequency)
    number_of_unique_users = len(list(users_freq_list))
    print "Number of contributors:", number_of_unique_users

    amenity_type_frequency = db[collection_name].aggregate( [
                                                              { "$match" : {"is_amenity": True} },
                                                              { "$group" : {"_id" : "$info.amenity" , "count" : {"$sum" : 1} } },
                                                              { "$sort" : {"count" : -1}}
                                                            ])
    cuisine_type_frequency = db[collection_name].aggregate([ {"$match" : {"info.amenity" : { "$in" : ["restaurant" , "fast_food"] } } },
                                                             {"$group" : {"_id" : "$info.cuisine", "count" : {"$sum" : 1} }},
                                                             {"$sort" : { "count" : -1 }}
    ])


    top_3_cafes_chains =  db[collection_name].aggregate([ {"$match" : {"info.amenity" : "cafe" } },
                                                             {"$group" : {"_id" : "$info.name", "count" : {"$sum" : 1} }},
                                                             {"$sort" : { "count" : -1 }},
                                                             {"$limit" : 3}
                                                          ])

    print "Top Cafes: ", list(top_3_cafes_chains)

    top_3_fast_food_chains =  db[collection_name].aggregate([ {"$match" : {"info.amenity" : "fast_food" } },
                                                             {"$group" : {"_id" : "$info.name", "count" : {"$sum" : 1} }},
                                                             {"$sort" : { "count" : -1 }},
                                                             {"$limit" : 3}
                                                          ])

    print "Top Fast Food Chains: ", list(top_3_fast_food_chains)

    denomination_frequency = db[collection_name].aggregate([ {"$match" : {"info.amenity" : "place_of_worship" } },
                                                             {"$group" : {"_id" : "$info.denomination", "count" : {"$sum" : 1} }},
                                                             {"$sort" : { "count" : -1 }}
    ])



    # I think the following solution "might" be more efficient sinceit loops over the data once. Is that a sound reasoning?
    """
    cursor = db[collection_name].find( {"is_amenity": True} )

    for docs in cursor:
        doc_id = docs["_id"]

        if docs["info"]["amenity"] in amenity_type_frequency:
            amenity_type_frequency[docs["info"]["amenity"]] += 1
        else:
            amenity_type_frequency[docs["info"]["amenity"]] = 1

        # Survey the food industry
        if docs["info"]["amenity"] in ["restaurant", "fast_food"]:
            if "cuisine" in docs["info"]:
                if docs["info"]["cuisine"] in cuisine_type_frequency:
                    cuisine_type_frequency[docs["info"]["cuisine"]] += 1
                else:
                    cuisine_type_frequency[docs["info"]["cuisine"]] = 1

        # Survey the places of worship
        if docs["info"]["amenity"] == "place_of_worship":
            if "denomination" in docs["info"]:
                if docs["info"]["denomination"] in denomination_frequency:
                    denomination_frequency[docs["info"]["denomination"]] += 1
                else:
                    denomination_frequency[docs["info"]["denomination"]] = 1
    """
    print "Users: ", users_freq_list
    print "Amenities: ", list(amenity_type_frequency)
    print "Cuisines:" , list(cuisine_type_frequency)
    print "Denominations: ", list(denomination_frequency)



# There is two files I used for development, a small file (About 15 MB that contained downtown Montreal), and another
# file that had the whole greater Montreal. test_config controls which one to use
test_config = True

if test_config:
    active_db = "my_test"
    active_collection = "test_collection_1"
	#Update path please to use the map file included in the submission zip
    active_map = ".\\map"
else:
    active_db = "montreal_osm"
    active_collection = "all_data"
    active_map = ".\\greater_montreal.osm"


# Insert the XML data to database, clean the database data and then diplay statistics
insert_xml_map_to_db(active_map, active_db, active_collection, True)
clean_osm_data(active_db, active_collection)
map_stats(active_db, active_collection)
