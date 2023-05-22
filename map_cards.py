import csv
import argparse

def main():
    """
    Python MTG Card Mapper.
    """

    # Add command line parser
    parser = argparse.ArgumentParser(
        description='Map output from magic_card_detector.py into collector' +
                     'number.')

    parser.add_argument('set_list',
                        help='path containing the map')
    parser.add_argument('input_cards',
                        help='path containing the images to be mapped')

    args = parser.parse_args()

    set_list_filename = args.set_list;
    input_cards_filename = args.input_cards;

    set_list = []
    with open(set_list_filename) as f:
        reader = csv.reader(f, delimiter=';')
        set_list = dict(reader)
        print(set_list)

    f = open("testfile.csv", "w")
    f2 = open("testfile2.csv", "w")
    with open(input_cards_filename) as input_cards_file:
        reader = csv.reader(input_cards_file, delimiter=';')
        for card in reader:
            f.write(card[0] + ";" + set_list[card[0]] + "\n")
            f2.write("CMR;" + set_list[card[0]] + "\n")

        input_cards = dict(reader)
        print(input_cards)

    f.close()
    f2.close()



if __name__ == "__main__":
    main()
