import csv
import argparse
import os

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

    set_name = args.set_name

    set_list_filename = os.path.join(args.set_list_path, set_name + ".csv");
    input_cards_filename = os.path.join(args.input_path, set_name, "cards_" + set_name + ".csv");
    output_cards_filename = os.path.join(args.output_path, set_name + ".csv");

    if not os.path.exists(args.output_path):
        os.mkdir(args.output_path)

    set_list = []
    with open(set_list_filename) as set_list_file:
        reader = csv.reader(set_list_file, delimiter=';')
        set_list = dict(reader)
        if (args.debug):
            print("Set list read from: " + set_list_filename)
            print(set_list)

    f = open(output_cards_filename, "w")
    with open(input_cards_filename) as input_cards_file:
        reader = csv.reader(input_cards_file, delimiter=';')
        if (args.debug):
            print("Detected cards read from: " + input_cards_filename)
        for card in reader:
            if (args.debug):
                print(card)
            if (card[0] == ''):
                print("Card detection missing in " + input_cards_filename)
            else:
                f.write(card[1] + ";" + set_list[card[0]] + "\n")


    f.close()



if __name__ == "__main__":
    main()
