import csv
import argparse
import os
import logging
import re

class Card:
    # Class representing a card in the collection

    def __init__(self, name, image_rotation, set_acrynm, image_file):
        self.name: str = name
        self.set_acrynm: str = set_acrynm
        self.image_file: str = image_file
        self.scan_rotation: str = image_rotation

        self.collector_number: str = "-1"

    def __str__(self):
        return f"<Card name:{self.name} set_acrynm:{self.set_acrynm} image_file:{self.image_file} collector_number:{self.collector_number}>"

    def __lt__(self, other):
        return self.collector_number < other.collector_number
    def __le__(self, other):
        return self.collector_number <= other.collector_number
    def __eq__(self, other):
        return self.collector_number == other.collector_number
    def __ne__(self, other):
        return self.collector_number != other.collector_number
    def __gt__(self, other):
        return self.collector_number > other.collector_number
    def __ge__(self, other):
        return self.collector_number >= other.collector_number


def open_set_list(set_list_filename):
    set_list = []
    with open(set_list_filename) as set_list_file:
        reader = csv.reader(set_list_file, delimiter=';')
        set_list = dict(reader)
        logging.info("Set list read from: " + set_list_filename)
    return set_list

def open_collection_list(input_cards_filename):
    collection_list = []
    with open(input_cards_filename) as input_cards_file:
        reader = csv.reader(input_cards_file, delimiter=';')
        logging.info("Detected cards read from: " + input_cards_filename)
        for card in reader:
            new_card = Card(card[0], card[1], card[2], card[3])
            collection_list.append(new_card)
            logging.debug(new_card)
    return collection_list

def find_collector_number(collection_list, set_list):
    for card in collection_list:
        if (card.name == ''):
            logging.error("Card detection missing in " + card.image_file)
        else:
            card.collector_number = set_list[card.name]
    return collection_list

def print_collection(collection, output_cards_filename):
    f = open(output_cards_filename, "w")
    for card in collection:
        f.write(card.set_acrynm + ";" + card.collector_number + "\n")
        logging.debug(card)
    f.close()
    return

def check_names(collection):
    error_cards: list[Card] = []
    for card in collection:
        if (card.name == ''):
            logging.error("Card missing name: " + card.image_file)
            error_cards.append(card)
    return error_cards

def check_collector_number(collection):
    max_number = str(collection[0].collector_number)
    re_max = re.search(r"([0-9]+)([a-z]*)", max_number)
    error_cards: list[Card] = []
    for card in collection:
        re_card  = re.search(r"([0-9]+)([a-z]*)", max_number)
        if (re_card.group(1) < re_max.group(1) or (re_card.group(1) == re_max.group(1) and re_card.group(2) < re_max.group(2))):
            logging.error("Card Collector Number Decreases: " + card.image_file)
            logging.error("Collector Number Decreases from: " + str(re_max.groups()) + " to " + str(re_card.groups()))
            error_cards.append(card)
        else:
            re_max = re_card
    return error_cards

def check_orientation(collection):
    scan_orientation = None
    error_cards: list[Card] = []
    for card in collection:
        if (card.scan_rotation != ""):
            if (scan_orientation == None):
                scan_orientation = float(card.scan_rotation)
            if (float(card.scan_rotation) != scan_orientation):
                logging.error("Card Rotation not consistent: " + card.image_file)
                error_cards.append(card)
    return error_cards

def check_collection(collection):
    # Check missing names
    check_names(collection)
    # Check increasing collector numbers
    check_collector_number(collection)
    # Check card identification orientation
    check_orientation(collection)
    return



def main():
    """
    Python MTG Card Mapper.
    """

    # Add command line parser
    parser = argparse.ArgumentParser(
        description='Map output from magic_card_detector.py into collector' +
                     'number.')

    parser.add_argument('set_name',
                        help='3 or 4 letter set acrynm in CAPS')
    parser.add_argument('set_list_path',
                        help='path containing the map')
    parser.add_argument('input_path',
                        help='path containing the images to be analyzed')
    parser.add_argument('output_path',
                        help='path to print mapped results')
    parser.add_argument('--debug', default=False, action='store_true',
                        help='run in verbose debug mode')

    args = parser.parse_args()

    if (args.debug):
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.INFO)

    set_name = args.set_name

    set_list_filename = os.path.join(args.set_list_path, set_name + ".csv");
    input_cards_filename = os.path.join(args.input_path, "cards_" + set_name + ".csv");
    output_cards_filename = os.path.join(args.output_path, set_name + ".csv");

    if not os.path.exists(args.output_path):
        os.mkdir(args.output_path)

    set_list = open_set_list(set_list_filename)

    collection_list = open_collection_list(input_cards_filename)
    collection_list = find_collector_number(collection_list, set_list)

    check_collection(collection_list)

    print_collection(collection_list, output_cards_filename)






if __name__ == "__main__":
    main()
