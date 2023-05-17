# magic_card_detector
Python implementation of a Magic: the Gathering card segmentation and recognition

General description of the algorithms and several example can be found in my blog:
https://tmikonen.github.io/quantitatively/2020-01-01-magic-card-detector/

TODO:
- Expects a folder and not an image name to analize. it will not run any detection
  if you give it a jpg file name because it appends it to the path you supply.
- Generate phash for other sets
- Remove hard-coded paths
- actually do arg pasring for reference images
- put results.txt into the output folder.
- figure out what is different between my reference images and the ones used.
  resolution?
- remove path reuiqrement from MagicCardDetector. It is not used by
  `save_hash.py`.

## Usage
To generate the phash of a set of cards, for example `March of the Machines`
with set code `MOM`, run the following:
```
python save_hash.py ../scryfalldler/sets/MOM/ MOM.dat
```

To identify cards in `../mycards` and output results to
`../mycards_identified`, run the following:
```
python magic_card_detector.py --phash MOM.dat ../mycards ../mycards_identified/
```


