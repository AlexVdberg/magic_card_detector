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
with set code `MOM` and all images in a folder of the same name, run the
following:
```
python save_hash.py ../scryfalldler/sets/MOM/ MOM.dat
```
You can speed this up with gnu parallel:
```
ls ../scryfalldler/sets | parallel "python save_hash.py ../scryfalldler/sets/{}/ dat/{}.dat"
```

To identify cards in `../mycards` and output results to
`../mycards_identified`, run the following:
```
python magic_card_detector.py --phash MOM.dat ../mycards/MOM/ ../mycards_identified/MOM/
```
To run this in parallel with gnu parallel:
```
ls ../mycards/ | parallel python magic_card_detector.py --phash dat/{}.dat ../mycards/{}/ ../mycards_identified/{}/
```

To scan images in batches from an Auto Document Feeder scanner. Ensure that the
images are zero padded so that the scripts can read them in the proper order.
```
scanimage -d epsonds:libusb:002:004 --format=jpeg --batch=card_%04d.jpg -x 70 -y 90 --batch-start=1
```

