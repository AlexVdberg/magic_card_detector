#!/bin/bash

prefix="out"
newprefix="card_"
postfix=".jpg"
targetDir="."
paddingLength=4

for file in ${prefix}[0-9]*${postfix}; do
  # strip the prefix off the file name
  postfile=${file#$prefix}
  # strip the postfix off the file name
  number=${postfile%$postfix}
  # subtract 1 from the resulting number
  i=$((number))
  # copy to a new name with padded zeros in a new folder
  cp ${file} "$targetDir"/$(printf $newprefix%0${paddingLength}d$postfix $i)
done

