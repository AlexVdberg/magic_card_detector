import pickle
import argparse
import magic_card_detector as mcg

def makeHash(path, name):
    card_detector = mcg.MagicCardDetector('./')
    card_detector.read_and_adjust_reference_images(path)

    hlist = []
    for image in card_detector.reference_images:
        image.original = None
        image.clahe = None
        image.adjusted = None
        hlist.append(image)

    with open(name, 'wb') as f:
        pickle.dump(hlist, f)

def main():
    """
    Python MTG Card hasher.
    """
    # Add command line parser
    parser = argparse.ArgumentParser(
        description='Create the hash file of images.')

    parser.add_argument('input_path',
                        help='path containing the images to be hashed')
    parser.add_argument('name',
                        help='name of data file to create')

    args = parser.parse_args()

    #makeHash(args.input_path, args.name)
    makeHash(args.input_path, args.name)

if __name__ == "__main__":
    main()
